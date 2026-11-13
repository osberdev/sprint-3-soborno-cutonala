"""Índice FAISS individual sobre la base segmentada `conocimientos/` (iteración 6).

Sigue el flujo de app.py del equipo (fragmentos de 1 000 caracteres con 200 de
solapamiento, embeddings `gemini-embedding-2`, índice FAISS guardado), con tres
diferencias deliberadas:

- Los fragmentos salen de los mismos archivos y reglas que la búsqueda local: llevan
  apartado, archivo y estados del autómata, y excluyen lo que el manifiesto excluye
  (capítulo 12, apartado 8.2 y frases de diseño del prototipo).
- Los metadatos se guardan en JSON; no hay `index.pkl` ni deserialización con pickle.
- La consulta vectorial no envía el mensaje del estudiante: se construye con la
  etapa, las reglas, la pregunta informativa y los hechos del caso en frases neutras.
  Después se aplica el mismo filtro por estado o por pregunta que en la búsqueda local.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any


BASE = Path(__file__).resolve().parent
CONOCIMIENTOS = BASE / "conocimientos"
RELATOS = CONOCIMIENTOS / "relatos_campus.md"
INDEX_DIR = BASE / "faiss_index_soborno"
MODEL = "gemini-embedding-2"
DIMENSION = 3072
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DOCUMENTOS = {
    "procesos": "conocimientos/*.md (archivos de orientación del manifiesto)",
    "relatos": "conocimientos/relatos_campus.md",
}


def _dependencias():
    try:
        import faiss
        import numpy as np
    except ImportError as error:
        raise RuntimeError("Instala las dependencias con: pip install -r requirements-faiss.txt") from error
    return faiss, np


def _cliente():
    clave = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not clave:
        raise RuntimeError("Carga GEMINI_API_KEY en esta terminal antes de indexar o consultar FAISS.")
    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError("Instala google-genai con: pip install -r requirements-faiss.txt") from error
    return genai.Client(api_key=clave)


def _huella(grupos: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Configuración y contenido exacto de cada grupo: si cambia un archivo o el manifiesto, se reindexa."""
    grupos = grupos if grupos is not None else leer_documentos()
    return {
        "modelo": MODEL,
        "dimension": DIMENSION,
        "tamano": CHUNK_SIZE,
        "solapamiento": CHUNK_OVERLAP,
        "archivos": {
            tipo: {
                "nombre": DOCUMENTOS[tipo],
                "sha256": hashlib.sha256(json.dumps(fragmentos, ensure_ascii=False, sort_keys=True)
                                         .encode("utf-8")).hexdigest(),
            }
            for tipo, fragmentos in grupos.items()
        },
    }


def _fragmentar(texto: str) -> list[str]:
    texto = re.sub(r"\s+", " ", texto).strip()
    resultado: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + CHUNK_SIZE, len(texto))
        if fin < len(texto):
            corte = texto.rfind(" ", inicio + CHUNK_SIZE // 2, fin)
            if corte > inicio:
                fin = corte
        fragmento = texto[inicio:fin].strip()
        if len(fragmento) >= 80:
            resultado.append(fragmento)
        if fin == len(texto):
            break
        inicio = max(inicio + 1, fin - CHUNK_OVERLAP)
    return resultado


def _partes(fragmento: dict[str, Any], tipo: str) -> list[dict[str, Any]]:
    """Divide un fragmento largo en partes de 1 000 caracteres con 200 de solapamiento."""
    partes = _fragmentar(fragmento["texto"]) or [re.sub(r"\s+", " ", fragmento["texto"]).strip()]
    return [{**fragmento, "texto": parte, "tipo": tipo, "parte": numero}
            for numero, parte in enumerate(partes, 1)]


def leer_documentos() -> dict[str, list[dict[str, Any]]]:
    """Fragmentos de orientación (los mismos de la búsqueda local) y del registro de relatos."""
    from chatbot_soborno import cargar_fragmentos

    procesos = [parte for f in cargar_fragmentos() for parte in _partes(f, "procesos")]
    relatos: list[dict[str, Any]] = []
    texto = RELATOS.read_text(encoding="utf-8")
    for seccion in re.split(r"^#{2,3} ", texto, flags=re.M)[1:]:
        titulo, _, cuerpo = seccion.partition("\n")
        cuerpo = re.sub(r"<!--.*?-->", " ", cuerpo, flags=re.S).replace("**", "")
        if len(cuerpo.strip()) >= 80:
            relatos.extend(_partes({"titulo": titulo.strip(), "texto": cuerpo, "fuentes": [],
                                    "archivo": RELATOS.name, "apartado": "", "estados": ["B2"]}, "relatos"))
    if not procesos or not relatos:
        raise ValueError("La base de conocimientos no produjo fragmentos para FAISS.")
    return {"procesos": procesos, "relatos": relatos}


def _textos_para_embedding(fragmentos: list[dict[str, Any]]) -> list[str]:
    return [f"title: {f['titulo']} | text: {f['texto']}" for f in fragmentos]


def _embeddings(cliente: Any, textos: list[str]) -> list[list[float]]:
    """Un Content por documento evita que Embedding 2 agregue todo el lote."""
    from google.genai import types

    vectores: list[list[float]] = []
    for inicio in range(0, len(textos), 8):
        lote = textos[inicio:inicio + 8]
        entradas = [types.Content(parts=[types.Part.from_text(text=t)]) for t in lote]
        for intento in range(3):
            try:
                salida = cliente.models.embed_content(model=MODEL, contents=entradas)
                break
            except Exception as error:
                # El nivel gratuito puede agotar su cuota por minuto a mitad de un grupo.
                if getattr(error, "code", None) != 429 or intento == 2:
                    raise
                print("Cuota por minuto alcanzada; reintentando este lote en 30 segundos...", flush=True)
                time.sleep(30)
        recibidos = [list(item.values or []) for item in (salida.embeddings or [])]
        if len(recibidos) != len(lote) or any(len(v) != DIMENSION for v in recibidos):
            raise RuntimeError("Gemini devolvió un número o tamaño de embeddings inesperado.")
        vectores.extend(recibidos)
        print(f"Embeddings: {len(vectores)}/{len(textos)}", flush=True)
    return vectores


def _meta_grupo(tipo: str, fragmentos: list[dict[str, Any]], huella: dict[str, Any]) -> dict[str, Any]:
    return {
        "modelo": huella["modelo"],
        "dimension": huella["dimension"],
        "tamano": huella["tamano"],
        "solapamiento": huella["solapamiento"],
        "archivo": huella["archivos"][tipo],
        "fragmentos": len(fragmentos),
    }


def _grupo_guardado_es_valido(tipo: str, fragmentos: list[dict[str, Any]], huella: dict[str, Any], faiss: Any) -> bool:
    """Sólo reutiliza un grupo completo de los mismos documentos, modelo y fragmentos."""
    try:
        meta = json.loads((INDEX_DIR / f"{tipo}.meta.json").read_text(encoding="utf-8"))
        guardados = json.loads((INDEX_DIR / f"{tipo}.json").read_text(encoding="utf-8"))
        indice = faiss.read_index(str(INDEX_DIR / f"{tipo}.faiss"))
    except (OSError, ValueError, RuntimeError):
        return False
    return (
        meta == _meta_grupo(tipo, fragmentos, huella)
        and guardados == fragmentos
        and indice.d == DIMENSION
        and indice.ntotal == len(fragmentos)
    )


def _guardar_grupo(tipo: str, indice: Any, fragmentos: list[dict[str, Any]], huella: dict[str, Any], faiss: Any) -> None:
    with tempfile.NamedTemporaryFile(dir=INDEX_DIR, suffix=".faiss", delete=False) as tmp:
        ruta_indice = Path(tmp.name)
    faiss.write_index(indice, str(ruta_indice))
    with tempfile.NamedTemporaryFile(dir=INDEX_DIR, suffix=".json", mode="w", encoding="utf-8", delete=False) as tmp:
        json.dump(fragmentos, tmp, ensure_ascii=False, indent=2)
        ruta_fragmentos = Path(tmp.name)
    with tempfile.NamedTemporaryFile(dir=INDEX_DIR, suffix=".json", mode="w", encoding="utf-8", delete=False) as tmp:
        json.dump(_meta_grupo(tipo, fragmentos, huella), tmp, ensure_ascii=False, indent=2)
        ruta_meta = Path(tmp.name)
    os.replace(ruta_indice, INDEX_DIR / f"{tipo}.faiss")
    os.replace(ruta_fragmentos, INDEX_DIR / f"{tipo}.json")
    os.replace(ruta_meta, INDEX_DIR / f"{tipo}.meta.json")


def reconstruir_indice(cliente: Any | None = None) -> dict[str, int]:
    """Reanuda por grupo si hay uno válido. No abre el index.pkl recibido."""
    faiss, np = _dependencias()
    cliente = cliente or _cliente()
    grupos = leer_documentos()
    huella = _huella(grupos)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for tipo, fragmentos in grupos.items():
        if _grupo_guardado_es_valido(tipo, fragmentos, huella, faiss):
            print(f"Reutilizando {tipo}: {len(fragmentos)} vectores guardados.", flush=True)
            continue
        vectores = np.asarray(_embeddings(cliente, _textos_para_embedding(fragmentos)), dtype="float32")
        indice = faiss.IndexFlatL2(DIMENSION)
        indice.add(vectores)
        _guardar_grupo(tipo, indice, fragmentos, huella, faiss)
        print(f"Guardado {tipo}: {len(fragmentos)} vectores.", flush=True)
    # El manifiesto se escribe al final: sólo un índice completo se considera vigente.
    for tipo, fragmentos in grupos.items():
        if not _grupo_guardado_es_valido(tipo, fragmentos, huella, faiss):
            raise RuntimeError(f"El grupo {tipo} no se guardó correctamente.")
    (INDEX_DIR / "manifest.json").write_text(json.dumps(huella, ensure_ascii=False, indent=2), encoding="utf-8")
    return {tipo: len(fragmentos) for tipo, fragmentos in grupos.items()}


class BuscadorFaiss:
    es_faiss = True

    def __init__(self, cliente: Any | None = None) -> None:
        faiss, np = _dependencias()
        self.faiss = faiss
        self.np = np
        self.cliente = cliente or _cliente()
        try:
            manifest = json.loads((INDEX_DIR / "manifest.json").read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise RuntimeError("No existe el índice individual. Ejecuta --reindexar-faiss.") from error
        if manifest != _huella():
            raise RuntimeError("La base de conocimientos o la configuración cambiaron. Ejecuta --reindexar-faiss.")
        self.indices = {}
        self.fragmentos = {}
        for tipo in DOCUMENTOS:
            self.indices[tipo] = faiss.read_index(str(INDEX_DIR / f"{tipo}.faiss"))
            self.fragmentos[tipo] = json.loads((INDEX_DIR / f"{tipo}.json").read_text(encoding="utf-8"))
            if self.indices[tipo].ntotal != len(self.fragmentos[tipo]):
                raise RuntimeError(f"Índice y metadatos incompatibles: {tipo}. Reindexa.")

    def _vector(self, texto: str) -> Any:
        salida = self.cliente.models.embed_content(model=MODEL, contents=f"task: question answering | query: {texto}")
        recibidos = salida.embeddings or []
        vector = list(recibidos[0].values or []) if recibidos else []
        if len(vector) != DIMENSION:
            raise RuntimeError("La consulta no produjo un embedding de 3072 dimensiones.")
        return self.np.asarray([vector], dtype="float32")

    def buscar(self, pregunta: str, estado: dict[str, Any], limite: int = 3) -> list[dict[str, Any]]:
        """Ordena todos los fragmentos por similitud y aplica el filtro por estado o por pregunta.

        `pregunta` solo sirve para reconocer la intención; al servicio se envía una consulta
        construida con la etapa y los hechos del caso, nunca el texto del estudiante.
        """
        from chatbot_soborno import admite
        from sprint3_soborno import intencion_pregunta

        consulta = estado.get("consulta") or intencion_pregunta(pregunta)
        fragmentos = self.fragmentos["procesos"]
        _, ids = self.indices["procesos"].search(self._vector(consulta_vectorial(estado, consulta)), len(fragmentos))
        elegidos: list[dict[str, Any]] = []
        apartados: set[str] = set()
        for i in ids[0]:
            if not 0 <= int(i) < len(fragmentos):
                continue
            fragmento = fragmentos[int(i)]
            if fragmento["apartado"] in apartados or not admite(fragmento, estado, consulta):
                continue
            elegidos.append(fragmento)
            apartados.add(fragmento["apartado"])
            if len(elegidos) >= limite:
                break
        return elegidos

    def buscar_registro(self, limite: int = 2) -> list[dict[str, Any]]:
        """Consulta los relatos sin remitir al servicio el nombre escrito por el usuario."""
        fragmentos = self.fragmentos["relatos"]
        _, ids = self.indices["relatos"].search(
            self._vector("relatos anónimos sobre dinero u obsequios a cambio de calificación"), limite)
        return [fragmentos[int(i)] for i in ids[0] if 0 <= int(i) < len(fragmentos)]


def consulta_vectorial(estado: dict[str, Any], consulta: str | None) -> str:
    """Texto de la consulta para el embedding: etapa, reglas, pregunta y hechos neutros (sin el mensaje)."""
    from automata_soborno import ESTADOS, REGLAS
    from gemini_soborno import DESCRIPCION_CONSULTA, hechos_del_caso

    partes: list[str] = []
    if consulta in DESCRIPCION_CONSULTA:
        partes.append(DESCRIPCION_CONSULTA[consulta])
    if estado.get("estado") in ESTADOS and estado["estado"] not in ("q0", "q1"):
        info = ESTADOS[estado["estado"]]
        partes.append(f"{info['nombre']}: {info['instancia']}")
    partes += [REGLAS[r] for r in estado.get("reglas", []) if r in REGLAS and r not in ("B1", "B2")]
    partes += hechos_del_caso(estado.get("ficha") or {})
    return ". ".join(partes) or "orientación sobre soborno académico en CUTonalá"

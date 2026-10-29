"""Índice FAISS individual, compatible con el flujo documental de app.py del equipo.

Se construye únicamente desde los PDF de este módulo. El índice del profesor se
inspeccionó como referencia, pero no se deserializa ni se mezcla con estos datos.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


BASE = Path(__file__).resolve().parent
PDF_DIR = BASE / "conocimientos_pdf"
INDEX_DIR = BASE / "faiss_index_soborno"
MODEL = "gemini-embedding-2"
DIMENSION = 3072
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DOCUMENTOS = {
    "procesos": "investigacion_soborno.pdf",
    "relatos": "casos_soborno.pdf",
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


def _fuentes_pdf() -> dict[str, Path]:
    fuentes = {tipo: PDF_DIR / nombre for tipo, nombre in DOCUMENTOS.items()}
    faltantes = [str(path) for path in fuentes.values() if not path.is_file()]
    if faltantes:
        raise FileNotFoundError("Faltan documentos para FAISS: " + ", ".join(faltantes))
    return fuentes


def _huella() -> dict[str, Any]:
    return {
        "modelo": MODEL,
        "dimension": DIMENSION,
        "tamano": CHUNK_SIZE,
        "solapamiento": CHUNK_OVERLAP,
        "archivos": {
            tipo: {"nombre": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for tipo, path in _fuentes_pdf().items()
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


def leer_documentos() -> dict[str, list[dict[str, Any]]]:
    """Extrae texto de PDF, manteniendo origen y página por fragmento."""
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Instala pypdf con: pip install -r requirements-faiss.txt") from error
    grupos: dict[str, list[dict[str, Any]]] = {}
    for tipo, path in _fuentes_pdf().items():
        fragmentos = []
        for numero, pagina in enumerate(PdfReader(str(path)).pages, 1):
            for texto in _fragmentar(pagina.extract_text() or ""):
                fragmentos.append({
                    "titulo": f"{path.stem}, página {numero}",
                    "texto": texto,
                    "fuentes": list(dict.fromkeys(re.findall(r"\bS\d{2}\b", texto))) if tipo == "procesos" else [],
                    "tipo": tipo,
                    "archivo": path.name,
                    "pagina": numero,
                })
        if not fragmentos:
            raise ValueError(f"El PDF no produjo fragmentos: {path}")
        grupos[tipo] = fragmentos
    return grupos


def _textos_para_embedding(fragmentos: list[dict[str, Any]]) -> list[str]:
    return [f"title: {f['titulo']} | text: {f['texto']}" for f in fragmentos]


def _embeddings(cliente: Any, textos: list[str]) -> list[list[float]]:
    """Un Content por documento evita que Embedding 2 agregue todo el lote."""
    from google.genai import types

    vectores: list[list[float]] = []
    for inicio in range(0, len(textos), 8):
        lote = textos[inicio:inicio + 8]
        entradas = [types.Content(parts=[types.Part.from_text(text=t)]) for t in lote]
        salida = cliente.models.embed_content(model=MODEL, contents=entradas)
        recibidos = [list(item.values or []) for item in (salida.embeddings or [])]
        if len(recibidos) != len(lote) or any(len(v) != DIMENSION for v in recibidos):
            raise RuntimeError("Gemini devolvió un número o tamaño de embeddings inesperado.")
        vectores.extend(recibidos)
        print(f"Embeddings: {len(vectores)}/{len(textos)}", flush=True)
    return vectores


def reconstruir_indice(cliente: Any | None = None) -> dict[str, int]:
    """Reindexa ambos PDF. No abre index.pkl ni el índice recibido del profesor."""
    faiss, np = _dependencias()
    cliente = cliente or _cliente()
    grupos = leer_documentos()
    huella = _huella()
    temporales: dict[str, tuple[Path, Path]] = {}
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for tipo, fragmentos in grupos.items():
        vectores = np.asarray(_embeddings(cliente, _textos_para_embedding(fragmentos)), dtype="float32")
        indice = faiss.IndexFlatL2(DIMENSION)
        indice.add(vectores)
        with tempfile.NamedTemporaryFile(dir=INDEX_DIR, suffix=".faiss", delete=False) as tmp:
            ruta_indice = Path(tmp.name)
        faiss.write_index(indice, str(ruta_indice))
        with tempfile.NamedTemporaryFile(dir=INDEX_DIR, suffix=".json", mode="w", encoding="utf-8", delete=False) as tmp:
            json.dump(fragmentos, tmp, ensure_ascii=False, indent=2)
            ruta_fragmentos = Path(tmp.name)
        temporales[tipo] = ruta_indice, ruta_fragmentos
    # El manifiesto se escribe al final: sólo un índice completo se considera vigente.
    (INDEX_DIR / "manifest.json").unlink(missing_ok=True)
    for tipo, (ruta_indice, ruta_fragmentos) in temporales.items():
        os.replace(ruta_indice, INDEX_DIR / f"{tipo}.faiss")
        os.replace(ruta_fragmentos, INDEX_DIR / f"{tipo}.json")
    (INDEX_DIR / "manifest.json").write_text(json.dumps(huella, ensure_ascii=False, indent=2), encoding="utf-8")
    return {tipo: len(fragmentos) for tipo, fragmentos in grupos.items()}


class BuscadorFaiss:
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
            raise RuntimeError("Los PDF o la configuración cambiaron. Ejecuta --reindexar-faiss.")
        self.indices = {}
        self.fragmentos = {}
        for tipo in DOCUMENTOS:
            self.indices[tipo] = faiss.read_index(str(INDEX_DIR / f"{tipo}.faiss"))
            self.fragmentos[tipo] = json.loads((INDEX_DIR / f"{tipo}.json").read_text(encoding="utf-8"))
            if self.indices[tipo].ntotal != len(self.fragmentos[tipo]):
                raise RuntimeError(f"Índice y metadatos incompatibles: {tipo}. Reindexa.")

    def buscar(self, pregunta: str, estado: dict[str, Any], limite: int = 3, *, tipo: str = "procesos") -> list[dict[str, Any]]:
        if tipo not in DOCUMENTOS:
            raise ValueError(f"Tipo de documentos desconocido: {tipo}")
        texto = f"task: question answering | query: {pregunta}"
        salida = self.cliente.models.embed_content(model=MODEL, contents=texto)
        recibidos = salida.embeddings or []
        vector = list(recibidos[0].values or []) if recibidos else []
        if len(vector) != DIMENSION:
            raise RuntimeError("La consulta no produjo un embedding de 3072 dimensiones.")
        _, ids = self.indices[tipo].search(self.np.asarray([vector], dtype="float32"), limite)
        return [self.fragmentos[tipo][int(i)] for i in ids[0] if 0 <= int(i) < len(self.fragmentos[tipo])]

    def buscar_registro(self, limite: int = 2) -> list[dict[str, Any]]:
        """Consulta los relatos sin remitir al servicio el nombre escrito por el usuario."""
        return self.buscar("relatos anónimos sobre dinero u obsequios a cambio de calificación", {}, limite, tipo="relatos")

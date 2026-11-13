"""Chatbot individual de soborno académico: autómata + recuperación + Gemini opcional.

La base consultada es la investigación de Oscar, segmentada en `conocimientos/`
según `conocimientos/manifiesto.json`. Solo se indexan los archivos de uso
"orientacion"; los relatos del campus se consultan aparte y los apartados
excluidos (metodología, escenarios ficticios, diseño del prototipo) no se recuperan.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any

from casos_consulta import resumen_registro
from automata_soborno import ESTADOS, REGLAS, SesionAutomata, respuesta_si_no
from gemini_soborno import ExtractorGemini, describir_fallo, redactar
from sprint3_soborno import intencion_pregunta, normalizar


BASE = Path(__file__).resolve().parent
CONOCIMIENTOS = BASE / "conocimientos"
MANIFIESTO = json.loads((CONOCIMIENTOS / "manifiesto.json").read_text(encoding="utf-8"))
FUENTES = json.loads((BASE / "fuentes.json").read_text(encoding="utf-8"))["fuentes"]
STOPWORDS = set(
    "a al algo ante como con cual cuando de del donde el ella en entre es esta este "
    "hay la las le lo los me mi mis no o para por que quien se si su sus un una uno "
    "y ya yo sobre puedo podria quisiera quiero necesito caso estudiante profesor "
    "docente hecho hechos universidad cut cutonala".split()
)
TERMINOS = {
    "botella": "regalo obsequio beneficio",
    "pago": "dinero beneficio",
    "pagar": "dinero beneficio",
    "reprobar": "calificacion evaluacion amenaza",
    "aprobar": "acreditar calificacion ventaja",
    "denunciar": "denuncia presentacion recepcion",
    "contactar": "contacto correo ubicacion",
    "cohecho": "soborno beneficio funcion",
}
PREFERENCIAS = {
    "encargado": ("6.2", "blanca elizabeth valeria rubi"),
    "ubicacion": ("6.2", "centro atencion estudiantes cae primera puerta izquierda"),
    "contacto": ("6.2", "correo primercontacto telefono"),
    "programa": ("5.2", "atencion violencia acompanamiento orientacion"),
    "relacion": ("5.2", "soborno primer contacto violencia"),
    "coordinacion": ("6.2", "coordinacion ingenieria ciencias computacionales dulce maria"),
    "plazo": ("5.6", "revision calificacion tres dias habiles"),
    "legal": ("7.4", "fiscalia anticorrupcion denuncia"),
    "personal": ("4.1", "registro apoyo bienestar"),
}
EXPANSION_REGLAS = {
    "B4": "comentario indirecto procedencia aclaracion",
    "B6": "bienestar apoyo orientacion educativa",
    "B7": "exigencia beneficio ventaja academica",
    "B8": "amenaza represalia medidas proteccion cautelares",
    "B9": "revision calificacion tres dias habiles",
    "B11": "bienestar apoyo orientacion educativa",
    "B12": "revision calificacion tres dias habiles",
    "B14": "fiscalia denuncia anticorrupcion",
    "B15": "asesoria juridica participacion",
    "B16": "peligro emergencia proteccion",
}
PARRAFOS_CLAVE = {
    "5.1": "El artículo 21.1",
    "5.5": "Los artículos 39–46",
    "7.3": "Se recomienda valoración legal temprana",
}
PRIORIDADES_CONSULTA = {
    "encargado": ["6.2"], "ubicacion": ["6.2"], "contacto": ["6.2"], "coordinacion": ["6.2"],
    "programa": ["5.2"], "relacion": ["5.2", "5.1"], "plazo": ["5.6"], "legal": ["7.4"], "personal": ["4.1"],
}


def apartados_prioritarios(estado: dict[str, Any], intencion: str | None) -> list[str]:
    """Apartados que encabezan la recuperación de cada etapa; son parte de la orientación, no de
    la búsqueda, y por eso valen igual en el modo local y en FAISS."""
    if intencion:
        return PRIORIDADES_CONSULTA.get(intencion, [])
    if estado.get("prioridad") == "urgente":
        return ["5.5", "7.3"]
    if estado.get("tipo_riesgo") and estado.get("estado") == "q3":
        return ["5.5", "5.6"]
    if estado.get("estado") in ("q3", "q5", "q6"):
        return ["5.1", "7.3", "4.2"]
    if (estado.get("ficha") or {}).get("procedencia") == "indirecta":
        return ["8.1"]
    return []


def seleccionar(ordenados: list[dict[str, Any]], estado: dict[str, Any], intencion: str | None,
                limite: int) -> list[dict[str, Any]]:
    """Primero los apartados prioritarios de la etapa (con su párrafo clave); después, el resto en el
    orden recibido (BM25 o similitud de vectores), un fragmento por apartado."""
    elegidos: list[dict[str, Any]] = []
    usados: set[str] = set()
    for apartado in apartados_prioritarios(estado, intencion):
        inicio = PARRAFOS_CLAVE.get(apartado)
        del_apartado = [f for f in ordenados if f.get("apartado") == apartado]
        candidato = next((f for f in del_apartado if inicio and f["texto"].startswith(inicio)),
                         del_apartado[0] if del_apartado else None)
        if candidato is not None:
            elegidos.append(candidato)
            usados.add(apartado)
    for fragmento in ordenados:
        if len(elegidos) >= limite:
            break
        if fragmento.get("apartado") not in usados:
            elegidos.append(fragmento)
            usados.add(fragmento.get("apartado"))
    return elegidos[:limite]


def palabras(texto: str) -> list[str]:
    normal = normalizar(texto)
    return [p for p in re.findall(r"[a-z0-9]{3,}", normal) if p not in STOPWORDS]


def filas_de_tabla(bloque: str) -> list[str]:
    """Convierte una tabla Markdown en una oración por fila: «Encabezado: celda; ...»."""
    lineas = [l.strip() for l in bloque.splitlines() if l.strip().startswith("|")]
    celdas = [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", l.strip("|"))] for l in lineas]
    celdas = [fila for fila in celdas if not all(re.fullmatch(r"-+", c) for c in fila if c)]
    if len(celdas) < 2:
        return []
    encabezado = celdas[0]
    return ["; ".join(f"{e}: {c}" for e, c in zip(encabezado, fila) if c) + "." for fila in celdas[1:]]


def sin_frases_de_diseno(parrafo: str, frases: list[str]) -> str:
    """Omite las oraciones que describen el diseño del prototipo (D35); el resto queda literal."""
    oraciones = re.split(r"(?<=\.)\s+", parrafo)
    return " ".join(o for o in oraciones if not any(f in normalizar(o) for f in frases))


def cargar_fragmentos(manifiesto: dict | None = None) -> list[dict[str, Any]]:
    """Divide los archivos de orientación por apartado y párrafo para recuperar evidencia."""
    manifiesto = manifiesto or MANIFIESTO
    no_indexar = manifiesto.get("no_indexar", {})
    apartados_excluidos = set(no_indexar.get("apartados", []))
    frases_de_diseno = no_indexar.get("frases", [])
    fragmentos: list[dict[str, Any]] = []
    for entrada in manifiesto["archivos"]:
        if entrada["uso"] != "orientacion":
            continue
        texto = (CONOCIMIENTOS / entrada["archivo"]).read_text(encoding="utf-8")
        for seccion in re.split(r"^## ", texto, flags=re.M)[1:]:
            titulo, _, cuerpo = seccion.partition("\n")
            titulo = titulo.strip()
            if titulo.split()[0] in apartados_excluidos:
                continue
            bloques: list[str] = []
            for bloque in re.split(r"\n\s*\n", cuerpo.strip()):
                # Los elementos de una lista se recuperan juntos: un punto suelto («7. Información…») no orienta.
                es_lista = re.match(r"^(- |\d+\. )", bloque.strip()) is not None
                if es_lista and bloques and re.match(r"^(- |\d+\. )", bloques[-1].strip()):
                    bloques[-1] += " " + bloque.strip()
                else:
                    bloques.append(bloque)
            for bloque in bloques:
                partes = filas_de_tabla(bloque) if bloque.lstrip().startswith("|") else [bloque]
                for parrafo in partes:
                    parrafo = sin_frases_de_diseno(re.sub(r"\s+", " ", parrafo).strip(), frases_de_diseno)
                    if len(parrafo) < 80 or parrafo.startswith("<!--"):
                        continue
                    ids = list(dict.fromkeys(re.findall(r"S\d{2}", parrafo)))
                    fragmentos.append({
                        "titulo": titulo,
                        "texto": parrafo,
                        "fuentes": [i for i in ids if i in FUENTES],
                        "archivo": entrada["archivo"],
                        "apartado": titulo.split()[0],
                        "estados": list(entrada["estados"]),
                    })
    return fragmentos


def extracto_de(fragmento: dict[str, Any]) -> str:
    """Las dos primeras oraciones del fragmento, como se muestran en «Dato recuperado»."""
    frases = re.split(r"(?<=[.!?])\s+", texto_visible(fragmento))
    extracto = " ".join(frases[:2]).replace("**", "")
    if len(extracto) > 420:
        extracto = extracto[:420].rsplit(" ", 1)[0] + "…"
    return extracto


def aporta_informacion(fragmento: dict[str, Any], respuesta: str, umbral: float = 0.5) -> bool:
    """El extracto aporta si al menos la mitad de sus palabras de contenido no están en la respuesta."""
    propias = {p for p in palabras(extracto_de(fragmento)) if len(p) >= 5}
    if not propias:
        return False
    ya_dichas = set(palabras(respuesta))
    return len(propias - ya_dichas) / len(propias) >= umbral


class Buscador:
    def __init__(self) -> None:
        self.fragmentos = cargar_fragmentos()
        self.conteos = [Counter(palabras(f["titulo"] + " " + f["texto"])) for f in self.fragmentos]
        self.documentos_con_palabra = Counter()
        for conteo in self.conteos:
            self.documentos_con_palabra.update(conteo.keys())
        self.longitud_media = sum(map(lambda c: sum(c.values()), self.conteos)) / len(self.conteos)

    def buscar(self, pregunta: str, estado: dict[str, Any], limite: int = 3) -> list[dict[str, Any]]:
        consulta = pregunta + " " + estado["justificacion"]
        for regla in estado.get("reglas", []):
            consulta += " " + EXPANSION_REGLAS.get(regla, "")
        intencion = intencion_pregunta(pregunta)
        seccion_preferida = None
        if intencion in PREFERENCIAS:
            seccion_preferida, palabras_adicionales = PREFERENCIAS[intencion]
            consulta += " " + palabras_adicionales
        for termino, expansion in TERMINOS.items():
            if termino in normalizar(pregunta):
                consulta += " " + expansion
        if estado.get("estado") in ("q3", "q5", "q6"):
            consulta += " exigencia beneficio ventaja academica orientacion juridica"
        if estado["prioridad"] == "urgente":
            consulta += " amenaza represalia medidas proteccion"
        buscadas = set(palabras(consulta))
        total = len(self.fragmentos)
        consulta_informativa = estado.get("consulta") or intencion
        resultados = []
        for fragmento, conteo in zip(self.fragmentos, self.conteos):
            if not admite(fragmento, estado, consulta_informativa):
                continue
            longitud = sum(conteo.values())
            titulo = set(palabras(fragmento["titulo"]))
            puntuacion = 0.0
            for termino in buscadas:
                frecuencia = conteo[termino]
                if not frecuencia:
                    continue
                df = self.documentos_con_palabra[termino]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                puntuacion += idf * (frecuencia * 2.2) / (
                    frecuencia + 1.2 * (0.25 + 0.75 * longitud / self.longitud_media)
                )
                if termino in titulo:
                    puntuacion += 1.25 * idf
            if seccion_preferida and fragmento["titulo"].startswith(seccion_preferida):
                puntuacion += 5
            if puntuacion:
                resultados.append((puntuacion, fragmento))
        resultados.sort(key=lambda x: x[0], reverse=True)
        return seleccionar([f for _, f in resultados], estado, intencion, limite)


DESTINO_PREGUNTA = {"B10": "q3", "B14": "q5", "B15": "q6", "B16": "qS"}


# Archivos que responden cada pregunta informativa (D34): «¿Quién es la encargada…?»
# ya no recupera la matriz de prioridad ni el nivel legal.
ARCHIVOS_POR_CONSULTA = {
    "encargado": {"directorio_cutonala.md"},
    "ubicacion": {"directorio_cutonala.md"},
    "contacto": {"directorio_cutonala.md"},
    "coordinacion": {"directorio_cutonala.md", "revision_evaluacion.md"},
    "programa": {"primer_contacto.md", "denuncia_universitaria.md"},
    "relacion": {"primer_contacto.md", "denuncia_universitaria.md"},
    "plazo": {"revision_evaluacion.md"},
    "niveles": {"canalizacion.md", "nivel_personal.md", "denuncia_universitaria.md", "nivel_legal.md"},
    "legal": {"nivel_legal.md", "directorio_externo.md", "asesoria_y_participacion.md"},
    "personal": {"nivel_personal.md"},
}


def admite(fragmento: dict[str, Any], estado: dict[str, Any], consulta: str | None) -> bool:
    """Filtro común a la búsqueda local y a FAISS.

    Una pregunta informativa consulta los archivos que la responden; un relato, los archivos
    de su estado (y del que abriría la pregunta pendiente). Si el mensaje trae ambas cosas,
    vale cualquiera de los dos criterios.
    """
    relato = any(r not in ("B1", "B2") for r in estado.get("reglas", []))
    if consulta in ARCHIVOS_POR_CONSULTA:
        if fragmento.get("archivo") in ARCHIVOS_POR_CONSULTA[consulta]:
            return True
        if not relato:
            return False
    permitidos = estados_de_busqueda(estado)
    return not permitidos or bool(permitidos & set(fragmento.get("estados", [])))


def estados_de_busqueda(estado: dict[str, Any]) -> set[str]:
    """Estados cuyos archivos se consultan: el actual y el que abriría la pregunta pendiente."""
    actuales = {estado.get("estado")} - {None, "q0"}
    if estado.get("pendiente") in DESTINO_PREGUNTA:
        actuales.add(DESTINO_PREGUNTA[estado["pendiente"]])
    if estado.get("salida") == "otro_tema":
        actuales.add("otro_tema")
    return actuales


def ids_y_enlaces(fragmentos: list[dict[str, Any]], estado: dict[str, Any]) -> dict[str, str]:
    ids = list(dict.fromkeys(
        [i for f in fragmentos for i in f["fuentes"]] + estado["fuentes"]
    ))
    return {i: FUENTES[i]["url"] for i in ids if i in FUENTES}


def texto_visible(fragmento: dict[str, Any]) -> str:
    """Prepara el fragmento para mostrarlo, sin formato Markdown."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", fragmento["texto"])
    return re.sub(r"(^|\s)- (?=\S)", r"\1", texto)


CASO_GUARDADO = Path(__file__).resolve().parent / "caso_guardado.local.json"


class CasoGuardado:
    """Caso guardado entre ejecuciones (iteración 5).

    Solo contiene el estado del autómata y la ficha (indicadores y decisiones), nunca el
    texto de los mensajes. El archivo está excluido de Git y se escribe de forma atómica.
    """

    def __init__(self, ruta: Path = CASO_GUARDADO) -> None:
        self.ruta = ruta

    def existe(self) -> bool:
        return self.ruta.exists()

    def guardar(self, sesion: SesionAutomata) -> None:
        datos = sesion.exportar()
        datos["guardado"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        temporal = self.ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporal, self.ruta)

    def cargar(self, extractor: Any = None) -> tuple[SesionAutomata | None, str | None]:
        """Devuelve la sesión y la fecha de guardado, o (None, motivo) si no se puede usar."""
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            return SesionAutomata.desde_dict(datos, extractor=extractor), datos.get("guardado")
        except FileNotFoundError:
            return None, None
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return None, f"el caso guardado no es válido ({error}); se ignora"

    def borrar(self) -> None:
        self.ruta.unlink(missing_ok=True)


class ChatSoborno:
    def __init__(self, buscador: Any | None = None, extractor_gemini: bool = False,
                 guardado: CasoGuardado | None = None, sesion: SesionAutomata | None = None) -> None:
        # El extractor de Gemini es opcional y separado de la redacción: envía el texto del
        # mensaje al servicio, mientras que la redacción solo envía la tarjeta del estado.
        self.extractor = ExtractorGemini() if extractor_gemini else None
        self.sesion = sesion or SesionAutomata(extractor=self.extractor)
        self.sesion.extractor = self.extractor
        self.guardado = guardado
        self.buscador = buscador if buscador is not None else Buscador()
        self.extractos_mostrados: set[str] = set()

    def responder(self, mensaje: str, gemini: bool = False) -> dict[str, Any]:
        if self.extractor:
            self.extractor.descartados = []
        estado = self.sesion.procesar(mensaje)
        if self.guardado:
            try:
                self.guardado.guardar(self.sesion)
            except OSError:
                pass  # guardar es una comodidad; la conversación sigue aunque falle el disco
        if "B2" in estado["reglas"]:
            respuesta, registros = resumen_registro(mensaje)
            # Una pregunta por referencias no es un hecho del caso del estudiante.
            # No se incorpora a la memoria del autómata ni se envía a Gemini.
            fragmentos = []
            fallo_faiss = None
            if registros and all(r["id"] in {"C01", "C02"} for r in registros) and hasattr(self.buscador, "buscar_registro"):
                try:
                    fragmentos = self.buscador.buscar_registro()
                except Exception as error:
                    fallo_faiss = describir_fallo(error)
            return {
                **estado,
                "success": True,
                "consulta_antecedentes": True,
                "justificacion": "La respuesta identifica la procedencia y el estado de cada relato consultado.",
                "respuesta_chatbot": respuesta,
                "modo": "FAISS + registro de relatos" if fragmentos else "Local + registro de relatos",
                "fragmentos": fragmentos,
                "casos_consultados": [r["id"] for r in registros],
                "fuentes_consultadas": {},
                "fallo_gemini": None,
                "fallo_faiss": fallo_faiss,
                "memoria_turnos": estado["turnos"],
            }
        estado = {**estado, "success": True, "memoria_turnos": estado["turnos"]}
        fallo_faiss = None
        fragmentos: list[dict[str, Any]] = []
        # Un turno sin regla ni pregunta informativa no aporta nada que buscar.
        # Retomar el caso tras Seguridad (B17) tampoco: la respuesta ya es completa.
        if (estado["reglas"] or estado.get("consulta")) and "B17" not in estado["reglas"]:
            try:
                fragmentos = self.buscador.buscar(mensaje, estado)
            except Exception as error:
                if isinstance(self.buscador, Buscador):
                    raise
                fallo_faiss = describir_fallo(error)
                fragmentos = Buscador().buscar(mensaje, estado)
        respuesta = estado["respuesta"]
        pregunta = estado.get("pregunta")
        if pregunta and respuesta.endswith(pregunta):
            respuesta = respuesta[: -len(pregunta)].rstrip()
        # El extracto se muestra al llegar a una etapa o al responder una pregunta informativa,
        # y nunca dos veces el mismo en la sesión (D25). Retomar el caso tras Seguridad (B17)
        # no es una etapa nueva: no añade extracto (D33).
        # Tampoco se muestra un extracto que repite lo que la respuesta ya dice.
        nuevos = [f for f in fragmentos if f["texto"] not in self.extractos_mostrados
                  and aporta_informacion(f, respuesta)]
        etapa = (estado["estado"] not in ("q0", "q1") and "B17" not in estado["reglas"]
                 and any(r not in ("B1", "B2") for r in estado["reglas"]))
        if nuevos and (etapa or estado.get("consulta")):
            primero = nuevos[0]
            self.extractos_mostrados.add(primero["texto"])
            extracto = extracto_de(primero)
            citas = ", ".join(primero["fuentes"])
            respuesta += f"\nDato recuperado de «{primero['titulo']}»: {extracto}"
            if citas:
                respuesta += f" [{citas}]"
        orientacion_base = respuesta
        # Sin texto previo, la pregunta va en la misma línea que «RESPUESTA:» (D44).
        respuesta = "\n".join(parte for parte in (respuesta.strip(), pregunta) if parte)
        fallo_gemini = None
        no_fundamentado: list[str] = []
        # Gemini redacta cuando el turno tiene una regla o una pregunta informativa; un turno
        # sin novedad o una pregunta sin dato conserva la respuesta local, breve (D40).
        redacta = gemini and (estado["reglas"] or estado.get("consulta")) and "B17" not in estado["reglas"]
        if redacta:
            try:
                redaccion, no_fundamentado = redactar(estado, fragmentos, orientacion_base)
                # Una redacción con datos que no están en el contexto no se muestra (iteración 4).
                if not no_fundamentado:
                    respuesta = redaccion + (f"\n{pregunta}" if pregunta else "")
            except Exception as error:
                fallo_gemini = describir_fallo(error)
        return {
            **estado,
            "respuesta_chatbot": respuesta,
            "modo": (
                ("Gemini" if redacta and not fallo_gemini and not no_fundamentado else "Local")
                + " + autómata + "
                + ("FAISS" if getattr(self.buscador, "es_faiss", False) and not fallo_faiss else "documentos")
            ),
            "fragmentos": fragmentos,
            "fuentes_consultadas": ids_y_enlaces(fragmentos, estado),
            "fallo_gemini": fallo_gemini,
            "gemini_no_fundamentado": no_fundamentado,
            "fallo_faiss": fallo_faiss,
            "hechos_descartados": list(self.extractor.descartados) if self.extractor else [],
        }


def mostrar(resultado: dict[str, Any]) -> None:
    if not resultado["success"]:
        print("Error:", resultado["error"])
        return
    print("\nRESPUESTA:", resultado["respuesta_chatbot"])
    print("MODO:", resultado["modo"])
    if resultado.get("consulta_antecedentes"):
        # D06: una consulta informativa no muestra la clasificación del caso.
        print("CONSULTA DE ANTECEDENTES: no cambia tu caso.")
    else:
        print(f"AUTÓMATA: {resultado['estado']} · {resultado['nombre']} | fase {resultado['fase']} "
              f"| prioridad: {resultado['prioridad']}")
        if resultado["reglas"]:
            print("REGLAS:", ", ".join(f"{r} {REGLAS[r]}" for r in resultado["reglas"]))
        if resultado.get("tipo_riesgo"):
            print("RIESGO DESCRITO:", resultado["tipo_riesgo"])
        if resultado.get("vias"):
            print("VÍAS CONCURRENTES:", "; ".join(resultado["vias"]))
        if resultado.get("otro_tema"):
            print("OTRO TEMA DEL EQUIPO:", resultado["otro_tema"])
        if resultado.get("pendiente"):
            print(f"ESPERA RESPUESTA: {resultado['pendiente']} (sí / no)")
    if resultado["fragmentos"]:
        print("FRAGMENTOS CONSULTADOS:")
        for f in resultado["fragmentos"]:
            visible = texto_visible(f)
            print(f"  · {f['titulo']}: {visible[:230]}{'…' if len(visible) > 230 else ''}")
    if resultado.get("casos_consultados"):
        print("REGISTRO DE RELATOS CONSULTADO:", ", ".join(resultado["casos_consultados"]))
    if resultado["fuentes_consultadas"]:
        print("FUENTES PÚBLICAS CITADAS EN LA INVESTIGACIÓN:")
        for clave, url in resultado["fuentes_consultadas"].items():
            print(f"  [{clave}] {url}")
    if resultado.get("hechos_gemini"):
        print("HECHOS AÑADIDOS POR GEMINI:", ", ".join(resultado["hechos_gemini"]))
    if resultado.get("hechos_descartados"):
        print("HECHOS DE GEMINI SIN CITA COMPROBABLE (descartados):",
              ", ".join(str(h.get("hecho")) for h in resultado["hechos_descartados"]))
    if resultado.get("extractor_consultado") and not (resultado.get("hechos_gemini") or resultado.get("hechos_descartados")
                                                        or resultado.get("fallo_extractor")):
        print("EXTRACTOR GEMINI: respondió sin hechos adicionales.")
    if resultado.get("fallo_extractor"):
        print("EXTRACTOR GEMINI NO RESPONDIÓ:", resultado["fallo_extractor"])
        print("El turno se evaluó solo con las reglas locales.")
    if resultado.get("gemini_no_fundamentado"):
        print("REDACCIÓN DE GEMINI NO FUNDAMENTADA:", "; ".join(resultado["gemini_no_fundamentado"]))
        print("Se mostró la respuesta local porque esos datos no están en el contexto enviado.")
    if resultado["fallo_gemini"]:
        print("GEMINI NO RESPONDIÓ:", resultado["fallo_gemini"])
        print("Se mostró la respuesta local; puedes volver a probar Gemini más tarde.")
    if resultado.get("fallo_faiss"):
        print("FAISS NO RESPONDIÓ:", resultado["fallo_faiss"])
        print("Se usó la búsqueda local para conservar la orientación.")


def retomar_si_existe(chat: "ChatSoborno", guardado: CasoGuardado, buscador: Any, extractor_gemini: bool,
                      entrada=input) -> "ChatSoborno":
    """Ofrece retomar el caso guardado; un «no» lo borra (iteración 5)."""
    if not guardado.existe():
        return chat
    sesion, fecha_o_motivo = guardado.cargar()
    if sesion is None:
        print(f"Aviso: {fecha_o_motivo}.")
        return chat
    info = ESTADOS[sesion.estado]
    print(f"Hay un caso guardado el {fecha_o_motivo or 'día anterior'} en {sesion.estado} · {info['nombre']}.")
    while True:
        try:
            respuesta = respuesta_si_no(entrada("¿Lo retomamos? Responde sí o no: ").strip())
        except (EOFError, KeyboardInterrupt):
            respuesta = "si"
        if respuesta in ("si", "no"):
            break
    if respuesta == "no":
        guardado.borrar()
        print("Caso guardado borrado. Empezamos de nuevo.")
        return chat
    print("RESPUESTA:", sesion.texto_reanudacion())
    return ChatSoborno(buscador=buscador, extractor_gemini=extractor_gemini, guardado=guardado, sesion=sesion)


DEMO = [
    "¿Dónde encuentro Primer Contacto en CUTonalá?",
    "Se comenta que un profesor llamado X aprueba por regalos.",
    "reset",
    "Un docente me pidió una botella a cambio de acreditar la materia.",
    "Si no se la doy, me amenaza con reprobarme.",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Chatbot individual de soborno académico para Sprint 3")
    parser.add_argument("--demo", action="store_true", help="muestra una conversación ficticia reproducible")
    parser.add_argument("--pregunta", help="procesa un solo mensaje y termina")
    parser.add_argument("--gemini", action="store_true", help="usa Gemini para redactar la orientación")
    parser.add_argument("--sin-guardar", action="store_true",
                        help="no guarda el caso entre ejecuciones (se guarda por defecto en la conversación interactiva)")
    parser.add_argument("--extractor-gemini", action="store_true",
                        help="usa Gemini para detectar hechos (envía el texto de cada mensaje)")
    parser.add_argument("--faiss", action="store_true", help="recupera de los PDF con el índice FAISS individual")
    parser.add_argument("--reindexar-faiss", action="store_true", help="reconstruye el índice desde los PDF individuales")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.reindexar_faiss:
        from faiss_soborno import reconstruir_indice
        try:
            cantidades = reconstruir_indice()
        except (RuntimeError, FileNotFoundError, ValueError) as error:
            print(f"No se pudo reconstruir FAISS: {error}", file=sys.stderr)
            return 2
        except Exception as error:
            if getattr(error, "code", None) == 429:
                print("Gemini agotó la cuota temporal. Los PDF completados quedaron guardados; vuelve a ejecutar --reindexar-faiss más tarde.", file=sys.stderr)
                return 2
            raise
        print("Índice individual actualizado:", cantidades)
        return 0
    try:
        if args.faiss:
            from faiss_soborno import BuscadorFaiss
            buscador = BuscadorFaiss()
        else:
            buscador = Buscador()
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        print(f"No se pudo cargar FAISS: {error}", file=sys.stderr)
        return 2
    pendientes = DEMO.copy() if args.demo else [args.pregunta] if args.pregunta else None
    # El caso se guarda solo en la conversación interactiva; la demostración y --pregunta no tocan el disco.
    guardado = None if (pendientes is not None or args.sin_guardar) else CasoGuardado()
    chat = ChatSoborno(buscador=buscador, extractor_gemini=args.extractor_gemini, guardado=guardado)
    if (args.gemini or args.extractor_gemini) and not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("No hay clave para Gemini. Ejecuta sin --gemini ni --extractor-gemini para la demostración local.",
              file=sys.stderr)
        return 2
    if args.extractor_gemini:
        print("Aviso: el extractor envía a Gemini el texto de cada mensaje (sin guardarlo en el servicio). "
              "Las consultas de antecedentes y las respuestas de sí o no no se envían.")
    if pendientes is None:
        print("Chatbot individual · soborno académico · CUTonalá")
        print("Usa relatos ficticios. Escribe 'reset' para reiniciar o 'salir' para terminar.")
        if guardado:
            print(f"El caso se guarda en {guardado.ruta.name}: solo el estado y los hechos, sin tus mensajes. "
                  "Escribe 'olvidar' para borrarlo.")
            chat = retomar_si_existe(chat, guardado, buscador, args.extractor_gemini)
    while True:
        if pendientes is not None:
            if not pendientes:
                break
            mensaje = pendientes.pop(0)
            print("\nESTUDIANTE:", mensaje)
        else:
            try:
                mensaje = input("\nESTUDIANTE: ").strip()
                if not sys.stdin.isatty():
                    print(mensaje)  # con entrada redirigida, el mensaje queda en la transcripción
            except (EOFError, KeyboardInterrupt):
                print("\nFin de la conversación.")
                break
        if mensaje.casefold() == "salir":
            break
        if mensaje.casefold() in ("reset", "olvidar"):
            if guardado:
                guardado.borrar()
            chat = ChatSoborno(buscador=buscador, extractor_gemini=args.extractor_gemini, guardado=guardado)
            print("Caso borrado y reiniciado; la base de conocimientos sigue disponible."
                  if guardado else "Caso reiniciado; la base de conocimientos sigue disponible.")
            continue
        if args.gemini or args.extractor_gemini:
            print("Consultando Gemini (espera limitada; hay respuesta local si falla)...", flush=True)
        mostrar(chat.responder(mensaje, gemini=args.gemini))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

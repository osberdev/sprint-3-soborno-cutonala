"""Demostración del Sprint 3: módulo individual de soborno en CUTonalá.

Usa sólo casos ficticios. Funciona con Python estándar; Gemini es opcional.
Conserva el contrato básico del autómata utilizado en el Sprint 2.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
FUENTES = json.loads((BASE / "fuentes.json").read_text(encoding="utf-8"))["fuentes"]
CONOCIMIENTO = (BASE / "conocimientos" / "primer_contacto_soborno.md").read_text(encoding="utf-8")
CAPAS = {1: "Orientación personal", 2: "UDG", 3: "Autoridad externa"}
ESTADO_INICIAL = {"x": 1, "y": 1}


def normalizar(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_acentos).strip()


FAQ: dict[str, tuple[str, tuple[str, ...]]] = {
    "encargado": (
        "El directorio de CUTonalá identifica a Blanca Elizabeth González Jauregui como encargada del despacho de Primer Contacto. El directorio central también registra a Valeria Rubí González Orizaba, con horario de atención distinto. Confirma el turno antes de acudir.",
        ("S06", "S08"),
    ),
    "ubicacion": (
        "Primer Contacto está en el Centro de Atención a Estudiantes (CAE) del CUTonalá: entrando al edificio, a la izquierda, primera puerta, en la oficina compartida con el enlace de la Defensoría. Campus: Av. Nuevo Periférico 555, Ejido San José Tateposco, Tonalá. El directorio central publica atención de Blanca de lunes a viernes de 9:00 a 15:00 y de Valeria de 12:00 a 19:00.",
        ("S05", "S08"),
    ),
    "contacto": (
        "El correo publicado de Primer Contacto es primercontacto@cutonala.udg.mx. El directorio central muestra 33 2300 2000, extensión 64117, mientras otras páginas del CUT muestran números distintos; confirma el teléfono por correo o en el CAE antes de usarlo para un trámite.",
        ("S06", "S08"),
    ),
    "programa": (
        "Primer Contacto orienta y acompaña a integrantes de la comunidad universitaria que relatan violencia; puede valorar riesgo, ofrecer primera atención y canalizar apoyos psicológicos, médicos o legales, además de recibir y remitir información conforme al reglamento. No determina responsabilidad ni impone sanciones.",
        ("S01", "S05"),
    ),
    "relacion": (
        "Si el posible soborno incluye amenazas, intimidación o necesidad de apoyo por violencia, Primer Contacto es pertinente para orientación y valoración de protección. La norma universitaria también contempla beneficios indebidos por ventajas académicas. Para un soborno sin violencia, conviene pedir que identifiquen la instancia receptora competente; Primer Contacto no es un paso obligatorio antes de consultar a Fiscalía.",
        ("S01", "S03", "S05"),
    ),
    "coordinacion": (
        "Para orientación académica en Ingeniería en Ciencias Computacionales, el directorio publica a Dulce María Vargas Mora, cd.computacion@cutonala.udg.mx, CAE, tercer piso. Puede ayudar a identificar el departamento de la materia. La Secretaría Académica publica a César E. González Coronado, cesar.gonzalez@cutonala.udg.mx, Biblioteca, segundo piso. La coordinación no decide por sí sola una sanción.",
        ("S06", "S11", "S01"),
    ),
    "plazo": (
        "Si cuestionas tu propia calificación, el reglamento prevé solicitar su revisión por escrito y con justificación ante la jefatura del departamento responsable de la materia dentro de tres días hábiles siguientes a la publicación o notificación. Es un trámite distinto de denunciar un posible soborno.",
        ("S04",),
    ),
    "niveles": (
        "Nivel personal: registrar hechos y pedir apoyo si lo necesitas. Nivel UDG: orientación, denuncia disciplinaria y, si corresponde, revisión de la propia evaluación. Nivel legal: asesoría y eventual denuncia ante la autoridad externa competente. Las vías pueden coexistir; no hay que terminar una para comenzar otra.",
        ("S01", "S04", "S10", "S17"),
    ),
    "legal": (
        "La Fiscalía Especializada en Combate a la Corrupción de Jalisco publica un formulario de denuncia con datos opcionales y formatos anónimo y con datos personales. Atiende posibles delitos de corrupción; su sitio está en https://fiscaliaanticorrupcion.jalisco.gob.mx/denuncia. Pedir orientación jurídica no requiere esperar a que concluya el procedimiento universitario. La autoridad decide si los hechos constituyen delito.",
        ("S13", "S17", "S01"),
    ),
    "personal": (
        "Anota fechas, materia, lo solicitado u ofrecido y la ventaja prometida; conserva mensajes completos y originales sin alterarlos ni difundirlos. Si te afecta emocionalmente, la Unidad de Orientación Educativa del CUTonalá publica atención psicológica y ubicación en el CAE, segundo piso.",
        ("S10", "S01"),
    ),
}


def intencion_pregunta(texto: str) -> str | None:
    t = normalizar(texto)
    if "primer contacto" in t and any(x in t for x in ("soborno", "relacion", "caso", "corresponde")):
        return "relacion"
    if any(x in t for x in ("encargad", "responsable", "quien atiende", "quien es")) and "primer contacto" in t:
        return "encargado"
    if any(x in t for x in ("donde", "ubicacion", "encuentro", "direccion", "horario")) and any(x in t for x in ("primer contacto", "oficina", "cae")):
        return "ubicacion"
    if any(x in t for x in ("consiste", "hace el programa", "sirve primer", "funciones del programa")):
        return "programa"
    if any(x in t for x in ("como contacto", "correo", "telefono", "escrib", "comunicarme", "vias de contacto")) and not any(x in t for x in ("soborno", "relacion")):
        return "contacto"
    if any(x in t for x in ("coordinador", "asesoria adicional", "asesor", "carrera")):
        return "coordinacion"
    if any(x in t for x in ("tres niveles", "3 niveles", "personal udg legal")):
        return "niveles"
    if any(x in t for x in ("tres dias", "3 dias", "revisar mi calificacion", "revision de calificacion", "plazo para revisar")):
        return "plazo"
    if any(x in t for x in ("fiscalia", "denuncia penal", "autoridad legal", "via legal", "cohecho")):
        return "legal"
    if any(x in t for x in ("apoyo psicologico", "salud mental", "me siento mal")):
        return "personal"
    return None


def evaluar_hechos(mensaje: str, historial: list[dict[str, str]], anterior: dict[str, int]) -> dict[str, Any]:
    actual = normalizar(mensaje)
    anteriores = " ".join(normalizar(h["mensaje"]) for h in historial if h.get("rol") == "estudiante")
    conjunto = (anteriores + " " + actual).strip()
    indirecto = bool(re.search(r"\b(me contaron|dicen que|escuche que|rumor|se comenta|me dijeron)\b", actual))
    amenaza = bool(re.search(r"\b(amenaz|intimid|golpear|matar|represali|me obliga|me forz)\w*", conjunto))
    amenaza_fisica = bool(re.search(r"\b(golpear|matar|agredir|lastimar|lesionar|pegar)\w*\b|violencia fisica", conjunto))
    amenaza_academica = amenaza and not amenaza_fisica and bool(
        re.search(r"\b(reprob|bajar la nota|bajar la calificacion|quitar puntos|perder la materia)\w*", conjunto)
    )
    beneficio = bool(re.search(r"\b(dinero|pagar|pag[oó]|cobrar|cuota|donaci[oó]n|regalo|botella|transferencia|soborno|mordida)\w*", conjunto))
    evaluacion = bool(re.search(r"\b(calificaci[oó]n|nota|acreditar|aprobar|pasar|reprobar|cien|100|materia|puntos)\b", conjunto))
    intercambio = bool(re.search(r"\b(a cambio de|para sacar|para aprobar|para pasar|si pago|si pagas|si doy|si entrego)\b", conjunto))
    excluye = bool(re.search(r"\b(voluntari[ao]|no afecta|sin relacion con|sin cambiar la nota)\b", actual))
    favoritismo = bool(re.search(r"\b(favoritismo|trato preferencial|cercania|amistad)\b", actual))
    sospecha_intercambio = beneficio and evaluacion and (intercambio or not excluye)
    fuentes: list[str] = []
    rutas: list[str] = []
    razones: list[str] = []
    prioridad = "informativa"
    tipo_riesgo = None
    x, y = anterior["x"], anterior["y"]

    if sospecha_intercambio and not indirecto:
        x, y = max(x, 4), 3
        rutas = ["personal", "UDG", "legal"]
        fuentes.extend(["S01", "S13", "S17"])
        razones.append("Se relata un posible beneficio ligado a una ventaja académica; requiere valoración institucional y jurídica, sin prejuzgar responsabilidad.")
        prioridad = "prioritaria"
    elif indirecto:
        rutas = ["personal"]
        fuentes.append("S01")
        razones.append("El relato es indirecto; conviene aclarar qué se sabe de primera mano antes de atribuir una conducta.")
    elif favoritismo:
        x, y = max(x, 2), max(y, 2)
        rutas = ["personal", "UDG"]
        fuentes.extend(["S04", "S11"])
        razones.append("Se describe posible trato preferencial, sin un beneficio intercambiado identificado. Puede revisarse la evaluación sin clasificarlo como soborno.")
    else:
        rutas = ["personal"] if (x, y) == (1, 1) else ["personal", "UDG"]
        razones.append("Faltan hechos concretos sobre el intercambio para cambiar la clasificación preliminar.")

    if amenaza:
        if amenaza_fisica:
            x, y = 5, 3
            prioridad = "urgente"
            tipo_riesgo = "fisico"
            for ruta in ("personal", "UDG", "legal"):
                if ruta not in rutas:
                    rutas.append(ruta)
            fuentes.extend(["S01", "S17"])
            razones.append("Se relata posible amenaza a la integridad física: solicitar protección inmediata. Si el peligro es actual, acudir a emergencias.")
        elif amenaza_academica:
            x, y = max(x, 4), max(y, 2)
            prioridad = "prioritaria"
            tipo_riesgo = "academico"
            if "UDG" not in rutas:
                rutas.append("UDG")
            fuentes.extend(["S01", "S04"])
            razones.append("Se relata presión mediante una posible represalia académica: documentarla y solicitar valoración de protección y de la evaluación. Esto no equivale por sí solo a peligro físico.")
        else:
            x, y = max(x, 4), max(y, 2)
            prioridad = "prioritaria"
            tipo_riesgo = "sin precisar"
            if "UDG" not in rutas:
                rutas.append("UDG")
            fuentes.append("S01")
            razones.append("Se menciona una amenaza sin precisar su naturaleza: conviene aclararla y solicitar valoración de protección.")

    if re.search(r"\b(publicaron mi nota|publicaron mi calificacion|salio mi calificacion|acaban de publicar)\b", actual):
        if "UDG" not in rutas:
            rutas.append("UDG")
        fuentes.append("S04")
        razones.append("Verifica de inmediato la fecha de publicación: la revisión de la propia evaluación tiene un plazo de tres días hábiles.")

    if indirecto and not amenaza:
        respuesta = "Puedo explicar las opciones sin tratar el comentario como hecho probado. Si alguien conoce un episodio de primera mano, puede pedir orientación y aportar los datos que recuerde."
    elif (x, y) == (1, 1) and not sospecha_intercambio and not amenaza:
        respuesta = "Necesito un dato más para orientar con precisión: ¿se pidió u ofreció algún beneficio a cambio de una ventaja académica, o se trata de una duda sobre la evaluación?"
    else:
        respuesta = (
            "La orientación preliminar abarca " + ", ".join(rutas) + ". "
            + " ".join(razones)
            + " Primer Contacto puede orientar especialmente si hay violencia o riesgo; una denuncia universitaria y una consulta ante Fiscalía pueden coexistir."
        )
    return {
        "coordenadas": {"x": x, "y": y},
        "capa_nombre": CAPAS[y],
        "estado": "Orientación sobre soborno académico" if sospecha_intercambio else "Aclaración de hechos",
        "justificacion": " ".join(razones),
        "respuesta": respuesta,
        "rutas": rutas,
        "prioridad": prioridad,
        "tipo_riesgo": tipo_riesgo,
        "fuentes": list(dict.fromkeys(fuentes)),
    }


def evaluar_transicion_automata(
    mensaje_usuario: str,
    historial: list[dict[str, str]] | None = None,
    estado_anterior: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Contrato compatible con el Sprint 2, ampliado con respuesta y fuentes."""
    anterior = dict(ESTADO_INICIAL if estado_anterior is None else estado_anterior)
    if anterior.get("x") not in range(1, 6) or anterior.get("y") not in CAPAS:
        raise ValueError("Estado anterior fuera del rango del autómata")
    if not mensaje_usuario.strip():
        return {"success": False, "error": "Mensaje vacío", "coordenadas": anterior}
    pregunta = intencion_pregunta(mensaje_usuario)
    if pregunta:
        respuesta, fuentes = FAQ[pregunta]
        resultado = {
            "coordenadas": anterior,
            "capa_nombre": CAPAS[anterior["y"]],
            "estado": "Consulta de información verificada",
            "justificacion": "Respuesta localizada en fichas institucionales y normas citadas.",
            "respuesta": respuesta,
            "rutas": [],
            "prioridad": "informativa",
            "fuentes": list(fuentes),
        }
    else:
        resultado = evaluar_hechos(mensaje_usuario, historial or [], anterior)
    resultado["success"] = True
    resultado["enlaces"] = {clave: FUENTES[clave]["url"] for clave in resultado["fuentes"]}
    return resultado


def explicacion_gemini(mensaje: str, resultado: dict[str, Any]) -> str:
    """Explica la respuesta base con Gemini usando sólo conocimiento curado."""
    clave = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not clave:
        raise RuntimeError("Falta GEMINI_API_KEY o GOOGLE_API_KEY para el modo Gemini")
    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError("Instala la dependencia opcional: python3 -m pip install google-genai") from error
    cliente = genai.Client(api_key=clave)
    modelo = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    prompt = (
        "Eres un orientador académico para una demostración con un caso ficticio de soborno en CUTonalá. "
        "Responde en español en hasta 130 palabras, en lenguaje sencillo. Usa sólo el contexto siguiente. "
        "Mantén los nombres, ubicaciones y contactos tal como aparecen. No atribuyas culpabilidad, "
        "no prometas anonimato ni una sanción, y no conviertas Primer Contacto en paso obligatorio. "
        "Si falta un dato, dilo. Termina con identificadores de fuentes entre corchetes.\n\n"
        f"CONTEXTO DOCUMENTAL:\n{CONOCIMIENTO}\n\n"
        f"PREGUNTA O RELATO FICTICIO:\n{mensaje}\n\n"
        f"EVALUACIÓN PRELIMINAR DETERMINISTA:\n{json.dumps(resultado, ensure_ascii=False)}"
    )
    respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
    if not respuesta.text:
        raise RuntimeError("Gemini no devolvió texto")
    return respuesta.text.strip()


class SesionAutomata:
    def __init__(self) -> None:
        self.historial: list[dict[str, str]] = []
        self.estado = dict(ESTADO_INICIAL)

    def procesar_mensaje(self, texto: str, usar_gemini: bool = False) -> dict[str, Any]:
        resultado = evaluar_transicion_automata(texto, self.historial, self.estado)
        if not resultado["success"]:
            return resultado
        if usar_gemini:
            resultado["respuesta_gemini"] = explicacion_gemini(texto, resultado)
        self.historial.append({"rol": "estudiante", "mensaje": texto})
        self.historial.append({"rol": "autómata", "mensaje": resultado["respuesta"]})
        self.estado = dict(resultado["coordenadas"])
        resultado["memoria_turnos"] = len(self.historial) // 2
        return resultado


def imprimir(resultado: dict[str, Any], con_gemini: bool = False) -> None:
    if not resultado["success"]:
        print("Error:", resultado["error"])
        return
    print("\nOrientación:", resultado["respuesta"])
    if con_gemini:
        print("\nExplicación con Gemini:", resultado["respuesta_gemini"])
    print("Estado:", resultado["estado"], "|", resultado["coordenadas"], "| prioridad:", resultado["prioridad"])
    if resultado["rutas"]:
        print("Vías posibles:", ", ".join(resultado["rutas"]))
    print("Fundamento:", resultado["justificacion"])
    for clave, url in resultado["enlaces"].items():
        print(f"Fuente {clave}: {url}")


DEMO = [
    "¿Quién es la encargada de Primer Contacto en CUTonalá?",
    "¿Dónde encuentro Primer Contacto?",
    "¿Cómo contacto Primer Contacto?",
    "¿En qué consiste el programa de Primer Contacto?",
    "¿Qué relación tiene mi caso de soborno con Primer Contacto?",
    "¿Qué asesoría adicional me puede dar la coordinadora de mi carrera?",
    "Un profesor me pide dinero a cambio de sacar 100 en una materia.",
    "Si no pago, me amenaza con reprobarme.",
]


def main() -> int:
    p = argparse.ArgumentParser(description="Demostración académica de orientación sobre soborno en CUTonalá")
    p.add_argument("--demo", action="store_true", help="ejecuta preguntas y un caso ficticio")
    p.add_argument("--pregunta", help="hace una sola consulta y termina")
    p.add_argument("--gemini", action="store_true", help="añade una explicación del modelo Gemini")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.gemini and not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("Modo Gemini solicitado, pero falta GEMINI_API_KEY o GOOGLE_API_KEY.", file=sys.stderr)
        return 2
    sesion = SesionAutomata()
    preguntas = DEMO if args.demo else [args.pregunta] if args.pregunta else None
    if preguntas is None:
        print("Sprint 3 · Soborno en CUTonalá · Fuente: directorios y normas consultados el 08/10/2026")
        print("Usa un caso ficticio. 'reset' reinicia; 'salir' termina.")
    try:
        while True:
            if preguntas is not None:
                if not preguntas:
                    break
                texto = preguntas.pop(0)
                print("\nEstudiante:", texto)
            else:
                texto = input("\nEstudiante: ").strip()
                if texto.casefold() == "salir":
                    break
                if texto.casefold() == "reset":
                    sesion = SesionAutomata()
                    print("Sesión reiniciada.")
                    continue
            imprimir(sesion.procesar_mensaje(texto, args.gemini), args.gemini)
    except (EOFError, KeyboardInterrupt):
        print("\nDemostración terminada.")
    except Exception as error:
        print(f"Error en la demostración: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

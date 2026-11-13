"""Preguntas frecuentes de Primer Contacto (Sprint 3) y utilidades de texto.

Las seis preguntas de la consigna del Sprint 3 (encargado, ubicación, contacto,
programa, relación con el caso y coordinación) se responden con fichas
institucionales tomadas de la investigación. Las reglas del caso viven en
`automata_soborno.py`; este archivo conserva una demostración por consola del
autómata sin recuperación de documentos.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata

def normalizar(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_acentos).strip()


# Respuestas a las preguntas informativas. Los nombres de instituciones, normas, personas,
# correos y teléfonos se copian exactos de la investigación (capítulos 4–7 y 6.2–6.3).
FAQ: dict[str, tuple[str, tuple[str, ...]]] = {
    "encargado": (
        "El directorio de Secretaría Académica identifica a Blanca Elizabeth González Jauregui como encargada del "
        "despacho de Primer Contacto. El directorio central de la Unidad para la Igualdad también incluye a Valeria "
        "Rubí González Orizaba. La investigación no probó llamadas ni disponibilidad presencial.",
        ("S06", "S08"),
    ),
    "ubicacion": (
        "Primer Contacto está en el Centro de Atención a Estudiantes (CAE) de CUTonalá: al entrar al CAE, primera "
        "puerta a la izquierda, en la oficina compartida con la Defensoría. El domicilio del campus es Av. Nuevo "
        "Periférico 555, Ejido San José Tateposco, C. P. 45425, Tonalá, Jalisco. El directorio central de la Unidad "
        "para la Igualdad señala atención de lunes a viernes, 9:00–15:00 para Blanca y 12:00–19:00 para Valeria; la "
        "página local anuncia atención 9:00–19:00.",
        ("S05", "S08"),
    ),
    "contacto": (
        "El correo publicado de Primer Contacto es primercontacto@cutonala.udg.mx. Para llamar existe una "
        "discrepancia: el directorio de CUT publica 33 2000 2300, mientras el central de Primer Contacto muestra "
        "33 2300 2000, extensión 64117; otras páginas conservan 33 3134 2222. No se selecciona uno como único número "
        "confirmado; el correo institucional y la ubicación publicada son alternativas mientras se verifica el teléfono.",
        ("S06", "S07", "S08"),
    ),
    "programa": (
        "La página de Primer Contacto de CUTonalá presenta sus funciones dentro de la prevención y atención de "
        "violencia: acompañamiento, valoración de riesgo, apoyo emocional, recepción y canalización. El Reglamento de "
        "Responsabilidades Vinculadas con Faltas a la Normatividad Universitaria también regula esta figura y le "
        "atribuye solicitar medidas de protección a la autoridad facultada. Primer Contacto no es el órgano que dicta "
        "una sentencia penal ni garantiza una sanción universitaria.",
        ("S01", "S05"),
    ),
    "relacion": (
        "Cuando el posible soborno se acompaña de amenazas, intimidación o afectaciones al bienestar, la relación con "
        "Primer Contacto es más directa. El artículo 21.1, fracciones X y XI, del Reglamento de Responsabilidades "
        "Vinculadas con Faltas a la Normatividad Universitaria contempla la exigencia o recepción de dinero o bienes "
        "para conceder ventajas académicas y el ofrecimiento, promesa o entrega de beneficios indebidos para "
        "obtenerlas. Para un soborno sin violencia resulta razonable pedir orientación y confirmación del canal de "
        "recepción; también existe la presentación ante las autoridades previstas en el artículo 51.",
        ("S01", "S03", "S05"),
    ),
    "coordinacion": (
        "Coordinación de Ingeniería en Ciencias Computacionales: Dulce María Vargas Mora, cd.computacion@cutonala.udg.mx, "
        "CAE, tercer piso. Es un contacto para orientación académica y localización del departamento de la materia; no "
        "se presenta como autoridad que por sí sola investiga o sanciona el soborno. Secretaría Académica: César E. "
        "González Coronado, cesar.gonzalez@cutonala.udg.mx, edificio de Biblioteca, segundo piso.",
        ("S06", "S11", "S01"),
    ),
    "plazo": (
        "El Reglamento General de Evaluación y Promoción de Alumnos permite solicitar por escrito y con justificación "
        "la revisión de una evaluación ante la jefatura del departamento responsable de la materia, dentro de los tres "
        "días hábiles siguientes a la publicación o notificación. Es un procedimiento académico separado de la denuncia "
        "de un posible soborno.",
        ("S04",),
    ),
    "niveles": (
        "El nivel personal atiende bienestar, comprensión y organización. El nivel universitario atiende evaluación, "
        "disciplina y derechos en la institución. El nivel legal atiende posibles responsabilidades y protección fuera "
        "de ella. No es necesario exigir que primero termine un expediente universitario.",
        ("S01", "S04", "S10", "S17"),
    ),
    "legal": (
        "La Fiscalía Especializada en Combate a la Corrupción de Jalisco publica una página de denuncia con narración "
        "de hechos, adjuntos y datos opcionales, y ofrece formatos para denuncia anónima y con datos personales: "
        "https://fiscaliaanticorrupcion.jalisco.gob.mx/denuncia. Recibe información e investiga posibles delitos de "
        "corrupción; una denuncia no equivale a condena. No es necesario que primero termine un expediente universitario.",
        ("S13", "S17", "S01"),
    ),
    "personal": (
        "Anota fecha aproximada, lugar o plataforma, materia y grupo, el beneficio solicitado u ofrecido y la ventaja "
        "académica mencionada. Conserva originales y copias privadas; no se debe alterar el material ni difundirlo en "
        "grupos abiertos. Si te afecta emocionalmente, la Unidad de Orientación Educativa de CUTonalá publica "
        "orientación psicológica e intervención en crisis en el CAE, segundo piso.",
        ("S10", "S01"),
    ),
}


def intencion_pregunta(texto: str) -> str | None:
    # Formas incompletas o con errores de «Primer Contacto»: «primer co», «primer contato»,
    # «contacto uno», «primercontacto» (D45).
    t = re.sub(r"\bprimer\s*co\w*|\bcontacto\s+(uno|1)\b", "primer contacto", normalizar(texto))
    if "primer contacto" in t and any(x in t for x in ("soborno", "relacion", "caso", "corresponde")):
        return "relacion"
    if any(x in t for x in ("encargad", "responsable", "quien atiende", "quien es")) and "primer contacto" in t:
        return "encargado"
    if any(x in t for x in ("donde", "ubicacion", "ubica", "encuentro", "encontrar", "direccion", "sitio", "lugar",
                            "llego", "llegar", "horario", "atiend", "despach", "abren", "dias"
                            )) and any(x in t for x in ("primer contacto", "oficina", "cae")):
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


def main() -> int:
    """Demostración del autómata por consola, sin recuperación de documentos."""
    from automata_soborno import REGLAS, SesionAutomata

    p = argparse.ArgumentParser(description="Demostración del autómata de soborno académico (sin documentos)")
    p.add_argument("--pregunta", help="procesa un solo mensaje y termina")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sesion = SesionAutomata()
    pendientes = [args.pregunta] if args.pregunta else None
    print("Autómata de soborno académico · CUTonalá. 'reset' reinicia; 'salir' termina.")
    while True:
        if pendientes is not None:
            if not pendientes:
                break
            texto = pendientes.pop(0)
            print("\nEstudiante:", texto)
        else:
            try:
                texto = input("\nEstudiante: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if texto.casefold() == "salir":
                break
            if texto.casefold() == "reset":
                sesion = SesionAutomata()
                print("Sesión reiniciada.")
                continue
        r = sesion.procesar(texto)
        print("Orientación:", r["respuesta"])
        print(f"Estado: {r['estado']} · {r['nombre']} | fase {r['fase']} | prioridad: {r['prioridad']}")
        if r["reglas"]:
            print("Reglas:", ", ".join(f"{x} {REGLAS[x]}" for x in r["reglas"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

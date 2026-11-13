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
    # Formas incompletas o con errores de «Primer Contacto»: «primer co», «primer contato»,
    # «contacto uno», «primercontacto» (D45).
    t = re.sub(r"\bprimer\s*co\w*|\bcontacto\s+(uno|1)\b", "primer contacto", normalizar(texto))
    if "primer contacto" in t and any(x in t for x in ("soborno", "relacion", "caso", "corresponde")):
        return "relacion"
    if any(x in t for x in ("encargad", "responsable", "quien atiende", "quien es")) and "primer contacto" in t:
        return "encargado"
    if any(x in t for x in ("donde", "ubicacion", "encuentro", "direccion", "horario", "atiend", "despach",
                            "abren", "dias")) and any(x in t for x in ("primer contacto", "oficina", "cae")):
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

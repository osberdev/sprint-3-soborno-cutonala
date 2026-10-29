"""Consulta prudente del registro de relatos, separada de la guía de procesos."""

from pathlib import Path
import re

from sprint3_soborno import normalizar


REGISTRO = Path(__file__).resolve().parent / "conocimientos" / "casos_soborno.md"


def pregunta_por_antecedentes(mensaje: str) -> bool:
    """Identifica preguntas de reputación, no relatos nuevos de primera mano."""
    texto = normalizar(mensaje)
    if re.search(r"\b(me pidio|me cobro|me exigio|me ofrecio|me amenazo|si no pago)\b", texto):
        return False
    if re.search(r"\b(primer contacto|revision de calificacion|que sabes de la norma)\b", texto):
        return False
    patrones = (
        r"\b(hay|existen|conoces|sabes de)\b.*\b(profesor|profesores|docente|docentes)\b.*\b(acusad|denunciad|soborno|cobr|pag)\w*",
        r"\b(que|cuales)\b.*\b(profesores|docentes)\b.*\b(acusad|denunciad|soborno)\w*",
        r"\b(que sabes de(?:l| la)?|que opinas de(?:l| la)?|tienes referencias de(?:l| la)?|hay denuncias contra|me conviene agendar con)\b",
        r"\b(profesor|profesora|docente)\b.*\b(tiene denuncias|esta acusado|esta acusada|cobra por|pide dinero por)\b",
    )
    return any(re.search(patron, texto) for patron in patrones)


def resumen_registro() -> tuple[str, list[dict[str, str]]]:
    """Extrae los patrones anónimos que sí constan en el documento individual."""
    contenido = REGISTRO.read_text(encoding="utf-8")
    registros = []
    for identificador in ("C01", "C02"):
        bloque = re.search(rf"^### {identificador}\..*?(?=^### |^## |\Z)", contenido, re.M | re.S)
        if not bloque:
            raise ValueError(f"No se encontró {identificador} en {REGISTRO}")
        conducta = re.search(r"^- \*\*Conducta referida:\*\* (.+)$", bloque.group(), re.M)
        estado = re.search(r"^- \*\*Estado:\*\* (.+)$", bloque.group(), re.M)
        if not conducta or not estado:
            raise ValueError(f"Faltan campos de {identificador} en {REGISTRO}")
        registros.append({"id": identificador, "conducta": conducta.group(1), "estado": estado.group(1)})
    respuesta = (
        "En la investigación individual no hay un caso nominal y verificable de soborno académico "
        "en CUTonalá. Se registraron sin nombres dos comentarios: uno sobre dinero presuntamente "
        "condicionado a una calificación y otro sobre un obsequio presuntamente ligado a acreditar. "
        "No están corroborados y no permiten identificar ni recomendar evitar a un docente. "
        "Si preguntas por una experiencia propia, cuéntame qué te solicitaron y qué ventaja académica "
        "se vinculó con ello; puedo explicarte cómo documentarla y qué vías de orientación existen."
    )
    return respuesta, registros

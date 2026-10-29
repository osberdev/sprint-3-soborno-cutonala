"""Consulta de relatos de clase, con procedencia y estado de cada señalamiento."""

import json
from pathlib import Path
import re

from sprint3_soborno import normalizar


REGISTRO = Path(__file__).resolve().parent / "conocimientos" / "casos_soborno.md"
REGISTRO_IDENTIFICADO = Path(__file__).resolve().parent / "conocimientos" / "casos_docentes.local.json"


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


def _relatos_anonimos() -> list[dict[str, str]]:
    """Extrae los patrones que constan en el documento individual."""
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
    return registros


def cargar_registro_identificado(ruta: Path | None = None) -> list[dict[str, str]]:
    """Los casos con nombre pueden proceder de testimonios de clase, sin resolución oficial."""
    ruta = ruta or REGISTRO_IDENTIFICADO
    if not ruta.exists():
        return []
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    casos = datos.get("casos", [])
    if not isinstance(casos, list):
        raise ValueError(f"El campo 'casos' debe ser una lista en {ruta}")
    obligatorios = ("id", "persona", "conducta", "procedencia", "fecha_registro", "soporte", "estado")
    for caso in casos:
        if not isinstance(caso, dict) or any(not isinstance(caso.get(c), str) or not caso[c].strip() for c in obligatorios):
            raise ValueError(f"Entrada incompleta en {ruta}; revisa los campos obligatorios.")
    return casos


def resumen_registro(mensaje: str = "", ruta_identificados: Path | None = None) -> tuple[str, list[dict[str, str]]]:
    """Nombra a quien figure en un testimonio registrado y explica qué se conoce."""
    anonimos = _relatos_anonimos()
    identificados = cargar_registro_identificado(ruta_identificados)
    consulta = normalizar(mensaje)
    nombrados = [c for c in identificados if normalizar(c["persona"]) in consulta]
    general = bool(re.search(r"\b(hay algun|hay profesores|existen profesores|cuales profesores|que profesores)\b", consulta))
    seleccion = nombrados if nombrados else identificados if general else []
    if seleccion:
        partes = [
            f"{c['persona']}: según {c['procedencia']} (registrado el {c['fecha_registro']}), "
            f"se señaló que {c['conducta']}. Soporte: {c['soporte']}. Estado: {c['estado']}."
            for c in seleccion
        ]
        return (
            "El registro de clase contiene estos señalamientos con su procedencia y estado; "
            "un testimonio no equivale a una resolución de responsabilidad. " + " ".join(partes),
            seleccion,
        )
    if mensaje and not general:
        return (
            "No encontré una entrada sobre esa persona en el registro de soborno de esta clase. "
            "Eso no confirma ni descarta señalamientos fuera de esta base. Si viviste una solicitud "
            "concreta, puedo orientarte sobre cómo documentarla y qué vías existen.",
            [],
        )
    respuesta = (
        "En este módulo constan dos relatos estudiantiles: uno sobre dinero presuntamente condicionado "
        "a una calificación y otro sobre un obsequio presuntamente ligado a acreditar. "
        "Los archivos aportados no vinculan ninguno con un nombre; su origen es indirecto y no están corroborados. "
        "Un testimonio identificado puede incorporarse con su procedencia y estado sin esperar una resolución oficial."
    )
    return respuesta, anonimos

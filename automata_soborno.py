"""Autómata de orientación sobre soborno académico en CUTonalá.

Implementa el diseño aprobado: estados q0–q6 y qS, reglas B1–B17 y preguntas
(1,0) que el usuario responde con sí o no. La tabla TRANSICIONES es la única
fuente de verdad de las flechas del diagrama; el resto del módulo decide qué
regla aplica a cada mensaje y conserva el registro (ficha) del caso.

Decisión y redacción están separadas: este módulo decide el estado y produce una
respuesta local; el chat puede pedir a Gemini que la redacte sin cambiar la ruta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import difflib
import re
from typing import Any

from casos_consulta import pregunta_por_antecedentes
from sprint3_soborno import FAQ, intencion_pregunta, normalizar

# ---------------------------------------------------------------------------
# Estados y transiciones (diagrama aprobado)
# ---------------------------------------------------------------------------

ESTADOS: dict[str, dict[str, Any]] = {
    "q0": {"nombre": "Inicial", "fase": "1/3 Comprender", "nivel": "Sin apoyo",
           "instancia": "Caso sin apoyo", "aceptacion": False, "terminal": False},
    "q1": {"nombre": "Aclaración", "fase": "1/3 Comprender", "nivel": "Sin apoyo",
           "instancia": "Hechos del caso", "aceptacion": False, "terminal": False},
    "q2": {"nombre": "Personal", "fase": "2/3 Orientar en CUTonalá", "nivel": "Personal",
           "instancia": "Unidad de Orientación Educativa · CAE, 2.º piso", "aceptacion": True, "terminal": False},
    "q3": {"nombre": "Primer Contacto", "fase": "2/3 Orientar en CUTonalá", "nivel": "UDG",
           "instancia": "Primer Contacto · CAE, primera puerta a la izquierda", "aceptacion": True, "terminal": False},
    "q4": {"nombre": "Académica", "fase": "2/3 Orientar en CUTonalá", "nivel": "UDG",
           "instancia": "Coordinación de ICC · CAE, 3.er piso → departamento de la materia", "aceptacion": True, "terminal": False},
    "q5": {"nombre": "Autoridad externa", "fase": "3/3 Autoridad externa", "nivel": "Legal",
           "instancia": "Fiscalía Especializada en Combate a la Corrupción de Jalisco", "aceptacion": True, "terminal": True},
    "q6": {"nombre": "Asesoría jurídica", "fase": "3/3 Autoridad externa", "nivel": "Legal",
           "instancia": "Procuraduría Social de Jalisco", "aceptacion": True, "terminal": True},
    "qS": {"nombre": "Seguridad", "fase": "Interrupción", "nivel": "Interrupción",
           "instancia": "Servicios de emergencia · intervención en crisis, CAE 2.º piso", "aceptacion": False, "terminal": False},
}

# (regla, origen) -> destino. "*" significa cualquier estado. Los lazos (B1, B2,
# B4 y B8 en q3) se registran con destino igual al origen.
TRANSICIONES: dict[tuple[str, str], str] = {
    ("B1", "*"): "=",
    ("B2", "*"): "=",
    ("B3", "q0"): "q1",
    ("B4", "q1"): "q1",
    ("B5", "q1"): "q1",          # salida a otro tema del equipo; el estado no cambia
    ("B6", "q1"): "q2",
    ("B7", "q1"): "q3",
    ("B8", "q1"): "q3",
    ("B8", "q3"): "q3",
    ("B9", "q1"): "q4",
    ("B10", "q2"): "q3",
    ("B11", "q3"): "q2",
    ("B12", "q3"): "q4",
    ("B13", "q4"): "q3",
    ("B14", "q3"): "q5",
    ("B15", "q2"): "q6",
    ("B15", "q3"): "q6",
    ("B16", "*"): "qS",
    ("B17", "qS"): "q1",
}

REGLAS = {
    "B1": "Pregunta informativa", "B2": "Consulta sobre docente", "B3": "Relata un caso",
    "B4": "Indirecto o implícito", "B5": "Sin intercambio", "B6": "Afectación personal",
    "B7": "Exigencia u ofrecimiento", "B8": "Amenaza o represalia", "B9": "Nota publicada",
    "B10": "Decide reportar (1,0)", "B11": "Necesita acompañamiento", "B12": "Calificación afectada",
    "B13": "Revela intercambio", "B14": "Acude a autoridad externa (1,0)",
    "B15": "Participación propia (1,0)", "B16": "Peligro actual", "B17": "A salvo",
}

PREGUNTAS = {
    "B10": "¿Quieres orientación para reportarlo en la universidad? Responde sí o no.",
    "B14": "¿Quieres orientación para acudir a la autoridad externa, la Fiscalía Anticorrupción? Responde sí o no.",
    "B15": "¿Quieres orientación sobre asesoría jurídica para tu propia situación antes de declarar? Responde sí o no.",
    "B16": "¿Estás en peligro en este momento? Responde sí o no.",
    "B17": "¿Estás en un lugar seguro ahora? Responde sí o no.",
    # Aclaración dentro de q1 (lazo B4): no es una flecha nueva; un «sí» confirma B7.
    "C1": "¿Ese pago o beneficio estuvo condicionado a una calificación o a otra ventaja académica? Responde sí o no.",
}
REFORMULACION = {
    "C1": "Te lo pregunto de otra forma: ¿se pidió u ofreció algo a cambio de una calificación, de aprobar o de otra "
          "ventaja académica? Responde sí o no.",
}
REPREGUNTA = "Para continuar necesito un sí o un no. Si prefieres no decidir ahora, también está bien: dime «no»."

# Orientación local de cada estado. Todo dato procede de la investigación
# (conocimientos/); los apartados de origen se indican en el comentario.
ORIENTACION = {
    # 4.3 y 6.2
    "q2": ("Lo primero es tu bienestar. La Unidad de Orientación Educativa del CUTonalá ofrece orientación "
           "psicológica e intervención en crisis en el CAE, segundo piso. Si lo deseas, puedes pedir el "
           "acompañamiento de una persona de confianza."),
    # 5.2, 5.3 y 6.2
    "q3": ("Primer Contacto está en el CAE, entrando a la izquierda, primera puerta (primercontacto@cutonala.udg.mx). "
           "Orienta, valora el riesgo y canaliza; la denuncia universitaria la reciben la Secretaría de la División "
           "o la Secretaría Académica. Conserva los mensajes completos y anota fecha, materia y lo que se pidió u ofreció."),
    # 5.6 y 6.2
    "q4": ("La revisión de tu propia calificación se solicita por escrito y con justificación ante la jefatura del "
           "departamento de la materia, dentro de los tres días hábiles siguientes a su publicación. La Coordinación "
           "de ICC (CAE, tercer piso) te ayuda a identificar el departamento. Es un trámite distinto de una denuncia."),
    # 7.3, 7.4 y 6.3
    "q5": ("La Fiscalía Especializada en Combate a la Corrupción de Jalisco recibe denuncias en formato anónimo o con "
           "datos personales. No necesitas terminar el trámite universitario para acudir: ambas vías pueden coexistir. "
           "La autoridad decide si los hechos constituyen delito."),
    # 7.5 y 6.3
    "q6": ("Como participaste en el intercambio, conviene asesoría jurídica independiente antes de cualquier declaración "
           "formal. La Procuraduría Social de Jalisco publica orientación jurídica gratuita (33 3030 2900). Pedir "
           "asesoría no implica culpabilidad y nadie puede garantizarte el resultado de un procedimiento."),
    # 4.1 y 4.3
    "qS": ("Tu seguridad es lo primero. Si hay peligro, aléjate de la situación y acude a los servicios de emergencia. "
           "En el CUTonalá, la Unidad de Orientación Educativa ofrece intervención en crisis en el CAE, segundo piso."),
}
AMENAZA_TEXTO = ("Ante una amenaza o represalia, la normativa universitaria contempla medidas de protección "
                 "(artículos 39 a 46 del reglamento de responsabilidades).")
FUENTES_ESTADO = {"q1": ["S01"], "q2": ["S10"], "q3": ["S01", "S05", "S06"], "q4": ["S04", "S11"],
                  "q5": ["S13", "S17"], "q6": ["S12", "S18"], "qS": ["S01", "S10"]}
SALUDO = r"^(hola|buenas|buenos dias|buenas tardes|buenas noches|que tal|hey)\b"


def destino(regla: str, origen: str) -> str:
    """Aplica la tabla de transiciones; lanza KeyError si la flecha no existe."""
    if (regla, origen) in TRANSICIONES:
        valor = TRANSICIONES[(regla, origen)]
    else:
        valor = TRANSICIONES[(regla, "*")]
    return origen if valor == "=" else valor


# ---------------------------------------------------------------------------
# Extracción local de hechos (reglas por palabras sobre texto normalizado)
# ---------------------------------------------------------------------------

def _hay(patron: str, texto: str) -> bool:
    return re.search(patron, texto) is not None


NEGACION_BENEFICIO = r"\b(no se de|sin|ningun|ninguna|no hubo|no pidio|no me pidio)\s+(\w+\s+){0,2}(pago|dinero|regalo|beneficio|nada)\b"
BENEFICIO = (r"\b(dinero|pesos?|\$\s?\d+|pag(o|os|ar|ue|ado|aba|aste|aron|ara|uen|ando)|le pague|transferencia|deposit\w*"
             r"|botell\w*|regal\w*|obsequi\w*|croquet\w*|aport\w*|cooperacion|donacion|mordida|soborn\w*|cuota\w*)\b")
VENTAJA = (r"\b(aprob\w*|reprob\w*|acredit\w*|pasar|pase|calificacion\w*|notas?|cien|100|puntos?|materia)\b")
NEXO = (r"(a cambio de|para (aprobar|acreditar|pasar|sacar|que me (pase|apruebe|cambie|cambiara|suba|ponga))"
        r"|si no (le )?(doy|pago|entrego|deposito)|quienes (den|aporten|paguen|entreguen)|tendran (100|cien)"
        r"|recibir\w* (puntos|cien|100)|puede cambiar (mi|la|las) (nota|calificacion)|conoce a alguien que puede"
        r"|condicion\w* (a|por|con) (una |la |mi |el )?(calificacion|nota|aprobar|pasar|acreditar)"
        r"|(solo |nada mas )?si (le )?(pagaba|daba|entregaba|pagabamos|dabamos))")
EXIGENCIA = (r"\b(me pidio|me pide|me piden|nos pidio|nos pide|me exig\w*|me cobr\w*|me solicit\w*|dijo que quienes"
             r"|dice que quienes|me dijo que .{0,40}si no)")
OFRECIMIENTO = r"\b(le ofreci|ofreci|le propuse|le di|le entregue|le pague|le regale|le deposite|le transferi|le lleve|acepte pagar)\b"
PAGO_PROPIO = r"\b(pague|le pague|deposite|transferi|le di|le entregue)\b"
PRESION = r"\b(por miedo|por temor|tenia miedo|tuve miedo|me presion\w*|bajo presion|me obligo|me obligaron|me forz\w*)"
AFECTACION = (r"\b(miedo|temor|angusti\w*|ansie\w*|estres\w*|deprim\w*|triste\w*|culpa\w*|no puedo dormir|me siento mal"
              r"|paranoi\w*|desconfi\w*|asustad\w*|preocupad\w*)")
INDIRECTO = (r"\b(se comenta|dicen que|me contaron|escuche que|rumor\w*|se dice|cuentan que|he escuchado|han dicho"
             r"|yo no lo he vivido|no me consta)")
IMPLICITO = (r"\b(insinu\w*|dio a entender|sugiri\w*|indirecta|regalit\w*|detallit\w*|ayudaria con|no estaria mal"
             r"|se agradeceria|uno nunca sabe)")
AMENAZA_FISICA = r"\b(golpe\w*|pegar\w*|agredi\w*|lastim\w*|matar\w*|herir\w*|violencia fisica|hacerme dano|me va a hacer algo)"
PELIGRO_ACTUAL = (r"\b(ahora mismo|en este momento|esta afuera|me esta siguiendo|me sigue|estoy en peligro"
                  r"|me esta esperando|esta aqui)")
AMENAZA = (r"(amenaz\w*|perjudic\w*|obstaculo\w*|si no .{0,40}(reprob\w*|bajar\w*|quitar\w*)"
           r"|(reprob\w*|bajar(me)? la (nota|calificacion)).{0,40}si no|me va a reprobar)")
REPRESALIA = (r"(despues de (reportar|denunciar|quejarme)|desde que (lo )?(reporte|denuncie)|tras reportar|represal\w*"
              r"|me castig\w*|en venganza)")
NOTA_CUESTIONADA = (r"(publicaron mi (nota|calificacion)|salio mi (nota|calificacion)|(nota|calificacion) injusta"
                    r"|me puso (una )?(nota|calificacion)|revisar mi (nota|calificacion)|no estoy de acuerdo con mi (nota|calificacion)"
                    r"|me bajo la (nota|calificacion)|cuestion\w* mi (nota|calificacion)|impugn\w*)")
QUIERE_REPORTAR = r"\b(quiero (reportar|denunciar|hacer algo|levantar una queja)|voy a (reportar|denunciar))"
A_SALVO = r"(estoy a salvo|ya estoy bien|estoy segur[oa]|ya paso|ya no estoy en peligro|estoy en un lugar seguro)"
OTROS_TEMAS = [
    ("acoso sexual", r"\b(sexual\w*|acostarme|tocar\w*|besar\w*|desnud\w*|fotos intimas|sal(ir|ga|iera|ia|gas|iese) con (el|ella|usted))"),
    ("favoritismo", r"\b(favorit\w*|favorece\w*|trato preferencial|preferencia\w*|consentid\w*|cercania|amigo suyo|amiga suya|su amig\w*)"),
    ("cuotas extraordinarias", r"\b(colecta|cooperacion voluntaria|aportacion voluntaria|cuota\w*|donacion voluntaria|voluntari\w*)"),
    ("hostigamiento", r"\b(hostig\w*|humill\w*|me grita\w*|me insulta\w*|acoso)\b"),
]
MODULO_POR_TEMA = {
    "acoso sexual": "acoso sexual",
    "favoritismo": "favoritismo",
    "cuotas extraordinarias": "cuotas extraordinarias",
    "hostigamiento": "hostigamiento",
}


VOCABULARIO = (
    "calificacion calificaciones condicionado condicionada condiciono aprobar acreditar materia profesor profesora "
    "docente dinero amenazo amenaza reprobar reprobarme inscripcion transferencia botella regalo insinuo colecta "
    "voluntaria favoritismo hostiga golpearme represalia publicaron injusta exigio ofreci entregue pague"
).split()


def corregir_escritura(texto: str) -> str:
    """Corrige errores de escritura en palabras clave («calaificacion» → «calificacion»)."""
    palabras = []
    for palabra in texto.split():
        limpia = palabra.strip(".,;:!?¿¡()\"'")
        if len(limpia) >= 6 and limpia not in VOCABULARIO:
            cercana = difflib.get_close_matches(limpia, VOCABULARIO, n=1, cutoff=0.85)
            if cercana:
                palabra = palabra.replace(limpia, cercana[0])
        palabras.append(palabra)
    return " ".join(palabras)


def extraer_hechos(mensaje: str) -> dict[str, Any]:
    """Convierte un mensaje en hechos verificables por las reglas B1–B17."""
    t = corregir_escritura(normalizar(mensaje))
    sin_negaciones = re.sub(NEGACION_BENEFICIO, " ", t)
    beneficio = _hay(BENEFICIO, sin_negaciones)
    ventaja = _hay(VENTAJA, t) and not _hay(r"no (cuenta|afecta|influye|vale) (para|en) la (calificacion|nota)", t)
    nexo = _hay(NEXO, t)
    exigencia = _hay(EXIGENCIA, t)
    ofrecimiento = _hay(OFRECIMIENTO, t)
    presion = _hay(PRESION, t)
    fisica = _hay(AMENAZA_FISICA, t)
    amenaza = _hay(AMENAZA, t) or fisica
    otro_tema = next((nombre for nombre, patron in OTROS_TEMAS if _hay(patron, t)), None)
    if otro_tema == "cuotas extraordinarias" and nexo:
        otro_tema = None  # una aportación condicionada a la nota sí es posible soborno
    if otro_tema in ("favoritismo", "hostigamiento") and beneficio and (nexo or exigencia or ofrecimiento):
        otro_tema = None
    return {
        "texto": t,
        "beneficio": beneficio,
        "ventaja": ventaja,
        "nexo": nexo,
        "exigencia": exigencia and beneficio,
        "ofrecimiento": ofrecimiento and beneficio,
        "pago_propio": _hay(PAGO_PROPIO, t) and beneficio,
        "presion": presion,
        "intercambio": beneficio and ventaja and (nexo or exigencia or ofrecimiento),
        "afectacion": _hay(AFECTACION, t),
        "indirecto": _hay(INDIRECTO, t),
        "implicito": _hay(IMPLICITO, t) and ventaja,
        "amenaza": "fisica" if fisica else ("academica" if amenaza else None),
        "represalia": _hay(REPRESALIA, t),
        "peligro_actual": _hay(PELIGRO_ACTUAL, t),
        "nota_cuestionada": _hay(NOTA_CUESTIONADA, t),
        "quiere_reportar": _hay(QUIERE_REPORTAR, t),
        "a_salvo": _hay(A_SALVO, t),
        "otro_tema": otro_tema,
    }


def _sin_alargamientos(texto: str) -> str:
    """Reduce letras repetidas: «siii» → «si», «noo» → «no» (D28)."""
    return re.sub(r"(\w)\1+", r"\1", texto)


# Respuestas que solo cuentan si son el mensaje completo: «ok gracias» o «va a
# reprobarme» no son un consentimiento (D30).
SI_EXACTO = {_sin_alargamientos(x) for x in ("si", "sip", "sep", "simon", "ok", "okay", "va", "sale", "dale",
                                              "afirmativo", "correcto", "asi es")}
NO_EXACTO = {_sin_alargamientos(x) for x in ("nop", "nope", "nel", "negativo", "para nada")}


def respuesta_si_no(mensaje: str) -> str | None:
    """Interpreta una respuesta (1,0): «si», «no», «no_se» o None si no es respuesta."""
    t = _sin_alargamientos(normalizar(mensaje).strip(" .,!¡¿?"))
    palabras = t.split()
    if not palabras or len(palabras) > 6 or t.startswith("si no "):
        return None
    if t in SI_EXACTO:
        return "si"
    if t in NO_EXACTO:
        return "no"
    if re.match(r"^(no se|no lo se|quiza|tal vez|puede ser|no estoy segur|igual y|no entiendo|no comprendo"
                r"|no me queda claro|a que te refieres|como que)", t):
        return "no_se"
    if re.match(r"^(si|claro|por supuesto|de acuerdo|esta bien)\b", t):
        return "si"
    if re.match(r"^no\b", t):
        return "no"
    return None


# ---------------------------------------------------------------------------
# Registro del caso y sesión
# ---------------------------------------------------------------------------

PARTICIPACION_PROPIA = {"ofrecio", "entrego", "pago_bajo_presion"}


@dataclass
class Ficha:
    procedencia: str | None = None            # "directa" | "indirecta"
    participacion: str | None = None          # "recibio" | "ofrecio" | "entrego" | "pago_bajo_presion"
    ofrecio: bool = False                     # hechos propios; cuentan como participación solo si hay intercambio
    pago: bool = False
    presion: bool = False
    beneficio: bool = False
    intercambio: bool = False
    amenaza: str | None = None                # "academica" | "fisica"
    represalia: bool = False
    peligro_actual: bool | None = None
    nota_cuestionada: bool = False
    afectacion: bool = False
    otro_tema: str | None = None
    implicito: bool = False
    decisiones: dict[str, str] = field(default_factory=dict)   # regla -> "si" | "no" | "desconocido"

    def actualizar(self, h: dict[str, Any]) -> None:
        if h["indirecto"]:
            self.procedencia = self.procedencia or "indirecta"
        elif h["intercambio"] or h["amenaza"] or h["afectacion"]:
            self.procedencia = "directa"
        self.ofrecio |= h["ofrecimiento"]
        self.pago |= h["pago_propio"]
        self.presion |= h["presion"]
        self.beneficio |= h["beneficio"]
        self.intercambio |= h["intercambio"]
        # La participación solo se registra cuando el beneficio está ligado a una ventaja académica:
        # «pagué la inscripción» no es participar en un intercambio (D01).
        if self.intercambio:
            if self.pago or self.ofrecio:
                self.participacion = ("pago_bajo_presion" if self.presion and self.pago
                                      else "entrego" if self.pago else "ofrecio")
            elif h["exigencia"] or self.participacion is None and h["intercambio"]:
                self.participacion = "recibio"
        if h["amenaza"] == "fisica" or (h["amenaza"] and self.amenaza is None):
            self.amenaza = h["amenaza"]
        self.represalia |= h["represalia"]
        self.nota_cuestionada |= h["nota_cuestionada"]
        self.afectacion |= h["afectacion"]
        self.implicito |= h["implicito"]
        if h["otro_tema"]:
            self.otro_tema = h["otro_tema"]

    def como_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class SesionAutomata:
    """Conversación de un caso: estado de control, ficha y pregunta (1,0) pendiente."""

    def __init__(self) -> None:
        self.estado = "q0"
        self.ficha = Ficha()
        self.pendiente: str | None = None
        self.intentos = 0
        self.turnos = 0
        self._nota: str | None = None   # texto que solo corresponde al turno actual
        self._ultima: str | None = None  # última respuesta, para no repetirla literalmente
        self._decidio_no = False          # se respondió «no» a una decisión en este turno

    # -- utilidades -------------------------------------------------------
    def _mover(self, regla: str, reglas: list[str]) -> None:
        self.estado = destino(regla, self.estado)
        reglas.append(regla)

    def _pregunta_del_estado(self) -> str | None:
        propia = self.ficha.participacion in PARTICIPACION_PROPIA
        f = self.ficha
        if self.estado == "q1":
            if (f.beneficio or f.implicito) and not f.intercambio and f.procedencia != "indirecta" \
                    and "C1" not in f.decisiones:
                return "C1"
            return None
        if self.estado == "q2":
            # Cada decisión se pregunta una vez: un «no» a B15 no se vuelve a preguntar (D29).
            regla = "B15" if propia else "B10"
            return regla if regla not in self.ficha.decisiones else None
        if self.estado == "q3":
            if propia and "B15" not in self.ficha.decisiones:
                return "B15"
            if self.ficha.participacion == "recibio" and "B14" not in self.ficha.decisiones:
                return "B14"
        return None

    def _preguntar(self, regla: str | None) -> None:
        if regla != self.pendiente:
            self.intentos = 0
        self.pendiente = regla

    # -- ciclo principal ----------------------------------------------------
    def procesar(self, mensaje: str) -> dict[str, Any]:
        self._nota = None
        self._decidio_no = False
        if not mensaje.strip():
            return self._resultado([], None, None, aviso="Mensaje vacío.")
        reglas: list[str] = []

        # B2: consulta sobre un docente. Es un lazo: no aporta hechos al caso.
        if pregunta_por_antecedentes(mensaje):
            reglas.append("B2")
            return self._resultado(reglas, None, None)
        self.turnos += 1

        h = extraer_hechos(mensaje)

        # B16: peligro actual, desde cualquier estado.
        if h["peligro_actual"] and self.estado != "qS":
            self.ficha.actualizar(h)
            self.ficha.peligro_actual = True
            self._mover("B16", reglas)
            self._preguntar(None)
            return self._resultado(reglas, None, None)

        # Respuesta a la pregunta (1,0) pendiente.
        respuesta = respuesta_si_no(mensaje) if self.pendiente else None
        if respuesta:
            return self._resolver(respuesta, reglas)

        if not self.pendiente and respuesta_si_no(mensaje) and self.estado != "qS":
            self._nota = ("No tengo una pregunta pendiente en este momento. Si algo cambió, cuéntame con tus "
                          "palabras qué pasó; también puedes preguntarme por Primer Contacto.")
            return self._resultado(reglas, None, None)

        # qS: no se hacen preguntas del caso; solo se confirma que la persona está a salvo.
        if self.estado == "qS":
            if h["a_salvo"]:
                self._mover("B17", reglas)
                self._preguntar(None)
            else:
                self._preguntar("B17")
            return self._resultado(reglas, None, None)

        consulta = intencion_pregunta(mensaje)
        if consulta:
            reglas.append("B1")
        narrativos = ("beneficio", "indirecto", "implicito", "amenaza", "represalia", "afectacion",
                      "exigencia", "ofrecimiento")
        # Junto a una pregunta informativa solo cuentan los hechos narrativos: «revisar mi
        # calificación» dentro de una pregunta por el plazo no abre un caso (D11).
        if consulta:
            hay_hechos = any(h[k] for k in narrativos)
        else:
            hay_hechos = any(h[k] for k in narrativos + ("ventaja", "otro_tema", "nota_cuestionada"))
        if consulta and not hay_hechos:
            return self._resultado(reglas, consulta, None)
        if not hay_hechos and self.estado == "q0" and re.match(SALUDO, h["texto"]) and len(h["texto"].split()) <= 4:
            return self._resultado(reglas, None, None, aviso="Hola. Puedes preguntarme por Primer Contacto o contarme qué pasó.")

        if not h["intercambio"] and (self.ficha.beneficio or self.ficha.implicito) and h["ventaja"] and h["nexo"]:
            h["intercambio"] = True
        if self.estado == "q0":
            self._mover("B3", reglas)
        self.ficha.actualizar(h)
        salida = self._aplicar_hechos(h, reglas)
        return self._resultado(reglas, consulta, salida, hechos=h)

    def _aplicar_hechos(self, h: dict[str, Any], reglas: list[str]) -> str | None:
        e = self.estado
        salida = None
        amenaza = h["amenaza"] or h["represalia"]
        if e == "q1":
            if h["otro_tema"] == "acoso sexual":
                self._mover("B5", reglas)
                salida = "otro_tema"
            elif h["indirecto"]:
                self._mover("B4", reglas)
            elif amenaza:
                self._mover("B8", reglas)
            elif h["afectacion"]:
                self._mover("B6", reglas)
            elif h["intercambio"]:
                self._mover("B7", reglas)
            elif h["nota_cuestionada"]:
                self._mover("B9", reglas)
            elif h["otro_tema"]:
                self._mover("B5", reglas)
                salida = "otro_tema"
            elif h["implicito"]:
                self._mover("B4", reglas)
        elif e == "q2":
            if h["quiere_reportar"]:
                self.ficha.decisiones["B10"] = "si"
                self._mover("B10", reglas)
        elif e == "q3":
            if amenaza:
                self._mover("B8", reglas)
            elif h["afectacion"]:
                self._mover("B11", reglas)
            elif h["nota_cuestionada"]:
                self._mover("B12", reglas)
        elif e == "q4":
            if h["intercambio"]:
                self._mover("B13", reglas)

        anterior = self.pendiente
        # Una amenaza física sin indicio de peligro actual: se pregunta si el peligro es actual.
        if h["amenaza"] == "fisica" and self.ficha.peligro_actual is None and self.estado != "qS":
            self._preguntar("B16")
        elif self.pendiente != "B16":
            self._preguntar(self._pregunta_del_estado())
        # Un mensaje que no responde la pregunta pendiente cuenta como un intento: se
        # reformula o se recuerda una vez y después no se insiste (D22, D31).
        if anterior and self.pendiente == anterior and not reglas:
            aviso = self._contar_intento(anterior)
            registrado = any(h[k] for k in ("beneficio", "amenaza", "represalia", "afectacion", "exigencia",
                                            "ofrecimiento", "nota_cuestionada"))
            if registrado:
                aviso = "Queda anotado en tu caso. " + (aviso or "")
            if aviso:
                self._nota = aviso.strip()
        return salida

    def _contar_intento(self, regla: str) -> str | None:
        """Respuesta que no es sí ni no. Devuelve el aviso que acompaña a la pregunta."""
        self.intentos += 1
        if self.intentos < 2:
            # La aclaración se reformula; las decisiones (1,0) recuerdan que se puede decir que no.
            return None if regla in REFORMULACION else REPREGUNTA
        self.ficha.decisiones[regla] = "desconocido"
        if regla == "B16":
            self.ficha.peligro_actual = False
        self._preguntar(None)
        self._preguntar(self._pregunta_del_estado())
        if regla == "C1":
            return ("No pasa nada si no lo tienes claro. Puedo explicarte qué vías existen, o puedes "
                    "contarme más cuando quieras.")
        return "Sin respuesta por ahora; seguimos con lo que sabemos."

    def _resolver(self, respuesta: str, reglas: list[str]) -> dict[str, Any]:
        regla = self.pendiente
        if respuesta == "no_se":
            aviso = self._contar_intento(regla)
            if regla == "C1" and aviso:
                self._nota = aviso
                return self._resultado(reglas, None, None)
            return self._resultado(reglas, None, None, aviso=aviso)
        self.ficha.decisiones[regla] = respuesta
        self._decidio_no = respuesta == "no"
        self._preguntar(None)
        if regla == "C1":
            if respuesta == "no":
                self._nota = ("Entonces no se describe un intercambio por una ventaja académica y no lo trato como "
                              "soborno. Conviene anotar fecha, materia y palabras exactas por si algo cambia; si hay "
                              "algo más, cuéntamelo.")
            if respuesta == "si":
                f = self.ficha
                f.intercambio = True
                f.procedencia = "directa"
                f.participacion = ("pago_bajo_presion" if f.presion and f.pago else "entrego" if f.pago
                                   else "ofrecio" if f.ofrecio else "recibio")
                self._mover("B7", reglas)
            self._preguntar(self._pregunta_del_estado())
            return self._resultado(reglas, None, None)
        if regla == "B16":
            self.ficha.peligro_actual = respuesta == "si"
            if respuesta == "si":
                self._mover("B16", reglas)
                return self._resultado(reglas, None, None)
        elif regla == "B17":
            if respuesta == "si":
                self._mover("B17", reglas)
            else:
                self._preguntar(None)
            return self._resultado(reglas, None, None)
        elif respuesta == "si":
            self._mover(regla, reglas)
        self._preguntar(self._pregunta_del_estado())
        return self._resultado(reglas, None, None)

    # -- salida -------------------------------------------------------------
    def vias_concurrentes(self) -> list[str]:
        f, e = self.ficha, self.estado
        vias = []
        if f.afectacion and e != "q2":
            vias.append("apoyo personal (Unidad de Orientación Educativa)")
        if (f.amenaza or f.represalia) and e not in ("q3", "qS"):
            vias.append("Primer Contacto (protección y medidas)")
        if f.nota_cuestionada and e != "q4":
            vias.append("revisión de la propia calificación (3 días hábiles)")
        if f.intercambio and e in ("q2", "q4"):
            vias.append("denuncia universitaria (Primer Contacto canaliza)")
        return vias

    def componer_respuesta(self, reglas: list[str], consulta: str | None, salida: str | None,
                           aviso: str | None) -> str:
        """Respuesta local del estado. Gemini puede redactarla de nuevo sin cambiar la ruta."""
        f, e = self.ficha, self.estado
        partes: list[str] = []
        if aviso:
            partes.append(aviso)
        if consulta:
            partes.append(FAQ[consulta][0])
        movimiento = [r for r in reglas if r not in ("B1", "B2")]
        # El «de acuerdo» acompaña solo al turno en que se respondió que no (D32).
        decision_negativa = not reglas and self._decidio_no and not aviso
        if salida == "otro_tema":
            texto = (f"Lo que describes no muestra un intercambio de un beneficio por una ventaja académica. "
                     f"Corresponde al tema de {f.otro_tema}, que atiende otro módulo del equipo; aquí oriento solo "
                     f"sobre soborno académico.")
            if f.otro_tema == "acoso sexual":
                texto += " Si hay riesgo o violencia, Primer Contacto (CAE, primera puerta a la izquierda) orienta y acompaña."
            partes.append(texto)
        elif e == "q1" and (movimiento or not consulta):
            if "B17" in reglas:
                partes.append("Me alegra que estés a salvo. Si quieres, retomamos tu caso: cuéntame qué pasó.")
            elif f.procedencia == "indirecta":
                partes.append("Lo que cuentas es un comentario de terceros; no lo trato como un hecho comprobado. "
                              "Si alguien vivió el episodio de primera mano, puede pedir orientación y aportar lo que recuerde.")
            elif self._nota:
                partes.append(self._nota)
            elif self.pendiente == "C1" and self.intentos >= 1:
                pass  # se reformula la pregunta sin repetir la introducción
            elif self.pendiente == "C1" and f.implicito:
                partes.append("Una insinuación puede ser relevante, pero falta saber si hubo una condición concreta.")
            elif self.pendiente == "C1":
                partes.append("Necesito aclarar un dato antes de orientarte.")
            elif not aviso:
                partes.append("Cuéntame qué pasó: quién pidió u ofreció algo, a cambio de qué, y si lo viviste tú.")
        elif self._nota:
            partes.append(self._nota)
        elif e == "qS" and self.pendiente == "B17":
            partes.append("Antes de seguir, necesito saber si estás en un lugar seguro.")
        elif decision_negativa:
            partes.append("De acuerdo. La orientación de esta etapa sigue disponible y puedes decidir más adelante.")
        elif e == "q3" and movimiento == ["B8"] and "B3" not in reglas:
            partes.append("Queda registrado como un hecho nuevo del caso. " + AMENAZA_TEXTO)
        elif e in ORIENTACION and movimiento:
            partes.append(ORIENTACION[e])
            if e == "q3" and (f.amenaza or f.represalia):
                partes.append(AMENAZA_TEXTO)
        if not partes and not self.pendiente:
            partes.append("Sigo aquí. Si hay algo nuevo, cuéntamelo; la orientación de esta etapa sigue disponible.")
        vias = self.vias_concurrentes()
        if vias and e not in ("q0", "q1", "qS") and movimiento:
            partes.append("También puede aplicar: " + "; ".join(vias) + ".")
        if self.pendiente:
            partes.append(self.texto_pregunta())
        texto = " ".join(partes)
        if texto == self._ultima and not reglas:
            if self.pendiente:
                texto = "Sigo esperando tu respuesta: " + self.texto_pregunta()
            elif e in ("q0", "q1"):
                texto = "Sigo atento. Cuando quieras, cuéntame qué pasó o pregúntame por Primer Contacto."
            else:
                texto = "Sigo atento. Si quieres, pregúntame por Primer Contacto o por los plazos de revisión."
        self._ultima = texto
        return texto

    def texto_pregunta(self) -> str | None:
        if not self.pendiente:
            return None
        if self.intentos >= 1 and self.pendiente in REFORMULACION:
            return REFORMULACION[self.pendiente]
        if self.pendiente == "C1" and self.ficha.implicito:
            return "¿Te pidió algo concreto o condicionó la calificación a algo? Responde sí o no."
        return PREGUNTAS[self.pendiente]

    def _resultado(self, reglas: list[str], consulta: str | None, salida: str | None,
                   aviso: str | None = None, hechos: dict[str, Any] | None = None) -> dict[str, Any]:
        info = ESTADOS[self.estado]
        prioridad = ("urgente" if self.estado == "qS" else "informativa" if self.estado in ("q0", "q1")
                     else "prioritaria")
        fuentes = list(FUENTES_ESTADO.get(self.estado, []))
        if consulta:
            fuentes = list(dict.fromkeys(list(FAQ[consulta][1]) + fuentes))
        return {
            "respuesta": self.componer_respuesta(reglas, consulta, salida, aviso),
            "justificacion": " · ".join(f"{r} {REGLAS[r]}" for r in reglas) or "Sin cambio de estado.",
            "prioridad": prioridad,
            "tipo_riesgo": self.ficha.amenaza,
            "fuentes": fuentes,
            "estado": self.estado,
            "nombre": info["nombre"],
            "fase": info["fase"],
            "nivel": info["nivel"],
            "instancia": info["instancia"],
            "aceptacion": info["aceptacion"],
            "reglas": reglas,
            "consulta": consulta,
            "salida": salida,
            "otro_tema": self.ficha.otro_tema if salida else None,
            "pregunta": self.texto_pregunta(),
            "pendiente": self.pendiente,
            "aviso": aviso,
            "vias": self.vias_concurrentes(),
            "ficha": self.ficha.como_dict(),
            "hechos": hechos,
            "turnos": self.turnos,
        }

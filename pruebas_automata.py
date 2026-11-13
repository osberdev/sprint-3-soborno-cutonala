"""Conformidad del autómata con el diagrama aprobado y casos límite; sin servicios externos."""

import ast
import json
from pathlib import Path
import re
import unittest

from automata_soborno import (ESTADOS, FUENTES_ESTADO, PREGUNTAS, REGLAS, TRANSICIONES, SesionAutomata, destino,
                              respuesta_si_no)

RAIZ = Path(__file__).resolve().parent

# Flechas del diagrama aprobado (corrigiendo la versión de Canva: q6 es Asesoría
# jurídica, q5 Autoridad externa, B8 tiene lazo en q3 y B10 es una pregunta (1,0)).
DIAGRAMA = {
    ("B1", "*"): "=", ("B2", "*"): "=", ("B3", "q0"): "q1", ("B4", "q1"): "q1", ("B5", "q1"): "q1",
    ("B6", "q1"): "q2", ("B7", "q1"): "q3", ("B8", "q1"): "q3", ("B8", "q3"): "q3", ("B9", "q1"): "q4",
    ("B10", "q2"): "q3", ("B11", "q3"): "q2", ("B12", "q3"): "q4", ("B13", "q4"): "q3",
    ("B14", "q3"): "q5", ("B15", "q2"): "q6", ("B15", "q3"): "q6", ("B16", "*"): "qS", ("B17", "qS"): "q1",
}


def conversar(*mensajes):
    sesion = SesionAutomata()
    resultado = None
    for mensaje in mensajes:
        resultado = sesion.procesar(mensaje)
    return sesion, resultado


class PruebasConformidad(unittest.TestCase):
    def test_tabla_coincide_con_el_diagrama(self):
        self.assertEqual(TRANSICIONES, DIAGRAMA)

    def test_las_17_reglas_existen_y_tienen_flecha(self):
        self.assertEqual(sorted(REGLAS, key=lambda r: int(r[1:])), [f"B{i}" for i in range(1, 18)])
        self.assertEqual({r for r, _ in TRANSICIONES}, set(REGLAS))

    def test_estados_aceptacion_y_terminales(self):
        self.assertEqual({e for e, i in ESTADOS.items() if i["aceptacion"]}, {"q2", "q3", "q4", "q5", "q6"})
        self.assertEqual({e for e, i in ESTADOS.items() if i["terminal"]}, {"q5", "q6"})
        self.assertEqual(ESTADOS["q6"]["nombre"], "Asesoría jurídica")
        self.assertEqual(ESTADOS["q5"]["nombre"], "Autoridad externa")
        # D36: la fase 3 no repite el nombre de q5.
        self.assertEqual({ESTADOS[q]["fase"] for q in ("q5", "q6")}, {"3/3 Orientar fuera de la UdeG"})

    def test_flecha_inexistente_no_se_inventa(self):
        with self.assertRaises(KeyError):
            destino("B14", "q1")


class PruebasCasosLimite(unittest.TestCase):
    def test_respuestas_si_no(self):
        self.assertEqual(respuesta_si_no("Sí"), "si")
        self.assertEqual(respuesta_si_no("sí, estoy a salvo"), "si")
        self.assertEqual(respuesta_si_no("no"), "no")
        self.assertEqual(respuesta_si_no("no sé"), "no_se")
        self.assertEqual(respuesta_si_no("quizá"), "no_se")
        self.assertIsNone(respuesta_si_no("Si no le pago, me amenaza con reprobarme."))
        self.assertIsNone(respuesta_si_no("Un docente me pidió dinero a cambio de aprobar la materia."))

    def test_no_se_repite_una_vez_y_despues_no_insiste(self):
        sesion, r = conversar("Un docente me pidió dinero a cambio de aprobar la materia.", "no sé")
        self.assertEqual(r["pendiente"], "B14")
        self.assertIn("sí o un no", r["respuesta"])
        r = sesion.procesar("quizá")
        self.assertIsNone(r["pendiente"])
        self.assertEqual(r["estado"], "q3")
        self.assertEqual(r["ficha"]["decisiones"]["B14"], "desconocido")

    def test_pago_ordinario_no_es_participacion_hasta_que_hay_intercambio(self):
        sesion, r = conversar("Ya pagué la inscripción y quiero saber mi calificación.")
        self.assertIsNone(r["ficha"]["participacion"])
        r = sesion.procesar("En realidad el profe me pidió ese pago a cambio de pasarme la materia.")
        self.assertEqual(r["estado"], "q3")
        self.assertEqual(r["ficha"]["participacion"], "entrego")
        self.assertEqual(r["pendiente"], "B15")

    def test_mensaje_mixto_responde_la_pregunta_y_registra_el_relato(self):
        _, r = conversar("¿Dónde está Primer Contacto? Un profe me pidió dinero para pasar.")
        self.assertEqual(r["reglas"], ["B1", "B3", "B7"])
        self.assertEqual(r["consulta"], "ubicacion")
        self.assertEqual(r["estado"], "q3")

    def test_pregunta_informativa_no_aporta_hechos_al_caso(self):
        sesion, r = conversar("¿Dónde encuentro Primer Contacto?")
        self.assertEqual(r["estado"], "q0")
        r = sesion.procesar("¿Cuál es el plazo para revisar mi calificación?")
        self.assertEqual(r["consulta"], "plazo")
        self.assertEqual(r["estado"], "q0")
        self.assertFalse(r["ficha"]["beneficio"])

    def test_peligro_actual_desde_un_estado_terminal(self):
        _, r = conversar("Un docente me pidió dinero a cambio de aprobar la materia.", "sí", "Ahora mismo me está siguiendo.")
        self.assertEqual(r["estado"], "qS")
        self.assertEqual(r["reglas"], ["B16"])

    def test_acoso_sexual_sale_a_otro_tema(self):
        _, r = conversar("El profe me dijo que me pasaba si salía con él.")
        self.assertEqual((r["estado"], r["salida"], r["otro_tema"]), ("q1", "otro_tema", "acoso sexual"))
        self.assertIn("Primer Contacto", r["respuesta"])

    def test_afectacion_en_primer_contacto_lleva_a_personal(self):
        _, r = conversar("Un docente me pidió dinero a cambio de aprobar la materia.", "Estoy muy angustiado.")
        self.assertEqual((r["estado"], r["reglas"]), ("q2", ["B11"]))

    def test_decidir_reportar_desde_personal(self):
        _, r = conversar("Me siento muy mal y con miedo, no sé qué hacer.", "quiero reportar al profesor")
        self.assertEqual((r["estado"], r["reglas"]), ("q3", ["B10"]))

    def test_revision_revela_intercambio(self):
        _, r = conversar("Publicaron mi calificación y creo que es injusta.",
                         "A mí me pidió dinero a cambio de pasar.")
        self.assertEqual((r["estado"], r["reglas"]), ("q3", ["B13"]))

    def test_saludo_no_abre_un_caso(self):
        _, r = conversar("hola")
        self.assertEqual((r["estado"], r["reglas"]), ("q0", []))

    def test_vias_concurrentes_se_conservan(self):
        _, r = conversar("Un docente me pidió dinero para aprobar.",
                         "Además publicaron mi calificación y es injusta.")
        self.assertEqual(r["estado"], "q4")
        self.assertIn("denuncia universitaria", " ".join(r["vias"]))



class PruebasRegresionPruebaManual(unittest.TestCase):
    """Conversación de la prueba manual del 12 de noviembre de 2026 (iteración 2)."""

    def test_aclaracion_con_errores_de_escritura_avanza(self):
        sesion, r = conversar("Ya pagué la inscripción y quiero saber mi calificación.")
        self.assertEqual((r["estado"], r["pendiente"]), ("q1", "C1"))
        r = sesion.procesar("condiciondo por una calaificacion")
        self.assertEqual((r["estado"], r["reglas"], r["pendiente"]), ("q3", ["B7"], "B15"))
        r = sesion.procesar("Si")
        self.assertEqual((r["estado"], r["reglas"]), ("q6", ["B15"]))

    def test_si_responde_la_aclaracion(self):
        _, r = conversar("Ya pagué la inscripción y quiero saber mi calificación.", "Si")
        self.assertEqual((r["estado"], r["reglas"]), ("q3", ["B7"]))

    def test_no_cierra_la_aclaracion_sin_soborno(self):
        sesion, r = conversar("Ya pagué la inscripción y quiero saber mi calificación.", "no")
        self.assertEqual((r["estado"], r["pendiente"]), ("q1", None))
        self.assertIn("no lo trato como soborno", r["respuesta"])
        r = sesion.procesar("ok")
        self.assertNotIn("no lo trato como soborno", r["respuesta"])

    def test_no_entiendo_no_es_un_no(self):
        sesion, r = conversar("Ya pagué la inscripción y quiero saber mi calificación.", "no entiendo")
        self.assertEqual(r["pendiente"], "C1")
        self.assertIn("de otra forma", r["respuesta"])
        r = sesion.procesar("sí")
        self.assertEqual(r["estado"], "q3")

    def test_no_repite_la_misma_pregunta_ni_insiste(self):
        sesion, primera = conversar("Ya pagué la inscripción y quiero saber mi calificación.")
        segunda = sesion.procesar("mmm")
        self.assertNotEqual(primera["respuesta"], segunda["respuesta"])
        tercera = sesion.procesar("mmm")
        self.assertIsNone(tercera["pendiente"])
        self.assertEqual(tercera["ficha"]["decisiones"]["C1"], "desconocido")

    def test_un_no_se_en_primer_contacto_no_repite_la_orientacion(self):
        sesion, r = conversar("Un docente me pidió dinero a cambio de aprobar la materia.")
        orientacion = r["respuesta"].split("¿")[0].strip()
        r = sesion.procesar("no sé")
        self.assertNotIn(orientacion, r["respuesta"])


    def test_si_sin_pregunta_pendiente_no_repite_lo_mismo(self):
        sesion, _ = conversar("Ya pagué la inscripción y quiero saber mi calificación.", "no")
        primera = sesion.procesar("si")
        self.assertIn("No tengo una pregunta pendiente", primera["respuesta"])
        segunda = sesion.procesar("si")
        self.assertNotEqual(primera["respuesta"], segunda["respuesta"])


class PruebasRegresionPruebaManual13Nov(unittest.TestCase):
    """Escenario de prueba del 13 de noviembre de 2026: pago bajo presión, q2 → q6."""

    PAGO = "Le di 500 pesos al profesor porque tenía miedo de reprobar la materia."

    def test_si_alargado_responde_la_decision(self):
        _, r = conversar(self.PAGO, "no se", "sii")
        self.assertEqual((r["estado"], r["reglas"]), ("q6", ["B15"]))

    def test_variantes_de_si_y_no(self):
        for texto, esperado in (("siii", "si"), ("noo", "no"), ("sip", "si"), ("nel", "no"), ("ok", "si"),
                                ("ok gracias", None), ("va a reprobarme", None)):
            with self.subTest(texto=texto):
                self.assertEqual(respuesta_si_no(texto), esperado)

    def test_respuesta_no_reconocida_no_deja_la_respuesta_vacia_ni_insiste(self):
        sesion, r = conversar(self.PAGO, "asdf")
        self.assertEqual(r["pendiente"], "B15")
        self.assertTrue(r["respuesta"].startswith("Para continuar necesito un sí o un no"))
        r = sesion.procesar("asdf")
        self.assertIsNone(r["pendiente"])
        self.assertEqual(r["ficha"]["decisiones"]["B15"], "desconocido")

    def test_un_no_a_b15_no_se_vuelve_a_preguntar(self):
        sesion, r = conversar(self.PAGO, "no")
        self.assertEqual((r["estado"], r["pendiente"]), ("q2", None))
        r = sesion.procesar("ok gracias")
        self.assertEqual(r["estado"], "q2")
        self.assertNotIn("De acuerdo", r["respuesta"])

    def test_salir_de_seguridad_retoma_el_caso_en_su_estado(self):
        sesion, r = conversar(self.PAGO, "sí", "Ahora mismo está afuera del salón esperándome.")
        self.assertEqual(r["estado"], "qS")
        r = sesion.procesar("Ya estoy a salvo.")
        self.assertEqual((r["estado"], r["reglas"], r["pendiente"]), ("q6", ["B17", "B6", "B15"], None))
        self.assertIn("donde lo dejamos", r["respuesta"])
        self.assertNotIn("cuéntame qué pasó", r["respuesta"])

    def test_salir_de_seguridad_conserva_la_decision_sin_responder(self):
        _, r = conversar(self.PAGO, "Ahora mismo está afuera del salón esperándome.", "Ya estoy a salvo.")
        self.assertEqual((r["estado"], r["reglas"], r["pendiente"]), ("q2", ["B17", "B6"], "B15"))

    def test_salir_de_seguridad_sin_caso_pide_el_relato(self):
        _, r = conversar("Ahora mismo me está siguiendo.", "Ya estoy a salvo.")
        self.assertEqual((r["estado"], r["reglas"]), ("q1", ["B17"]))
        self.assertIn("cuéntame qué pasó", r["respuesta"])

    def test_el_camino_retomado_usa_solo_flechas_del_diagrama(self):
        sesion, _ = conversar("Un docente me pidió dinero a cambio de aprobar la materia.", "sí",
                              "Ahora mismo me está siguiendo.")
        origen = sesion.estado
        r = sesion.procesar("sí, estoy a salvo")
        for regla in r["reglas"]:
            origen = destino(regla, origen)  # KeyError si la flecha no existe
        self.assertEqual(origen, r["estado"])
        self.assertEqual(r["estado"], "q5")


class PruebasPreguntaSinDato(unittest.TestCase):
    """Prueba con Gemini del 13 nov 2026: «atienden los sabados?» (D38)."""

    def test_en_q0_no_abre_un_caso(self):
        _, r = conversar("¿atienden los sábados?")
        self.assertEqual((r["estado"], r["reglas"], r["sin_dato"]), ("q0", [], True))
        self.assertTrue(r["respuesta"].startswith("No tengo información oficial"))

    def test_con_pregunta_pendiente_no_cuenta_como_intento(self):
        sesion, _ = conversar("Un docente me pidió dinero a cambio de aprobar la materia.")
        r = sesion.procesar("atienden los sabados?")
        self.assertEqual((r["estado"], r["pendiente"]), ("q3", "B14"))
        self.assertEqual(sesion.intentos, 0)
        r = sesion.procesar("sí")
        self.assertEqual(r["estado"], "q5")

    def test_formas_incompletas_de_primer_contacto_son_pregunta_informativa(self):
        # Prueba del 13 nov 2026 (D45): antes recibían «No tengo información oficial».
        from sprint3_soborno import intencion_pregunta
        for texto in ("donde esta primer co", "donde encuentro contacto uno", "dónde está primer contato",
                      "en primer contacto, atienden los sabados?", "en que sitio encontrar primer contacto puedo"):
            with self.subTest(texto=texto):
                self.assertEqual(intencion_pregunta(texto), "ubicacion")
        self.assertIsNone(intencion_pregunta("despachan los sabados?"))

    def test_pregunta_por_un_lugar_no_abre_un_caso(self):
        # D49: «en que sitio encontrar primer contacto puedo» abría un caso (B3, q1).
        _, r = conversar("en que sitio encontrar primer contacto puedo")
        self.assertEqual((r["estado"], r["reglas"], r["consulta"]), ("q0", ["B1"], "ubicacion"))
        _, r = conversar("en que horario abren la biblioteca")
        self.assertEqual((r["estado"], r["reglas"], r["sin_dato"]), ("q0", [], True))

    def test_expresiones_coloquiales_de_dinero_sin_extractor(self):
        # D50: el extractor de Gemini las detectó; las reglas locales también deben hacerlo.
        for mensaje in ("El profe me dijo que con una lana me pasaba la materia.",
                        "el maestro me dijo qu a cambio de unos billetes me pasaba la materia",
                        "un docente me insinuo que acambio de un favor monetario podria aprobar la materia"):
            with self.subTest(mensaje=mensaje):
                _, r = conversar(mensaje)
                self.assertEqual(r["estado"], "q3")

    def test_dos_preguntas_sin_dato_no_terminan_en_sigo_atento(self):
        # D46: la segunda respuesta igual se sustituía por «Sigo esperando tu respuesta».
        sesion, _ = conversar("Un docente me pidió dinero a cambio de aprobar la materia.", "despachan los sabados?")
        r = sesion.procesar("despachan los domingos?")
        self.assertTrue(r["respuesta"].startswith("Tampoco encuentro ese dato"))
        self.assertEqual(r["pendiente"], "B14")

    def test_una_pregunta_con_hechos_sigue_siendo_un_relato(self):
        _, r = conversar("¿Qué hago si un profe me pidió dinero para pasar?")
        self.assertEqual(r["estado"], "q3")


class PruebasFidelidadDeNombres(unittest.TestCase):
    """Nombres de instituciones y normas exactos e identificables (decisión del 13 nov 2026)."""

    NOMBRE = re.compile(
        r"\b(?:Fiscal[ií]a|Procuradur[ií]a|Defensor[ií]a|Contralor[ií]a|Secretar[ií]a|Coordinaci[oó]n|Unidad|"
        r"Divisi[oó]n|Departamento|Centro|Universidad|Reglamento|Ley|C[oó]digo|Primer Contacto|Ministerio P[uú]blico)"
        r"(?:(?: (?:de la|de los|de las|a la|para la|del|de|en|con|para|y|a))? [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñü]*)*")

    @staticmethod
    def textos_del_codigo(archivo):
        arbol = ast.parse((RAIZ / archivo).read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(arbol)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                      and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        # Se omiten docstrings y expresiones regulares (patrones de búsqueda, no texto mostrado).
        return [n.value for n in ast.walk(arbol)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
                and not re.search(r"\\b|\(\?:|\[A-Z", n.value)]

    def test_cada_nombre_propio_es_un_nombre_completo_de_la_investigacion(self):
        investigacion = "\n".join(p.read_text(encoding="utf-8")
                                  for p in sorted((RAIZ / "conocimientos").glob("*.md")))
        # Nombres completos tal como aparecen en la investigación: «Fiscalía Anticorrupción»
        # no vale, porque allí siempre continúa («… de Jalisco»).
        completos = {m.group(0) for m in self.NOMBRE.finditer(investigacion)}
        # «Centro de Atención a Estudiantes y CRT» enumera dos nombres.
        completos |= {n.split(" y ")[0] for n in completos}
        for archivo in ("automata_soborno.py", "sprint3_soborno.py", "gemini_soborno.py"):
            for texto in self.textos_del_codigo(archivo):
                for nombre in (m.group(0) for m in self.NOMBRE.finditer(texto)):
                    with self.subTest(archivo=archivo, nombre=nombre):
                        self.assertIn(nombre, completos)

    def test_pregunta_b14_nombra_la_fiscalia_completa(self):
        self.assertIn("Fiscalía Especializada en Combate a la Corrupción de Jalisco", PREGUNTAS["B14"])

    def test_las_referencias_existen_en_fuentes(self):
        fuentes = json.loads((RAIZ / "fuentes.json").read_text(encoding="utf-8"))["fuentes"]
        from sprint3_soborno import FAQ
        citadas = {s for _, ids in FAQ.values() for s in ids} | {s for ids in FUENTES_ESTADO.values() for s in ids}
        self.assertLessEqual(citadas, set(fuentes))


class PruebasHipotesisYPagos(unittest.TestCase):
    """D42 (preguntas hipotéticas), D47 (pagos ordinarios) y D52 (verbos con cambio de raíz)."""

    RELATO = "Un docente me pidió dinero a cambio de aprobar la materia."

    def test_una_pregunta_hipotetica_no_se_registra_como_hecho(self):
        sesion, r = conversar(self.RELATO, "¿Y si me amenaza con reprobarme?")
        self.assertEqual((r["estado"], r["reglas"], r["pendiente"], r["hipotetica"]), ("q3", [], "B14", True))
        self.assertIsNone(r["ficha"]["amenaza"])
        self.assertIn("no lo registro", r["respuesta"])
        self.assertIn("artículos 39–46", r["respuesta"])
        self.assertEqual(sesion.procesar("sí")["estado"], "q5")  # la pregunta pendiente sigue en pie

    def test_una_hipotesis_no_abre_un_caso(self):
        for mensaje in ("¿Y si un profe me pide dinero para pasar?",
                        "¿Qué pasaría si le ofreciera dinero al profe para que me pase?",
                        "En caso de que me pida dinero, ¿qué hago?"):
            with self.subTest(mensaje=mensaje):
                _, r = conversar(mensaje)
                self.assertEqual((r["estado"], r["reglas"], r["hipotetica"]), ("q0", [], True))

    def test_lo_ocurrido_no_se_confunde_con_una_hipotesis(self):
        for mensaje in ("¿Qué hago si un profe me pidió dinero para pasar?",
                        "Me pidió dinero y si no le pago me reprueba."):
            with self.subTest(mensaje=mensaje):
                _, r = conversar(mensaje)
                self.assertEqual((r["estado"], r["hipotetica"]), ("q3", False))

    def test_pago_ordinario_no_cambia_la_participacion(self):
        _, r = conversar(self.RELATO, "Ya pagué la inscripción y quiero saber mi calificación.")
        self.assertEqual((r["ficha"]["participacion"], r["pendiente"]), ("recibio", "B14"))
        self.assertNotIn("Queda anotado", r["respuesta"])

    def test_pago_vinculado_despues_si_es_participacion(self):
        _, r = conversar(self.RELATO, "Ya le pagué lo que me pidió.")
        self.assertEqual((r["ficha"]["participacion"], r["pendiente"]), ("entrego", "B15"))

    def test_verbos_con_cambio_de_raiz(self):
        for mensaje in ("Me pidió dinero y si no le pago me reprueba.", "El profe dice que si le pagas te aprueba."):
            with self.subTest(mensaje=mensaje):
                _, r = conversar(mensaje)
                self.assertEqual(r["estado"], "q3")


class PruebasCausaBenefica(unittest.TestCase):
    """Prueba manual del 13 nov 2026: «… 100 pesos para pasar … para darle de comer a los perritos» (D53, D54)."""

    def test_una_causa_no_cambia_el_intercambio_y_se_explica(self):
        _, r = conversar("el profesor me pidio 100 pesos para pasar la materia supuestamente para darle de comer "
                         "a los perritos")
        self.assertEqual((r["estado"], r["reglas"]), ("q3", ["B3", "B7"]))
        self.assertIn("Una causa benéfica no autoriza cambiar los criterios de acreditación.", r["respuesta"])

    def test_sin_intercambio_la_causa_no_se_menciona(self):
        _, r = conversar("Organizan una colecta voluntaria de croquetas para los animales del campus; no cuenta para "
                         "la calificación.")
        self.assertNotIn("Una causa benéfica", r["respuesta"])

    def test_cien_pesos_no_es_una_calificacion(self):
        # «100 pesos» es un monto; sin ventaja académica el bot solo aclara (C1), no presume una nota.
        _, r = conversar("Le presté 100 pesos a un compañero.")
        self.assertFalse(r["hechos"]["ventaja"])
        self.assertEqual(r["estado"], "q1")
        _, r = conversar("El profesor dijo que quienes den 200 pesos tendrán 100 en la materia.")
        self.assertEqual(r["estado"], "q3")


if __name__ == "__main__":
    unittest.main(verbosity=2)

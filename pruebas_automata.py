"""Conformidad del autómata con el diagrama aprobado y casos límite; sin servicios externos."""

import unittest

from automata_soborno import ESTADOS, REGLAS, TRANSICIONES, SesionAutomata, destino, respuesta_si_no

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


if __name__ == "__main__":
    unittest.main(verbosity=2)

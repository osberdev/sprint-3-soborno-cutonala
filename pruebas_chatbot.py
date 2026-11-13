"""Pruebas de integración del módulo individual; no realizan llamadas a Gemini."""

import unittest
from unittest.mock import patch

from chatbot_soborno import Buscador, ChatSoborno, FUENTES


class PruebasSprint3(unittest.TestCase):
    def test_base_solo_incluye_apartados_pertinentes_de_la_investigacion(self):
        fragmentos = Buscador().fragmentos
        self.assertGreater(len(fragmentos), 60)
        capitulos = {f["apartado"].split(".")[0] for f in fragmentos}
        # Metodología, escenarios ficticios, casos ajenos, evaluación web, diseño
        # del prototipo, conclusiones y referencias no se recuperan (D04).
        self.assertFalse(capitulos & {"1", "9", "10", "11", "12", "13", "15"})
        self.assertFalse(any(f["apartado"] == "14.4" for f in fragmentos))
        self.assertTrue(all(f["archivo"] and f["estados"] for f in fragmentos))

    def test_pregunta_de_ubicacion_recupera_el_directorio(self):
        respuesta = ChatSoborno().responder("¿Dónde encuentro Primer Contacto en CUTonalá?")
        self.assertIn("CAE", respuesta["respuesta_chatbot"])
        self.assertTrue(any("Primer Contacto" in f["texto"] and "CAE" in f["texto"]
                            for f in respuesta["fragmentos"]))
        self.assertIn("S05", respuesta["fuentes_consultadas"])

    def test_comentario_sobre_persona_no_se_convierte_en_hecho(self):
        respuesta = ChatSoborno().responder("Se comenta que el profesor X aprueba por regalos")
        self.assertEqual(respuesta["estado"], "q1")
        self.assertIn("B4", respuesta["reglas"])
        self.assertEqual(respuesta["ficha"]["procedencia"], "indirecta")
        self.assertIn("comentario", respuesta["respuesta_chatbot"])

    def test_relato_directo_y_represalia_academica_conservan_estado(self):
        chat = ChatSoborno()
        inicial = chat.responder("Un docente me pidió una botella a cambio de acreditar la materia")
        self.assertEqual(inicial["estado"], "q3")
        self.assertEqual(inicial["reglas"], ["B3", "B7"])
        self.assertEqual(inicial["pendiente"], "B14")
        self.assertTrue(any(f["titulo"].startswith("5.1") for f in inicial["fragmentos"]))
        continuacion = chat.responder("Si no se la doy, me amenaza con reprobarme")
        self.assertEqual(continuacion["estado"], "q3")
        self.assertEqual(continuacion["reglas"], ["B8"])
        self.assertEqual(continuacion["tipo_riesgo"], "academica")
        self.assertEqual(continuacion["prioridad"], "prioritaria")
        self.assertEqual(continuacion["pendiente"], "B14")
        self.assertNotIn("acudir a emergencias", continuacion["respuesta_chatbot"])
        self.assertEqual(continuacion["memoria_turnos"], 2)
        self.assertTrue(any(f["titulo"].startswith("5.5") for f in continuacion["fragmentos"]))

    def test_pago_ya_realizado_en_pesos_se_reconoce(self):
        chat = ChatSoborno()
        respuesta = chat.responder(
            "Un docente me pidió 100 pesos para croquetas a cambio de ponerme 100 en la materia; "
            "pagué y la calificación quedó registrada. ¿Cómo puedo proceder?"
        )
        self.assertEqual(respuesta["estado"], "q3")
        self.assertEqual(respuesta["prioridad"], "prioritaria")
        # Pagó lo que se le pidió: participación propia, se ofrece asesoría jurídica (B15).
        self.assertEqual(respuesta["ficha"]["participacion"], "entrego")
        self.assertEqual(respuesta["pendiente"], "B15")

    def test_amenaza_fisica_si_activa_orientacion_inmediata(self):
        chat = ChatSoborno()
        chat.responder("Un docente me pidió dinero a cambio de aprobar la materia")
        respuesta = chat.responder("Si no pago, me amenaza con golpearme")
        self.assertEqual(respuesta["estado"], "q3")
        self.assertEqual(respuesta["tipo_riesgo"], "fisica")
        self.assertEqual(respuesta["pendiente"], "B16")
        urgente = chat.responder("sí")
        self.assertEqual(urgente["estado"], "qS")
        self.assertEqual(urgente["prioridad"], "urgente")
        self.assertIn("servicios de emergencia", urgente["respuesta_chatbot"])

    def test_todos_los_enlaces_tienen_fuente_identificada(self):
        respuesta = ChatSoborno().responder("¿Cuál es el plazo para revisar mi calificación?")
        self.assertIn("tres días hábiles", respuesta["respuesta_chatbot"])
        self.assertTrue(respuesta["fuentes_consultadas"])
        self.assertTrue(all(clave in FUENTES for clave in respuesta["fuentes_consultadas"]))

    def test_modo_gemini_conserva_la_pregunta_pendiente(self):
        chat = ChatSoborno()
        with patch("chatbot_soborno.redactar", return_value=("Texto redactado por Gemini.", [])):
            respuesta = chat.responder("Un docente me pidió dinero a cambio de aprobar", gemini=True)
        self.assertEqual(respuesta["modo"], "Gemini + autómata + documentos")
        self.assertTrue(respuesta["respuesta_chatbot"].startswith("Texto redactado por Gemini."))
        self.assertTrue(respuesta["respuesta_chatbot"].endswith(respuesta["pregunta"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Pruebas de integración del módulo individual; no realizan llamadas a Gemini."""

import os
import sys
import types
import unittest
from unittest.mock import patch

from chatbot_soborno import Buscador, ChatSoborno, FUENTES, explicar_con_gemini


class PruebasSprint3(unittest.TestCase):
    def test_base_solo_incluye_apartados_pertinentes_de_la_investigacion(self):
        fragmentos = Buscador().fragmentos
        self.assertGreater(len(fragmentos), 60)
        self.assertFalse(any(f["titulo"].startswith("2.") for f in fragmentos))
        self.assertFalse(any(f["titulo"].startswith("9.") for f in fragmentos))
        self.assertFalse(any(f["titulo"].startswith("10.") for f in fragmentos))

    def test_pregunta_de_ubicacion_recupera_el_directorio(self):
        respuesta = ChatSoborno().responder("¿Dónde encuentro Primer Contacto en CUTonalá?")
        self.assertIn("CAE", respuesta["respuesta_chatbot"])
        self.assertTrue(any("Primer Contacto" in f["texto"] and "CAE" in f["texto"]
                            for f in respuesta["fragmentos"]))
        self.assertIn("S05", respuesta["fuentes_consultadas"])

    def test_comentario_sobre_persona_no_se_convierte_en_hecho(self):
        respuesta = ChatSoborno().responder("Se comenta que el profesor X aprueba por regalos")
        self.assertIn("indirecto", respuesta["justificacion"])
        self.assertNotIn("legal", respuesta["rutas"])
        self.assertIn("comentario", respuesta["respuesta_chatbot"])

    def test_relato_directo_y_represalia_academica_conservan_estado(self):
        chat = ChatSoborno()
        inicial = chat.responder("Un docente me pidió una botella a cambio de acreditar la materia")
        self.assertEqual(inicial["coordenadas"], {"x": 4, "y": 3})
        self.assertIn("UDG", inicial["rutas"])
        self.assertIn("legal", inicial["rutas"])
        self.assertTrue(any(f["titulo"].startswith("5.1") for f in inicial["fragmentos"]))
        continuacion = chat.responder("Si no se la doy, me amenaza con reprobarme")
        self.assertEqual(continuacion["coordenadas"], {"x": 4, "y": 3})
        self.assertEqual(continuacion["tipo_riesgo"], "academico")
        self.assertEqual(continuacion["prioridad"], "prioritaria")
        self.assertNotIn("acudir a emergencias", continuacion["respuesta_chatbot"])
        self.assertEqual(continuacion["memoria_turnos"], 2)
        self.assertTrue(any(f["titulo"].startswith("5.5") for f in continuacion["fragmentos"]))

    def test_amenaza_fisica_si_activa_orientacion_inmediata(self):
        chat = ChatSoborno()
        chat.responder("Un docente me pidió dinero a cambio de aprobar la materia")
        respuesta = chat.responder("Si no pago, me amenaza con golpearme")
        self.assertEqual(respuesta["coordenadas"], {"x": 5, "y": 3})
        self.assertEqual(respuesta["tipo_riesgo"], "fisico")
        self.assertEqual(respuesta["prioridad"], "urgente")

    def test_todos_los_enlaces_tienen_fuente_identificada(self):
        respuesta = ChatSoborno().responder("¿Cuál es el plazo para revisar mi calificación?")
        self.assertIn("tres días hábiles", respuesta["respuesta_chatbot"])
        self.assertTrue(respuesta["fuentes_consultadas"])
        self.assertTrue(all(clave in FUENTES for clave in respuesta["fuentes_consultadas"]))

    def test_conexion_gemini_se_integra_sin_enviar_informe_completo(self):
        llamadas = []

        class ClienteFalso:
            def __init__(self, api_key, http_options):
                self.interactions = self

            def create(self, **kwargs):
                llamadas.append(kwargs)
                return types.SimpleNamespace(output_text="Orientación de prueba [S1][S2].")

        modulo_google = types.ModuleType("google")
        modulo_google.genai = types.SimpleNamespace(Client=ClienteFalso)
        modulo_google_genai = types.ModuleType("google.genai")
        modulo_google_genai.types = types.SimpleNamespace(
            HttpRetryOptions=lambda **kwargs: kwargs,
            HttpOptions=lambda **kwargs: kwargs,
        )
        chat = ChatSoborno()
        estado = chat.sesion.procesar_mensaje("Un docente me pidió dinero a cambio de aprobar")
        fragmentos = chat.buscador.buscar("Un docente me pidió dinero a cambio de aprobar", estado)
        with patch.dict(sys.modules, {"google": modulo_google, "google.genai": modulo_google_genai}), patch.dict(
            os.environ, {"GEMINI_API_KEY": "clave_ficticia_para_prueba"}
        ):
            respuesta = explicar_con_gemini("Un docente me pidió dinero a cambio de aprobar", estado, fragmentos, [])
        self.assertEqual(respuesta, "Orientación de prueba.")
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(llamadas[0]["model"], "gemini-3.5-flash-lite")
        self.assertEqual(llamadas[0]["timeout"], 12)
        self.assertIn("SALIDA DEL AUTÓMATA", llamadas[0]["input"])
        self.assertIn("FRAGMENTOS RECUPERADOS", llamadas[0]["input"])
        self.assertIn("No escribas citas", llamadas[0]["input"])
        self.assertLess(len(llamadas[0]["input"]), 15000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

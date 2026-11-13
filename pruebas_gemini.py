"""Pruebas de la iteración 4 (Gemini). Ninguna llama al servicio: `generar` se sustituye."""

import json
import os
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import patch

import gemini_soborno
from sprint3_soborno import normalizar
from automata_soborno import ORIENTACION, SesionAutomata
from chatbot_soborno import ChatSoborno
from escenarios_aceptacion import ESCENARIOS
from gemini_soborno import (ECO_DE_INSTRUCCIONES, ESQUEMA_HECHOS, INSTRUCCION_REDACCION, MODELO_POR_DEFECTO, ExtractorGemini,
                            interpretar_extraccion, limpiar_redaccion, verificar_fundamento)

RAIZ = Path(__file__).resolve().parent
RELATO = "El profesor Ramírez me pidió 500 pesos a cambio de aprobar la materia."


class GeminiFalso:
    """Sustituye a `gemini_soborno.generar` y guarda lo que se le habría enviado."""

    def __init__(self, salida):
        self.salida = salida
        self.llamadas: list[dict] = []

    def __call__(self, entrada, instruccion, esquema=None):
        self.llamadas.append({"entrada": entrada, "instruccion": instruccion, "esquema": esquema})
        return self.salida(entrada) if callable(self.salida) else self.salida


def base_de(entrada: str) -> str:
    """La orientación base que viaja en la tarjeta: una redacción que solo la reordena es fundamentada."""
    tarjeta = json.loads(entrada.split("TARJETA DEL ESTADO\n", 1)[1].split("\n\nCONTEXTO", 1)[0])
    return tarjeta["orientacion_base"].split("\nDato recuperado")[0]


class PruebasConfiguracion(unittest.TestCase):
    def test_una_sola_configuracion_del_modelo(self):
        # D10: el nombre del modelo de texto solo aparece en gemini_soborno.py.
        for ruta in RAIZ.glob("*.py"):
            if ruta.name in ("gemini_soborno.py", "pruebas_gemini.py"):
                continue
            with self.subTest(archivo=ruta.name):
                self.assertIsNone(re.search(r"gemini-\d", ruta.read_text(encoding="utf-8")))

    def test_peticion_sin_guardado_y_con_salida_estructurada(self):
        llamadas = []

        class ClienteFalso:
            def __init__(self, api_key, http_options):
                self.interactions = self

            def create(self, **kwargs):
                llamadas.append(kwargs)
                return types.SimpleNamespace(output_text='{"hechos": []}')

        google = types.ModuleType("google")
        google.genai = types.SimpleNamespace(Client=ClienteFalso)
        genai = types.ModuleType("google.genai")
        genai.types = types.SimpleNamespace(HttpRetryOptions=lambda **k: k, HttpOptions=lambda **k: k)
        with patch.dict(sys.modules, {"google": google, "google.genai": genai}), \
                patch.dict(os.environ, {"GEMINI_API_KEY": "clave_ficticia"}, clear=False):
            os.environ.pop("GEMINI_MODEL", None)
            gemini_soborno.generar("entrada", "instrucción", ESQUEMA_HECHOS)
        peticion = llamadas[0]
        self.assertEqual(peticion["model"], MODELO_POR_DEFECTO)
        self.assertEqual((peticion["timeout"], peticion["store"]), (12, False))
        self.assertEqual(peticion["generation_config"], {"temperature": 0.2})
        self.assertEqual(peticion["system_instruction"], "instrucción")
        self.assertEqual(peticion["response_format"]["mime_type"], "application/json")
        self.assertEqual(peticion["response_format"]["schema"], ESQUEMA_HECHOS)


class PruebasRedaccion(unittest.TestCase):
    def test_no_envia_mensajes_ni_historial(self):
        # D07: Gemini recibe hechos del caso en frases neutras, nunca el texto del estudiante.
        falso = GeminiFalso(base_de)
        chat = ChatSoborno()
        with patch("gemini_soborno.generar", falso):
            chat.responder("¿Dónde encuentro Primer Contacto?", gemini=True)
            chat.responder(RELATO, gemini=True)
        entrada = falso.llamadas[-1]["entrada"]
        for privado in ("Ramírez", "500", "Dónde encuentro"):
            self.assertNotIn(privado, entrada)
        self.assertIn("Se describe un beneficio a cambio de una ventaja académica.", entrada)
        self.assertIn("Primer Contacto", entrada)  # D19: q3 es el estado central del nivel UDG

    def test_instruccion_breve_y_en_positivo(self):
        # D08 y D19: sin listas de prohibiciones ni la regla que ocultaba Primer Contacto.
        reglas = [l for l in INSTRUCCION_REDACCION.splitlines() if re.match(r"\d+\.", l)]
        self.assertLessEqual(len(reglas), 8)
        self.assertFalse(any(re.match(r"\d+\.\s+No\b", l) for l in reglas))
        self.assertNotIn("No menciones Primer Contacto", INSTRUCCION_REDACCION)
        self.assertIn("no tienes información oficial", INSTRUCCION_REDACCION)  # regla del profesor

    def test_redaccion_fundamentada_se_muestra_con_la_pregunta_al_final(self):
        chat = ChatSoborno()
        with patch("gemini_soborno.generar", GeminiFalso(base_de)):
            r = chat.responder(RELATO, gemini=True)
        self.assertEqual(r["modo"], "Gemini + autómata + documentos")
        self.assertEqual(r["gemini_no_fundamentado"], [])
        self.assertTrue(r["respuesta_chatbot"].endswith(r["pregunta"]))

    def test_datos_inventados_hacen_volver_a_la_respuesta_local(self):
        trampas = {
            "correo": "Escribe a denuncias.soborno@udg.mx para reportarlo.",
            "teléfono": "Llama al 33 1234 5678 para pedir una cita.",
            "instancia": "Acude a la Fiscalía Anticorrupción Universitaria.",
            "plazo en cifras": "Tienes 15 días hábiles para presentar tu escrito.",
            "plazo en palabras": "Tienes quince días hábiles para presentar tu escrito.",
            "enlace": "Llena el formulario en https://denuncias.cutonala.udg.mx hoy mismo.",
            "artículo": "El artículo 87 del reglamento te protege.",
        }
        for nombre, invento in trampas.items():
            with self.subTest(trampa=nombre):
                local = ChatSoborno().responder(RELATO)
                chat = ChatSoborno()
                with patch("gemini_soborno.generar", GeminiFalso(lambda e: base_de(e) + " " + invento)):
                    r = chat.responder(RELATO, gemini=True)
                self.assertTrue(r["gemini_no_fundamentado"])
                self.assertTrue(r["modo"].startswith("Local"))
                self.assertEqual(r["respuesta_chatbot"], local["respuesta_chatbot"])

    def test_pregunta_informativa_trampa(self):
        # Una pregunta sin dato en la base: inventar un horario se detecta; admitirlo no.
        chat = ChatSoborno()
        with patch("gemini_soborno.generar", GeminiFalso("Primer Contacto atiende los sábados de 8:00 a 11:00.")):
            r = chat.responder("¿Dónde encuentro Primer Contacto?", gemini=True)
        self.assertIn("8:00", " ".join(r["gemini_no_fundamentado"]))
        honesta = "No tengo información oficial sobre atención en sábado; Primer Contacto está en el CAE."
        with patch("gemini_soborno.generar", GeminiFalso(honesta)):
            r = ChatSoborno().responder("¿Dónde encuentro Primer Contacto?", gemini=True)
        self.assertEqual(r["gemini_no_fundamentado"], [])

    def test_parafrasis_de_datos_reales_es_fundamentada(self):
        soporte = ["El reglamento prevé solicitar la revisión dentro de tres días hábiles. "
                   "La Unidad de Orientación Educativa de CUTonalá está en el CAE. Tel. 33 3030 2900."]
        texto = ("Tienes 3 días hábiles para pedir la revisión. La Unidad de Orientación Educativa del "
                 "CUTonalá te atiende; su teléfono es 33 3030 2900.")
        self.assertEqual(verificar_fundamento(texto, soporte), [])

    def test_pregunta_final_de_gemini_se_omite(self):
        self.assertEqual(limpiar_redaccion("Acude a Primer Contacto. ¿Quieres saber más?"),
                         "Acude a Primer Contacto.")
        self.assertEqual(limpiar_redaccion("Orientación [S05] de prueba **clave**."), "Orientación de prueba clave.")

    def test_eco_de_las_instrucciones_se_omite(self):
        # Oraciones reales de la prueba manual del 13 nov 2026 (D39, D40).
        texto = ("Sobre lo que relatas en esta etapa inicial, Primer Contacto está en el CAE. "
                 "En esta etapa de primer contacto, recuerda que esta orientación no es una denuncia ni una "
                 "decisión jurídica. Acude a Primer Contacto. Esta orientación no constituye una denuncia "
                 "formal ni una decisión jurídica sobre los hechos. El programa añade después, por separado, "
                 "la pregunta del turno.")
        self.assertEqual(limpiar_redaccion(texto), "Acude a Primer Contacto.")

    def test_la_orientacion_local_no_se_confunde_con_un_eco(self):
        for estado, texto in ORIENTACION.items():
            for oracion in re.split(r"(?<=[.!?])\s+", texto if isinstance(texto, str) else " ".join(texto)):
                with self.subTest(estado=estado, oracion=oracion[:40]):
                    self.assertIsNone(re.search(ECO_DE_INSTRUCCIONES, normalizar(oracion)))

    def test_gemini_solo_redacta_turnos_con_regla_o_pregunta_informativa(self):
        falso = GeminiFalso(base_de)
        chat = ChatSoborno()
        with patch("gemini_soborno.generar", falso):
            chat.responder(RELATO, gemini=True)                      # B3, B7: redacta
            r = chat.responder("¿atienden los sábados?", gemini=True)  # sin dato: local
        self.assertEqual(len(falso.llamadas), 1)
        self.assertTrue(r["modo"].startswith("Local"))
        self.assertTrue(r["respuesta_chatbot"].startswith("No tengo información oficial"))

    def test_fallo_de_gemini_muestra_la_respuesta_local(self):
        def falla(*_):
            raise RuntimeError("cuota agotada")
        with patch("gemini_soborno.generar", falla):
            r = ChatSoborno().responder(RELATO, gemini=True)
        self.assertEqual(r["fallo_gemini"], "cuota agotada")
        self.assertEqual(r["respuesta_chatbot"], ChatSoborno().responder(RELATO)["respuesta_chatbot"])


class PruebasExtractor(unittest.TestCase):
    MENSAJE = "El profe me dijo que con una lana me pasaba la materia."

    def test_cita_que_no_esta_en_el_mensaje_se_descarta(self):
        salida = json.dumps({"hechos": [
            {"hecho": "beneficio", "cita": "con una lana"},
            {"hecho": "exigencia", "cita": "me exigió dinero"},       # no está en el mensaje
            {"hecho": "inventado", "cita": "me pasaba"},              # fuera del vocabulario
            {"hecho": "ventaja", "cita": "me"},                       # cita demasiado corta
        ]})
        aceptados, descartados = interpretar_extraccion(salida, self.MENSAJE)
        self.assertEqual(aceptados, {"beneficio"})
        self.assertEqual(len(descartados), 3)

    def test_hechos_con_cita_completan_lo_que_las_reglas_no_ven(self):
        local = SesionAutomata().procesar(self.MENSAJE)
        self.assertEqual(local["estado"], "q1")
        salida = json.dumps({"hechos": [
            {"hecho": "beneficio", "cita": "con una lana"},
            {"hecho": "exigencia", "cita": "El profe me dijo"},
            {"hecho": "nexo", "cita": "con una lana me pasaba"},
        ]})
        with patch("gemini_soborno.generar", GeminiFalso(salida)):
            r = SesionAutomata(extractor=ExtractorGemini()).procesar(self.MENSAJE)
        self.assertEqual((r["estado"], r["reglas"]), ("q3", ["B3", "B7"]))
        self.assertEqual(r["hechos_gemini"], ["beneficio", "exigencia", "nexo"])

    def test_extractor_nunca_quita_hechos_locales(self):
        # Con un extractor que no encuentra nada, los 20 escenarios aprobados dan lo mismo.
        for identificador, mensajes, estado, reglas, salida in ESCENARIOS:
            with self.subTest(escenario=identificador):
                sesion = SesionAutomata(extractor=lambda _m: set())
                for mensaje in mensajes:
                    resultado = sesion.procesar(mensaje)
                self.assertEqual(resultado["estado"], estado)

    def test_fallo_del_extractor_sigue_con_reglas_locales(self):
        def falla(_):
            raise TimeoutError("sin respuesta")
        r = SesionAutomata(extractor=falla).procesar(RELATO)
        self.assertEqual(r["estado"], SesionAutomata().procesar(RELATO)["estado"])
        self.assertEqual(r["fallo_extractor"], "sin respuesta")

    def test_no_recibe_antecedentes_ni_respuestas_de_si_o_no(self):
        enviados = []
        sesion = SesionAutomata(extractor=lambda m: enviados.append(m) or set())
        sesion.procesar(RELATO)
        sesion.procesar("sí")
        sesion.procesar("¿Hay profesores acusados de pedir dinero?")
        self.assertEqual(enviados, [RELATO])

    def test_se_informa_cuando_el_extractor_no_encuentra_hechos(self):
        r = SesionAutomata(extractor=lambda _m: set()).procesar(RELATO)
        self.assertTrue(r["extractor_consultado"])
        self.assertEqual(r["hechos_gemini"], [])

    def test_redaccion_y_extraccion_son_independientes(self):
        falso = GeminiFalso('{"hechos": []}')
        with patch("gemini_soborno.generar", falso):
            ChatSoborno().responder(RELATO, gemini=False)
            ChatSoborno(extractor_gemini=True).responder(RELATO, gemini=False)
        self.assertEqual(len(falso.llamadas), 1)
        self.assertIsNotNone(falso.llamadas[0]["esquema"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

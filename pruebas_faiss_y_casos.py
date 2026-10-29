"""Pruebas locales de procedencia y enrutamiento; no llaman a servicios externos."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from casos_consulta import pregunta_por_antecedentes, resumen_registro
from chatbot_soborno import ChatSoborno
from faiss_soborno import DIMENSION, MODEL, leer_documentos, reconstruir_indice, _fragmentar


class PruebasCasosYFaiss(unittest.TestCase):
    def test_antecedente_no_se_toma_como_denuncia_personal(self):
        self.assertTrue(pregunta_por_antecedentes("¿Hay algún profesor acusado de soborno en CUTonalá?"))
        self.assertTrue(pregunta_por_antecedentes("¿Qué sabes del profesor X?"))
        self.assertFalse(pregunta_por_antecedentes("El profesor X me pidió dinero para aprobar"))
        self.assertFalse(pregunta_por_antecedentes("¿Qué sabes de Primer Contacto?"))

    def test_fuente_indica_que_los_relatos_no_estan_corroborrados(self):
        respuesta, registros = resumen_registro()
        self.assertEqual([r["id"] for r in registros], ["C01", "C02"])
        self.assertTrue(all("no corroborado" in r["estado"] for r in registros))
        self.assertIn("no hay un caso nominal y verificable", respuesta)

    def test_antecedente_no_altera_caso_que_se_relata_despues(self):
        chat = ChatSoborno()
        consulta = chat.responder("¿Hay algún profesor acusado de soborno en el centro?", gemini=True)
        self.assertEqual(consulta["memoria_turnos"], 0)
        self.assertEqual(consulta["modo"], "Local + registro de relatos")
        caso = chat.responder("El profesor X me pidió dinero a cambio de aprobar la materia")
        self.assertEqual(caso["coordenadas"], {"x": 4, "y": 3})
        self.assertIn("UDG", caso["rutas"])
        self.assertIn("legal", caso["rutas"])
        self.assertEqual(caso["memoria_turnos"], 1)

    def test_fallo_de_busqueda_vectorial_conserva_respuesta_local(self):
        class BuscadorCaido:
            def buscar_registro(self):
                raise RuntimeError("servicio temporalmente no disponible")

            def buscar(self, pregunta, estado, limite=3):
                raise RuntimeError("servicio temporalmente no disponible")

        chat = ChatSoborno(buscador=BuscadorCaido())
        antecedente = chat.responder("¿Hay algún profesor acusado de soborno?")
        self.assertIn("no hay un caso nominal", antecedente["respuesta_chatbot"])
        self.assertIsNotNone(antecedente["fallo_faiss"])
        caso = chat.responder("Un docente me pidió dinero para aprobar la materia")
        self.assertEqual(caso["coordenadas"], {"x": 4, "y": 3})
        self.assertTrue(caso["fragmentos"])
        self.assertIsNotNone(caso["fallo_faiss"])

    def test_modo_faiss_muestra_fragmento_sin_cabecera_pdf(self):
        class BuscadorFicticio:
            es_faiss = True

            def buscar(self, pregunta, estado, limite=3):
                return [{"titulo": "investigacion_soborno, página 10", "pagina": 10,
                         "archivo": "investigacion_soborno.pdf", "fuentes": [],
                         "texto": "Investigación documental | CUTonalá | Corte: 8 oct 2026 10 "
                                  "6 Directorio. Primer Contacto está en el CAE."},
                        {"titulo": "investigacion_soborno, página 7", "pagina": 7,
                         "archivo": "investigacion_soborno.pdf", "fuentes": ["S01"],
                         "texto": "Un apartado distinto sobre procedimientos."}]

        respuesta = ChatSoborno(buscador=BuscadorFicticio()).responder("¿Dónde encuentro Primer Contacto?")
        self.assertEqual(respuesta["modo"], "Local + autómata + FAISS")
        self.assertIn("6 Directorio", respuesta["respuesta_chatbot"])
        self.assertNotIn("Corte: 8 oct", respuesta["respuesta_chatbot"])
        self.assertIn("S05", respuesta["fuentes_consultadas"])
        self.assertNotIn("S01", respuesta["fuentes_consultadas"])

    def test_pdf_separados_con_procedencia_y_pagina(self):
        grupos = leer_documentos()
        self.assertGreater(len(grupos["procesos"]), 5)
        self.assertGreater(len(grupos["relatos"]), 1)
        for tipo, fragmentos in grupos.items():
            self.assertTrue(all(f["tipo"] == tipo and f["pagina"] >= 1 for f in fragmentos))
            self.assertTrue(all(len(f["texto"]) <= 1000 for f in fragmentos))

    def test_fragmentos_cubren_final_del_documento(self):
        texto = " ".join(f"palabra{i}" for i in range(300))
        fragmentos = _fragmentar(texto)
        self.assertGreater(len(fragmentos), 1)
        self.assertIn("palabra299", fragmentos[-1])

    @unittest.skipUnless(importlib.util.find_spec("faiss"), "FAISS no está instalado en este Python")
    def test_reconstruccion_reanuda_sin_repetir_pdf_terminado(self):
        grupos = {
            tipo: [{"titulo": tipo, "texto": "texto de prueba", "fuentes": [], "tipo": tipo,
                    "archivo": f"{tipo}.pdf", "pagina": 1}]
            for tipo in ("procesos", "relatos")
        }
        huella = {"modelo": MODEL, "dimension": DIMENSION, "tamano": 1000, "solapamiento": 200,
                  "archivos": {tipo: {"nombre": f"{tipo}.pdf", "sha256": tipo} for tipo in grupos}}
        llamadas = []

        def embeddings_ficticios(cliente, textos):
            llamadas.append(textos)
            if len(llamadas) == 2:
                raise RuntimeError("cuota temporal agotada")
            return [[0.01] * DIMENSION for _ in textos]

        with tempfile.TemporaryDirectory() as temporal, \
                patch("faiss_soborno.INDEX_DIR", Path(temporal)), \
                patch("faiss_soborno.leer_documentos", return_value=grupos), \
                patch("faiss_soborno._huella", return_value=huella), \
                patch("faiss_soborno._embeddings", side_effect=embeddings_ficticios):
            with self.assertRaisesRegex(RuntimeError, "cuota temporal"):
                reconstruir_indice(cliente=object())
            self.assertTrue((Path(temporal) / "procesos.meta.json").is_file())
            self.assertFalse((Path(temporal) / "manifest.json").exists())
            resultado = reconstruir_indice(cliente=object())
            self.assertEqual(resultado, {"procesos": 1, "relatos": 1})
            self.assertEqual(len(llamadas), 3)
            self.assertTrue((Path(temporal) / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)

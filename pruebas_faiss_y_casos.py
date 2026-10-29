"""Pruebas locales de procedencia y enrutamiento; no llaman a servicios externos."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from casos_consulta import pregunta_por_antecedentes, resumen_registro
from chatbot_soborno import ChatSoborno
from faiss_soborno import DIMENSION, MODEL, leer_documentos, reconstruir_indice, _fragmentar


class PruebasCasosYFaiss(unittest.TestCase):
    def setUp(self):
        ruta_ausente = Path(__file__).resolve().parent / "conocimientos" / "sin_registro_de_prueba.json"
        parche = patch("casos_consulta.REGISTRO_IDENTIFICADO", ruta_ausente)
        parche.start()
        self.addCleanup(parche.stop)

    def test_antecedente_no_se_toma_como_denuncia_personal(self):
        self.assertTrue(pregunta_por_antecedentes("¿Hay algún profesor acusado de soborno en CUTonalá?"))
        self.assertTrue(pregunta_por_antecedentes("¿Hay algún profesor señalado por pedir dinero a cambio de calificaciones?"))
        self.assertTrue(pregunta_por_antecedentes("¿Qué sabes del profesor X?"))
        self.assertFalse(pregunta_por_antecedentes("El profesor X me pidió dinero para aprobar"))
        self.assertFalse(pregunta_por_antecedentes("¿Qué sabes de Primer Contacto?"))

    def test_fuente_indica_que_los_relatos_no_estan_corroborrados(self):
        respuesta, registros = resumen_registro()
        self.assertEqual([r["id"] for r in registros], ["C01", "C02"])
        self.assertTrue(all("no corroborado" in r["estado"] for r in registros))
        self.assertIn("Los archivos aportados no vinculan ninguno con un nombre", respuesta)

    def test_testimonio_nominal_se_atribuye_sin_darlo_por_probado(self):
        caso = {
            "id": "T01", "persona": "Docente de Prueba",
            "alias": ["Docente Prueba"], "tema": "soborno", "beneficio": "dinero",
            "conducta": "habría pedido dinero a cambio de aprobar una materia",
            "materia": "Asignatura Ficticia", "ciclo": "2024A",
            "resultado": "el estudiante afirma que aprobó",
            "procedencia": "testimonio directo de una estudiante",
            "fecha_registro": "2026-10-29", "soporte": "relato verbal, sin archivo adjunto",
            "estado": "señalamiento pendiente de corroboración",
        }
        evaluacion = {
            "id": "T02", "persona": "Docente de Prueba",
            "alias": ["Docente Prueba"],
            "tema": "evaluacion", "conducta": "habría dado trato preferencial a amistades",
            "procedencia": "comentario indirecto de clase", "fecha_registro": "2026-10-29",
            "soporte": "sin documento adjunto", "estado": "comentario no corroborado",
        }
        botella = {
            "id": "T03", "persona": "Docente de Botella",
            "tema": "soborno", "beneficio": "botella",
            "conducta": "habría aceptado una botella a cambio de aprobar",
            "procedencia": "comentario indirecto de clase", "fecha_registro": "2026-10-29",
            "soporte": "sin documento adjunto", "estado": "comentario no corroborado",
        }
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporal:
            ruta = Path(temporal) / "casos_docentes.local.json"
            ruta.write_text(json.dumps({"casos": [caso, evaluacion, botella]}, ensure_ascii=False), encoding="utf-8")
            respuesta, registros = resumen_registro("¿Qué sabes de Docente Prueba?", ruta)
            self.assertEqual([r["id"] for r in registros], ["T01", "T02"])
            self.assertIn("Procedencia: testimonio directo", respuesta)
            self.assertIn("Materia: Asignatura Ficticia", respuesta)
            self.assertIn("Ciclo: 2024A", respuesta)
            self.assertIn("pendiente de corroboración", respuesta)
            self.assertNotIn("culpable", respuesta)
            _, solo_soborno = resumen_registro("¿Hay algún profesor acusado de soborno?", ruta)
            self.assertEqual([r["id"] for r in solo_soborno], ["T01", "T03"])
            _, solo_dinero = resumen_registro("¿Hay algún profesor señalado por pedir dinero?", ruta)
            self.assertEqual([r["id"] for r in solo_dinero], ["T01"])
            _, solo_botellas = resumen_registro("¿Qué profesores aceptan botellas?", ruta)
            self.assertEqual([r["id"] for r in solo_botellas], ["T03"])
            _, solo_evaluacion = resumen_registro("¿Qué sabes del amiguismo de Docente de Prueba?", ruta)
            self.assertEqual([r["id"] for r in solo_evaluacion], ["T02"])
            otra, otros_registros = resumen_registro("¿Qué sabes del profesor Distinto?", ruta)
            self.assertEqual(otros_registros, [])
            self.assertNotIn("Docente de Prueba", otra)
            with patch("casos_consulta.REGISTRO_IDENTIFICADO", ruta):
                salida = ChatSoborno().responder("¿Qué sabes de Docente de Prueba?", gemini=True)
            self.assertEqual(salida["casos_consultados"], ["T01", "T02"])
            self.assertEqual(salida["fragmentos"], [])
            self.assertEqual(salida["memoria_turnos"], 0)

    def test_antecedente_no_altera_caso_que_se_relata_despues(self):
        chat = ChatSoborno()
        consulta = chat.responder("¿Hay algún profesor señalado por pedir dinero a cambio de calificaciones?", gemini=True)
        self.assertEqual(consulta["memoria_turnos"], 0)
        self.assertEqual(consulta["modo"], "Local + registro de relatos")
        caso = chat.responder(
            "El profesor X me pidió 100 pesos para croquetas a cambio de ponerme 100 en la materia; "
            "pagué y la calificación quedó registrada. ¿Cómo procedo?"
        )
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
        self.assertIn("dos relatos estudiantiles", antecedente["respuesta_chatbot"])
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

        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporal, \
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

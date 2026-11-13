"""Pruebas locales de procedencia y enrutamiento; no llaman a servicios externos."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from casos_consulta import pregunta_por_antecedentes, resumen_registro
from chatbot_soborno import ChatSoborno
from faiss_soborno import DIMENSION, MODEL, consulta_vectorial, leer_documentos, reconstruir_indice, _fragmentar


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
        self.assertEqual(caso["estado"], "q3")
        self.assertEqual(consulta["reglas"], ["B2"])
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
        self.assertEqual(caso["estado"], "q3")
        self.assertTrue(caso["fragmentos"])
        self.assertIsNotNone(caso["fallo_faiss"])

    def test_modo_faiss_se_identifica_y_cita_sus_fuentes(self):
        class BuscadorFicticio:
            es_faiss = True

            def buscar(self, pregunta, estado, limite=3):
                return [{"titulo": "6.2 Atención en CUTonalá", "apartado": "6.2", "archivo": "directorio_cutonala.md",
                         "estados": ["B1", "q3"], "fuentes": ["S05"],
                         "texto": "Conviene confirmar el turno por correo antes de acudir a la oficina."}]

        respuesta = ChatSoborno(buscador=BuscadorFicticio()).responder("¿Dónde encuentro Primer Contacto?")
        self.assertEqual(respuesta["modo"], "Local + autómata + FAISS")
        self.assertIn("Dato recuperado de «6.2 Atención en CUTonalá»", respuesta["respuesta_chatbot"])
        self.assertIn("S05", respuesta["fuentes_consultadas"])

    def test_fragmentos_faiss_salen_de_la_base_segmentada(self):
        # Iteración 6: mismos archivos y exclusiones que la búsqueda local; ya no se leen los PDF.
        grupos = leer_documentos()
        procesos, relatos = grupos["procesos"], grupos["relatos"]
        self.assertTrue(all(f["tipo"] == "procesos" and f["apartado"] and f["estados"] for f in procesos))
        self.assertTrue(all(len(f["texto"]) <= 1000 for f in procesos + relatos))
        apartados = {f["apartado"] for f in procesos}
        self.assertFalse({"8.2", "12", "12.1", "9.1", "10.4"} & apartados)
        self.assertNotIn("demostracion del prototipo", " ".join(f["texto"].lower() for f in procesos))
        self.assertTrue(all(f["archivo"] == "relatos_campus.md" for f in relatos))
        self.assertTrue(any("C01" in f["titulo"] for f in relatos))

    def test_consulta_vectorial_no_incluye_el_mensaje(self):
        chat = ChatSoborno()
        estado = chat.sesion.procesar("El profesor Ramírez me pidió 500 pesos a cambio de aprobar la materia.")
        texto = consulta_vectorial(estado, None)
        for privado in ("Ramírez", "500", "pesos"):
            self.assertNotIn(privado, texto)
        self.assertIn("Primer Contacto", texto)
        self.assertIn("Se describe un beneficio a cambio de una ventaja académica.", texto)

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



@unittest.skipUnless(importlib.util.find_spec("faiss") and importlib.util.find_spec("numpy"),
                     "FAISS no está instalado en este Python")
class PruebasBuscadorFaiss(unittest.TestCase):
    """Índice real de FAISS con embeddings ficticios deterministas: sin llamadas al servicio."""

    @staticmethod
    def vector(texto):
        import hashlib
        import numpy as np
        semilla = int(hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8], 16)
        return [float(x) for x in np.random.default_rng(semilla).normal(size=DIMENSION)]

    def setUp(self):
        from faiss_soborno import BuscadorFaiss

        self.enviados = []
        prueba = self

        class Modelos:
            def embed_content(self, model, contents):
                prueba.enviados.append(contents)
                return types.SimpleNamespace(embeddings=[types.SimpleNamespace(values=prueba.vector(contents))])

        self.carpeta = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.carpeta.cleanup)
        parche = patch("faiss_soborno.INDEX_DIR", Path(self.carpeta.name))
        parche.start()
        self.addCleanup(parche.stop)
        with patch("faiss_soborno._embeddings", side_effect=lambda _c, textos: [self.vector(t) for t in textos]):
            with redirect_stdout(io.StringIO()):
                reconstruir_indice(cliente=object())
        self.buscador = BuscadorFaiss(cliente=types.SimpleNamespace(models=Modelos()))

    def test_pregunta_informativa_solo_recupera_sus_archivos(self):
        r = ChatSoborno(buscador=self.buscador).responder("¿Quién es la encargada de Primer Contacto?")
        self.assertEqual(r["modo"], "Local + autómata + FAISS")
        self.assertTrue(r["fragmentos"])
        self.assertTrue(all(f["archivo"] == "directorio_cutonala.md" for f in r["fragmentos"]))

    def test_relato_filtra_por_estado_y_no_envia_el_mensaje(self):
        r = ChatSoborno(buscador=self.buscador).responder(
            "El profesor Ramírez me pidió 500 pesos a cambio de aprobar la materia.")
        self.assertEqual(r["estado"], "q3")
        self.assertTrue(r["fragmentos"])
        self.assertTrue(all({"q3", "q5"} & set(f["estados"]) for f in r["fragmentos"]))
        enviados = " ".join(self.enviados)
        for privado in ("Ramírez", "500", "pesos"):
            self.assertNotIn(privado, enviados)

    def test_cambio_en_la_base_exige_reindexar(self):
        from faiss_soborno import BuscadorFaiss
        with patch("faiss_soborno._huella", return_value={"distinta": True}):
            with self.assertRaisesRegex(RuntimeError, "reindexar"):
                BuscadorFaiss(cliente=object())


if __name__ == "__main__":
    unittest.main(verbosity=2)

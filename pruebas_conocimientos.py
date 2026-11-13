"""Pruebas de la base de conocimiento segmentada; no llaman a servicios externos."""

import importlib.util
import json
from pathlib import Path
import unittest

from chatbot_soborno import Buscador, ChatSoborno, texto_visible

RAIZ = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("segmentar", RAIZ / "herramientas" / "segmentar_investigacion.py")
segmentar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(segmentar)
MANIFIESTO = json.loads((RAIZ / "conocimientos" / "manifiesto.json").read_text(encoding="utf-8"))
DESTINOS = {"q0", "q1", "q2", "q3", "q4", "q5", "q6", "qS", "B1", "B2", "otro_tema"}


class PruebasConocimientos(unittest.TestCase):
    def test_archivos_coinciden_textualmente_con_la_investigacion(self):
        for ruta, esperado in segmentar.contenido_esperado().items():
            with self.subTest(archivo=ruta.name):
                self.assertEqual(ruta.read_text(encoding="utf-8"), esperado)

    def test_cada_apartado_esta_asignado_o_excluido(self):
        self.assertEqual(segmentar.apartados_sin_destino(), [])

    def test_manifiesto_usa_estados_del_automata(self):
        for entrada in MANIFIESTO["archivos"]:
            with self.subTest(archivo=entrada["archivo"]):
                self.assertTrue((RAIZ / "conocimientos" / entrada["archivo"]).exists())
                self.assertTrue(entrada["estados"])
                self.assertTrue(set(entrada["estados"]) <= DESTINOS)

    def test_ningun_apartado_se_asigna_dos_veces(self):
        apartados = [a for e in MANIFIESTO["archivos"] for a in e["apartados"]]
        self.assertEqual(len(apartados), len(set(apartados)))

    def test_tablas_y_negritas_se_muestran_sin_formato(self):
        for fragmento in Buscador().fragmentos:
            visible = texto_visible(fragmento)
            self.assertNotIn("|---", visible)
            self.assertNotIn("**", visible)

    def test_diseno_del_prototipo_no_llega_al_estudiante(self):
        respuesta = ChatSoborno().responder("El profe insinuó que un regalito ayudaría con la nota.")
        self.assertTrue(respuesta["fragmentos"])
        self.assertFalse(any(f["apartado"].startswith("12") for f in respuesta["fragmentos"]))

    def test_cada_estado_recupera_de_sus_archivos(self):
        chat = ChatSoborno()
        aclaracion = chat.responder("Ya pagué la inscripción y quiero saber mi calificación.")
        self.assertTrue(all("q1" in f["estados"] for f in aclaracion["fragmentos"]))
        respuesta = chat.responder("Si")
        # q3 con la pregunta B15 pendiente: archivos de q3 y de q6.
        self.assertTrue(all({"q3", "q6"} & set(f["estados"]) for f in respuesta["fragmentos"]))
        self.assertFalse(any(f["apartado"] in ("7.1", "7.6") for f in respuesta["fragmentos"]))

    def test_relatos_del_campus_no_se_indexan_como_orientacion(self):
        self.assertFalse(any(f["archivo"] == "relatos_campus.md" for f in Buscador().fragmentos))


if __name__ == "__main__":
    unittest.main(verbosity=2)

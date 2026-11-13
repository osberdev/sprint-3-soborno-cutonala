"""Pruebas de la iteración 5: retomar un caso entre ejecuciones. Sin servicios externos."""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from automata_soborno import SesionAutomata
from chatbot_soborno import CasoGuardado, ChatSoborno, retomar_si_existe

RAIZ = Path(__file__).resolve().parent
RELATO = "El profesor Ramírez me pidió 500 pesos a cambio de aprobar la materia."


def conversar(sesion, *mensajes):
    resultado = None
    for mensaje in mensajes:
        resultado = sesion.procesar(mensaje)
    return resultado


class PruebasExportacion(unittest.TestCase):
    def test_retomar_da_el_mismo_resultado_que_no_interrumpir(self):
        guiones = [
            [RELATO, "no sé"],                                            # pregunta pendiente con un intento
            ["Le di 500 pesos al profesor porque tenía miedo de reprobar la materia.", "sí",
             "Ahora mismo está afuera del salón esperándome."],          # en qS, con camino q1 → q2 → q6
            ["Ya pagué la inscripción y quiero saber mi calificación."],  # pago ordinario sin vincular
        ]
        siguientes = ["sí", "Ya estoy a salvo.", "condicionado por una calificación"]
        for guion, siguiente in zip(guiones, siguientes):
            with self.subTest(guion=guion[0][:30]):
                continua = SesionAutomata()
                conversar(continua, *guion)
                retomada = SesionAutomata.desde_dict(json.loads(json.dumps(continua.exportar())))
                a, b = continua.procesar(siguiente), retomada.procesar(siguiente)
                for clave in ("estado", "reglas", "pendiente", "ficha", "respuesta"):
                    self.assertEqual(a[clave], b[clave], clave)

    def test_no_guarda_el_texto_de_los_mensajes(self):
        sesion = SesionAutomata()
        conversar(sesion, RELATO, "Además me amenazó con reprobarme si no le pago.")
        guardado = json.dumps(sesion.exportar(), ensure_ascii=False)
        for privado in ("Ramírez", "500", "pesos", "amenazó", "reprobarme"):
            self.assertNotIn(privado, guardado)

    def test_datos_invalidos_se_rechazan(self):
        valido = SesionAutomata()
        conversar(valido, RELATO)
        base = valido.exportar()
        alteraciones = {
            "version": {"version": 99},
            "estado": {"estado": "q9"},
            "pendiente": {"pendiente": "B99"},
            "camino": {"camino": ["B14"]},                       # B14 no sale de q1
            "camino que no llega": {"camino": ["B6"]},           # termina en q2, el estado es q3
            "campo extra": {"ficha": {**base["ficha"], "nombre_docente": "X"}},
            "texto libre": {"ficha": {**base["ficha"], "participacion": "le dio dinero a Ramírez"}},
            "decisión": {"ficha": {**base["ficha"], "decisiones": {"B14": "tal vez"}}},
        }
        for nombre, cambio in alteraciones.items():
            with self.subTest(alteracion=nombre):
                with self.assertRaises(ValueError):
                    SesionAutomata.desde_dict({**base, **cambio})


class PruebasArchivo(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.guardado = CasoGuardado(Path(self.carpeta.name) / "caso_guardado.local.json")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_cada_turno_se_guarda_y_se_retoma_en_otra_ejecucion(self):
        ChatSoborno(guardado=self.guardado).responder(RELATO)
        self.assertTrue(self.guardado.existe())
        sesion, fecha = self.guardado.cargar()
        self.assertEqual((sesion.estado, sesion.pendiente), ("q3", "B14"))
        self.assertTrue(fecha)
        r = ChatSoborno(guardado=self.guardado, sesion=sesion).responder("sí")
        self.assertEqual(r["estado"], "q5")
        self.assertEqual(self.guardado.cargar()[0].estado, "q5")

    def test_archivo_danado_se_ignora_con_aviso(self):
        self.guardado.ruta.write_text("{no es json", encoding="utf-8")
        sesion, motivo = self.guardado.cargar()
        self.assertIsNone(sesion)
        self.assertIn("no es válido", motivo)

    def test_retomar_o_borrar_al_iniciar(self):
        ChatSoborno(guardado=self.guardado).responder(RELATO)
        with redirect_stdout(io.StringIO()) as salida:
            chat = retomar_si_existe(ChatSoborno(), self.guardado, None, False, entrada=lambda _: "sí")
        self.assertEqual(chat.sesion.estado, "q3")
        self.assertIn("Retomamos tu caso donde lo dejamos", salida.getvalue())
        self.assertIn("Fiscalía Especializada", salida.getvalue())   # la pregunta pendiente B14
        with redirect_stdout(io.StringIO()):
            chat = retomar_si_existe(ChatSoborno(), self.guardado, None, False, entrada=lambda _: "no")
        self.assertEqual(chat.sesion.estado, "q0")
        self.assertFalse(self.guardado.existe())

    def test_el_archivo_esta_excluido_de_git(self):
        reglas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("caso_guardado.local.json", reglas)
        self.assertIn("caso_guardado.local.tmp", reglas)


if __name__ == "__main__":
    unittest.main(verbosity=2)

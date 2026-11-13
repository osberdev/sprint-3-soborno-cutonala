"""Criterios de aceptación del autómata nuevo (estados q0–q6 y qS, reglas B1–B17).

Cada escenario es una conversación y el resultado que el autómata debe producir:
el estado final, las reglas que deben dispararse y, si aplica, la salida a otro
tema del equipo. Los escenarios 9.x adaptan a primera persona los escenarios
ficticios del capítulo 9 de la investigación; los G·x reproducen el guion de la
prueba manual del 12 de noviembre de 2026.

"sí" y "no" responden la pregunta (1,0) que el autómata dejó pendiente.
Las pruebas se omiten mientras no exista `automata_soborno.py` (iteración 2).
"""

import importlib.util
import unittest

ESCENARIOS = [
    # id, mensajes, estado final, reglas que deben aparecer, salida esperada
    ("9.1a", ["Organizan una colecta voluntaria de croquetas para los animales del campus; no cuenta para la calificación."],
     "q1", {"B3", "B5"}, "otro_tema"),
    ("9.1b", ["Organizan una colecta de croquetas para los animales del campus.",
              "Ahora el profesor dice que quienes aporten recibirán puntos extra sin hacer ninguna actividad."],
     "q3", {"B3", "B7"}, None),
    ("9.2", ["El profesor dijo que quienes den 200 pesos para una causa tendrán 100 en la materia; guardé el mensaje.", "sí"],
     "q5", {"B3", "B7", "B14"}, None),
    ("9.3", ["Le ofrecí una botella al profesor para aprobar y la aceptó.", "sí"],
     "q6", {"B3", "B7", "B15"}, None),
    ("9.4", ["Siento que el profe favorece a un amigo suyo con mejores oportunidades, pero no sé de ningún pago."],
     "q1", {"B3", "B5"}, "otro_tema"),
    ("9.5", ["Le ofrecí dinero al profesor para que me cambiara la nota y lo rechazó.", "sí"],
     "q6", {"B3", "B7", "B15"}, None),
    ("9.6", ["La profesora me dijo que voy a reprobar si no le doy dinero.", "sí"],
     "q5", {"B3", "B8", "B14"}, None),
    ("9.7", ["Un compañero que no es docente me pide una transferencia y dice que conoce a alguien que puede cambiar mi calificación.", "no"],
     "q3", {"B3", "B7"}, None),
    ("9.8", ["Un docente me pidió dinero para aprobar.",
             "Después de reportarlo me mandó un mensaje amenazando con perjudicarme y ahora me puso una nota injusta."],
     "q3", {"B3", "B7", "B8"}, None),
    ("9.9", ["Desde hace años se dice que en cierta materia se puede pagar para pasar, pero yo no lo he vivido."],
     "q1", {"B3", "B4"}, None),
    ("9.10", ["Le di dinero al profesor porque tenía miedo de reprobar y ahora quiero ayuda.", "sí"],
     "q6", {"B3", "B6", "B15"}, None),
    ("G1", ["¿Dónde encuentro Primer Contacto?"], "q0", {"B1"}, None),
    ("G2", ["Se comenta que un profesor aprueba por regalos."], "q1", {"B3", "B4"}, None),
    ("G3-G4", ["Un docente me pidió dinero a cambio de aprobar la materia.", "Si no le pago, me amenaza con reprobarme."],
     "q3", {"B3", "B7", "B8"}, None),
    ("G5", ["Ya pagué la inscripción y quiero saber mi calificación."], "q1", {"B3"}, None),
    ("G6", ["El profe insinuó que un regalito ayudaría con la nota."], "q1", {"B3", "B4"}, None),
    # Decisión de implementación: una amenaza física sin indicio de peligro actual
    # va a q3 (B8) y el autómata pregunta si el peligro es actual; "sí" activa B16.
    ("G7-G8", ["Me amenazó con golpearme si no le pago.", "sí"], "qS", {"B3", "B8", "B16"}, None),
    # En qS una retractación no basta: se confirma que la persona está a salvo (B17).
    ("G9", ["Me amenazó con golpearme si no le pago.", "sí", "Era broma, olvídalo."], "qS", {"B16"}, None),
    ("G9b", ["Me amenazó con golpearme si no le pago.", "sí", "Era broma, olvídalo.", "sí"], "q1", {"B16", "B17"}, None),
    ("G10", ["Me amenazó con golpearme si no le pago.", "¿Hay profesores acusados de pedir dinero?"],
     "q3", {"B2"}, None),
]


@unittest.skipUnless(importlib.util.find_spec("automata_soborno"), "El autómata nuevo se implementa en la iteración 2")
class PruebasAceptacion(unittest.TestCase):
    def test_escenarios(self):
        from automata_soborno import SesionAutomata

        for identificador, mensajes, estado, reglas, salida in ESCENARIOS:
            with self.subTest(escenario=identificador):
                sesion = SesionAutomata()
                disparadas: set[str] = set()
                for mensaje in mensajes:
                    resultado = sesion.procesar(mensaje)
                    disparadas.update(resultado["reglas"])
                self.assertEqual(resultado["estado"], estado)
                self.assertLessEqual(reglas, disparadas)
                self.assertEqual(resultado.get("salida"), salida)


if __name__ == "__main__":
    unittest.main(verbosity=2)

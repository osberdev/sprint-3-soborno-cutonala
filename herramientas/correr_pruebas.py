"""Ejecuta todas las suites de pruebas y resume el resultado (iteración 7).

Uso, desde la raíz del repositorio:

    python3 herramientas/correr_pruebas.py            # resumen
    python3 herramientas/correr_pruebas.py --detalle  # salida completa de cada suite

Ninguna prueba llama a servicios externos. Las pruebas de FAISS se omiten si
`faiss-cpu` y `numpy` no están instalados en el Python que las ejecuta.
"""

from __future__ import annotations

import argparse
import platform
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SUITES = [
    ("pruebas_automata.py", "Autómata: tabla de transiciones, casos límite, nombres exactos, regresiones"),
    ("escenarios_aceptacion.py", "Escenarios de aceptación aprobados (9.x y guion de prueba manual)"),
    ("pruebas_conocimientos.py", "Base segmentada: fidelidad textual, exclusiones y recuperación por estado"),
    ("pruebas_chatbot.py", "Chat en modo local"),
    ("pruebas_gemini.py", "Gemini simulado: qué se envía, datos inventados, extractor y fallos"),
    ("pruebas_persistencia.py", "Retomar un caso entre ejecuciones"),
    ("pruebas_faiss_y_casos.py", "Registro de relatos y FAISS con embeddings ficticios"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--detalle", action="store_true", help="muestra la salida completa de cada suite")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"Python {platform.python_version()} · {platform.system()} {platform.release()}")
    total = omitidas = 0
    fallidas: list[str] = []
    for archivo, descripcion in SUITES:
        salida = subprocess.run([sys.executable, archivo], cwd=RAIZ, capture_output=True, text=True,
                                encoding="utf-8")
        texto = salida.stdout + salida.stderr
        ejecutadas = int(m.group(1)) if (m := re.search(r"Ran (\d+) tests?", texto)) else 0
        saltadas = int(m.group(1)) if (m := re.search(r"skipped=(\d+)", texto)) else 0
        estado = "OK" if salida.returncode == 0 else "FALLA"
        total += ejecutadas
        omitidas += saltadas
        if salida.returncode:
            fallidas.append(archivo)
        extra = f", {saltadas} omitidas" if saltadas else ""
        print(f"{estado:5} {archivo:28} {ejecutadas:3} pruebas{extra} · {descripcion}")
        if args.detalle or salida.returncode:
            print(texto)
    print(f"\nTotal: {total} pruebas, {omitidas} omitidas, {len(fallidas)} suites con fallas.")
    return 1 if fallidas else 0


if __name__ == "__main__":
    raise SystemExit(main())

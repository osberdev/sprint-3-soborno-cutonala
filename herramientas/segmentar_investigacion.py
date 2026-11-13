"""Segmenta la investigación (.docx) en los archivos de conocimiento de `conocimientos/`.

Solo usa la biblioteca estándar: lee el XML del .docx, conserva el texto de cada
apartado sin reescribirlo y lo distribuye según `conocimientos/manifiesto.json`.

Uso:
    python3 herramientas/segmentar_investigacion.py            # regenera los archivos
    python3 herramientas/segmentar_investigacion.py --verificar  # comprueba sin escribir
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

RAIZ = Path(__file__).resolve().parent.parent
DOCX = RAIZ / "Investigacion_soborno_CUTonala.docx"
CONOCIMIENTOS = RAIZ / "conocimientos"
MANIFIESTO = CONOCIMIENTOS / "manifiesto.json"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ESTILOS = {"Ttulo1": "h1", "Ttulo2": "h2", "Listaconvietas": "li", "Subttulo": "p"}
AVISO = "<!-- Generado por herramientas/segmentar_investigacion.py; no editar a mano. -->"
INICIO_BLOQUE = "<!-- inicio de bloque generado desde la investigación -->"
FIN_BLOQUE = "<!-- fin de bloque generado -->"


def _texto(elemento: ET.Element) -> str:
    partes: list[str] = []
    for nodo in elemento.iter():
        if nodo.tag == W + "t" and nodo.text:
            partes.append(nodo.text)
        elif nodo.tag == W + "tab":
            partes.append("\t")
        elif nodo.tag in (W + "br", W + "cr"):
            partes.append("\n")
    return "".join(partes)


def _tabla(tbl: ET.Element) -> str:
    filas = []
    for tr in tbl.findall(W + "tr"):
        celdas = []
        for tc in tr.findall(W + "tc"):
            parrafos = [_texto(p).strip() for p in tc.findall(W + "p")]
            celdas.append(" ".join(p for p in parrafos if p).replace("|", "\\|"))
        filas.append(celdas)
    if not filas:
        return ""
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    lineas = ["| " + " | ".join(filas[0]) + " |", "|" + "---|" * ancho]
    lineas += ["| " + " | ".join(f) + " |" for f in filas[1:]]
    return "\n".join(lineas)


def leer_bloques(docx: Path = DOCX) -> list[dict[str, str]]:
    """Devuelve los bloques del documento en orden, con el apartado al que pertenecen."""
    with zipfile.ZipFile(docx) as z:
        cuerpo = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    bloques: list[dict[str, str]] = []
    capitulo, apartado = "0", "0"
    for elemento in cuerpo:
        if elemento.tag == W + "tbl":
            bloques.append({"apartado": apartado, "tipo": "tabla", "texto": _tabla(elemento)})
            continue
        if elemento.tag != W + "p":
            continue
        estilo = elemento.find(f"{W}pPr/{W}pStyle")
        tipo = ESTILOS.get(estilo.get(W + "val") if estilo is not None else "", "p")
        texto = _texto(elemento).strip()
        if not texto:
            continue
        if tipo == "h1":
            numero = re.match(r"(\d+)\s", texto)
            capitulo = numero.group(1) if numero else "0"
            apartado = capitulo
        elif tipo == "h2":
            numero = re.match(r"(\d+\.\d+)\s", texto)
            apartado = numero.group(1) if numero else capitulo
        bloques.append({"apartado": apartado, "tipo": tipo, "texto": texto})
    return bloques


def cargar_manifiesto() -> dict:
    return json.loads(MANIFIESTO.read_text(encoding="utf-8"))


def _cuerpo_apartados(apartados: list[str], bloques: list[dict[str, str]]) -> str:
    secciones: list[str] = []
    for apartado in apartados:
        propios = [b for b in bloques if b["apartado"] == apartado]
        titulo = next((b["texto"] for b in propios if b["tipo"] in ("h1", "h2")), None)
        contenido = [b for b in propios if b["tipo"] not in ("h1", "h2")]
        if titulo is None:
            raise ValueError(f"El apartado {apartado} no existe en la investigación")
        if not contenido:
            continue  # capítulo sin texto introductorio propio
        partes = [f"## {titulo}"]
        for b in contenido:
            partes.append(f"- {b['texto']}" if b["tipo"] == "li" else b["texto"])
        secciones.append("\n\n".join(partes))
    return "\n\n".join(secciones)


def _fuentes(texto: str) -> list[str]:
    return sorted(set(re.findall(r"S\d{2}", texto)))


def renderizar(entrada: dict, bloques: list[dict[str, str]]) -> str:
    cuerpo = _cuerpo_apartados(entrada["apartados"], bloques)
    if entrada.get("bloque_generado"):
        return cuerpo
    apartados = [a for a in entrada["apartados"] if "." in a] or entrada["apartados"]
    fuentes = ", ".join(_fuentes(cuerpo)) or "ninguna"
    cabecera = (
        f"# {entrada['titulo']}\n\n{AVISO}\n\n"
        f"Fuente: Investigacion_soborno_CUTonala.docx, apartados {', '.join(apartados)}. "
        f"Corte documental: 8 de octubre de 2026. Fuentes citadas: {fuentes}."
    )
    return f"{cabecera}\n\n{cuerpo}\n"


def _con_bloque(actual: str, bloque: str) -> str:
    nuevo = f"{INICIO_BLOQUE}\n\n{bloque}\n\n{FIN_BLOQUE}"
    if INICIO_BLOQUE in actual:
        return re.sub(re.escape(INICIO_BLOQUE) + r".*?" + re.escape(FIN_BLOQUE), lambda _: nuevo, actual, flags=re.S)
    return actual.rstrip("\n") + "\n\n" + nuevo + "\n"


def contenido_esperado(docx: Path = DOCX) -> dict[Path, str]:
    bloques = leer_bloques(docx)
    esperado: dict[Path, str] = {}
    for entrada in cargar_manifiesto()["archivos"]:
        ruta = CONOCIMIENTOS / entrada["archivo"]
        texto = renderizar(entrada, bloques)
        if entrada.get("bloque_generado"):
            texto = _con_bloque(ruta.read_text(encoding="utf-8"), texto)
        esperado[ruta] = texto
    return esperado


def apartados_sin_destino(docx: Path = DOCX) -> list[str]:
    """Apartados del documento que no están asignados ni excluidos en el manifiesto."""
    manifiesto = cargar_manifiesto()
    asignados = {a for e in manifiesto["archivos"] for a in e["apartados"]}
    excluidos = {a for e in manifiesto["excluidos"] for a in e["apartados"]}
    faltantes = []
    for apartado in dict.fromkeys(b["apartado"] for b in leer_bloques(docx)):
        capitulo = apartado.split(".")[0]
        if apartado not in asignados and apartado not in excluidos and capitulo not in excluidos:
            faltantes.append(apartado)
    return faltantes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true", help="comprueba que los archivos coinciden con el .docx")
    args = parser.parse_args()
    faltantes = apartados_sin_destino()
    if faltantes:
        print("Apartados sin destino en el manifiesto:", ", ".join(faltantes), file=sys.stderr)
        return 1
    diferencias = []
    for ruta, texto in contenido_esperado().items():
        actual = ruta.read_text(encoding="utf-8") if ruta.exists() else None
        if actual == texto:
            continue
        if args.verificar:
            diferencias.append(ruta.name)
        else:
            ruta.write_text(texto, encoding="utf-8")
            print("Actualizado:", ruta.relative_to(RAIZ))
    if diferencias:
        print("No coinciden con la investigación:", ", ".join(diferencias), file=sys.stderr)
        return 1
    if args.verificar:
        print("Los archivos de conocimiento coinciden con la investigación.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

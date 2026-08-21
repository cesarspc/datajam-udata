"""Ejecuta notebooks seleccionados, cada uno con un kernel nuevo."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]


def execute(path: Path) -> None:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        allow_errors=False,
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute(cwd=str(ROOT))
    nbformat.write(notebook, path)
    error_outputs = [
        output
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type == "error"
    ]
    if error_outputs:
        raise RuntimeError(f"{path.name} conservó errores de ejecución.")
    executed = [cell.execution_count for cell in notebook.cells if cell.cell_type == "code"]
    if not executed or any(value is None for value in executed):
        raise RuntimeError(f"{path.name} contiene celdas de código sin ejecutar.")
    print(f"APROBADO {path.name}: {len(executed)} celdas de código, kernel limpio, sin errores")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebooks", nargs="+", help="Rutas relativas de notebooks")
    args = parser.parse_args()
    for item in args.notebooks:
        path = (ROOT / item).resolve()
        if path.parent != (ROOT / "notebooks").resolve():
            raise ValueError(f"Notebook fuera del directorio esperado: {path}")
        execute(path)


if __name__ == "__main__":
    main()

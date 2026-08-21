"""Genera los notebooks fuente del dashboard con una estructura uniforme."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def notebook(cells: list[dict]) -> dict:
    prepared_cells = []
    for index, cell in enumerate(cells, start=1):
        prepared = dict(cell)
        prepared["id"] = f"cell-{index:03d}"
        prepared_cells.append(prepared)
    return {
        "cells": prepared_cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP = """from pathlib import Path
import sys

PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent
if not (PROJECT_ROOT / "data" / "processed").exists():
    raise FileNotFoundError("Ejecute el notebook desde la raíz del repositorio o desde notebooks/.")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
"""

LOAD = """import pandas as pd
from src.dashboard_utils import load_dataset

df = load_dataset(PROJECT_ROOT)
print(f"Registros: {len(df)} | Localidades: {df['locality'].nunique()}")
df.head()"""


NOTEBOOK_DEFINITIONS = {
    "00_preparacion_y_validacion.ipynb": [
        markdown("""# 00 — Preparación y validación

Este notebook crea la entrada analítica común del dashboard mediante una **transformación mínima** del archivo procesado existente `indice_localidad_disposicion_inadecuada.csv`.

No reconstruye la encuesta, los delitos, la población ni el indicador de disposición. Solo selecciona las variables existentes, normaliza los nombres visibles de las localidades, valida tipos y escalas, y guarda `dashboard_dataset.csv` porque la especificación exige una entrada tabular común para los notebooks 01–07."""),
        markdown("## 1. Configuración de rutas e importaciones"),
        code(SETUP),
        code("""import pandas as pd
from src.dashboard_utils import (
    DASHBOARD_DATASET,
    NUMERIC_COLUMNS,
    REQUIRED_COLUMNS,
    SOURCE_DATASET,
    prepare_dashboard_dataset,
    validate_dataset,
)

source_path = PROCESSED_DIR / SOURCE_DATASET
assert source_path.exists(), f"No existe el insumo procesado: {source_path}"
print(f"Insumo reutilizado: {source_path.relative_to(PROJECT_ROOT)}")"""),
        markdown("""## 2. Consolidación mínima

Las estadísticas y la metodología se conservan tal como están en el dataset procesado. Los porcentajes ya se encuentran en escala 0–100."""),
        code("""df, validation_report, output_path = prepare_dashboard_dataset(PROJECT_ROOT)
print(f"Archivo analítico generado: {output_path.relative_to(PROJECT_ROOT)}")
validation_report"""),
        markdown("## 3. Validaciones requeridas"),
        code("""df.shape"""),
        code("""df.info()"""),
        code("""df.isna().sum()"""),
        code("""df.duplicated().sum()"""),
        code("""df.describe()"""),
        code("""locality_count = df["locality"].nunique()
assert locality_count == len(df) == 19
assert df["disposicion_inadecuada_pct"].between(0, 100).all()
assert df["insecurity_noche_pct"].between(0, 100).all()
assert set(NUMERIC_COLUMNS).issubset(df.select_dtypes(include="number").columns)
assert output_path.exists() and output_path.stat().st_size > 0
print(f"Validación aprobada: {locality_count} localidades, sin duplicados ni nulos; porcentajes en escala 0–100.")"""),
        markdown("""## 4. Trazabilidad

- Entrada: `data/processed/indice_localidad_disposicion_inadecuada.csv`.
- Salida: `data/processed/dashboard_dataset.csv`.
- Transformaciones: selección de las diez variables analíticas existentes, normalización ortográfica de localidades, ordenamiento y validación.
- No se modificó ningún archivo procesado previo."""),
    ],
    "01_kpis.ipynb": [
        markdown("""# 01 — Indicadores principales

Los cuatro indicadores resumen se calculan directamente desde el dataset analítico común. Pearson y Spearman comparan la disposición inadecuada con la brecha de percepción; ningún valor está codificado manualmente."""),
        markdown("## 1. Importaciones y rutas"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Cálculo y visualización Plotly"),
        code("""from src.dashboard_utils import calculate_metrics, create_indicators

metrics = calculate_metrics(df)
{
    "Disposición inadecuada promedio (%)": round(metrics["mean_disposition"], 2),
    "Percepción de inseguridad promedio (%)": round(metrics["mean_insecurity"], 2),
    "Pearson": round(metrics["pearson_r"], 3),
    "Spearman": round(metrics["spearman_r"], 3),
}"""),
        code("""fig_kpis = create_indicators(df)
assert len(fig_kpis.data) == 4
assert all(trace.type == "indicator" for trace in fig_kpis.data)
fig_kpis.show(config={"displaylogo": False, "responsive": True})"""),
        markdown("Los porcentajes se muestran como puntos porcentuales en escala 0–100. Los coeficientes describen asociación y no implican causalidad."),
    ],
    "02_relacion_scatter.ipynb": [
        markdown("""# 02 — Relación principal: dispersión y regresión

Cada punto representa una localidad. El eje X muestra hogares con disposición inadecuada y el eje Y la brecha estandarizada entre inseguridad nocturna y delitos estimados. Las líneas discontinuas corresponden a los promedios y forman cuatro cuadrantes interpretativos."""),
        markdown("## 1. Importaciones, rutas y datos"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Estadísticas calculadas"),
        code("""from src.dashboard_utils import calculate_metrics, create_scatter_relationship

metrics = calculate_metrics(df)
print(f"Pearson r = {metrics['pearson_r']:.3f} (p = {metrics['pearson_p']:.4f})")
print(f"Spearman ρ = {metrics['spearman_r']:.3f} (p = {metrics['spearman_p']:.4f})")
print(f"Pendiente = {metrics['slope']:.4f} | R² = {metrics['r_squared']:.3f}")"""),
        markdown("## 3. Visualización Plotly"),
        code("""fig_scatter = create_scatter_relationship(df)
assert len(fig_scatter.data) == 2
assert {trace.type for trace in fig_scatter.data} == {"scatter"}
fig_scatter.show(config={"displaylogo": False, "scrollZoom": True, "responsive": True})"""),
        markdown("La tendencia es exploratoria. Una relación estadística entre ambas variables no permite afirmar que una cause la otra."),
    ],
    "03_heatmap_correlaciones.ipynb": [
        markdown("""# 03 — Relación directa entre disposición e inseguridad

El mapa de calor se reemplaza por un gráfico de dispersión: una forma habitual y más accesible de comunicar la relación entre dos variables cuantitativas. La [Government Analysis Function](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/) recomienda la dispersión para mostrar correlaciones, y la [Office for National Statistics](https://service-manual.ons.gov.uk/data-visualisation/chart-types/choosing-a-chart-type) aconseja priorizar gráficos simples y familiares.

Cada punto representa una localidad. La gráfica compara directamente hogares con disposición inadecuada y personas que se sienten inseguras al caminar de noche."""),
        markdown("## 1. Importaciones, rutas y datos"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Relación calculada desde los datos"),
        code("""from scipy.stats import pearsonr
from src.dashboard_utils import create_direct_relationship

direct_r, direct_p = pearsonr(df["disposicion_inadecuada_pct"], df["insecurity_noche_pct"])
print(f"Relación lineal: {direct_r:.3f} | p = {direct_p:.4f}")"""),
        markdown("## 3. Gráfico de dispersión Plotly"),
        code("""fig_relacion_directa = create_direct_relationship(df)
assert len(fig_relacion_directa.data) == 2
assert {trace.type for trace in fig_relacion_directa.data} == {"scatter"}
fig_relacion_directa.show(config={"displaylogo": False, "scrollZoom": True, "responsive": True})"""),
        markdown("La tendencia resume una asociación territorial. No permite concluir que una variable sea la causa de la otra."),
    ],
    "04_mapas_territoriales.ipynb": [
        markdown("""# 04 — Mapas territoriales

Los mapas coropléticos usan exclusivamente el shapefile local `data/raw/dai_shp/DAILoc.shp`. Se filtran las 19 localidades presentes en el dataset analítico; Sumapaz no aparece porque no tiene observación completa en ese insumo procesado."""),
        markdown("## 1. Importaciones, rutas y datos"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Carga y verificación de geometrías"),
        code("""from src.dashboard_utils import (
    create_disposition_map,
    create_insecurity_map,
    load_geography,
    locality_key,
)

gdf, geojson = load_geography(PROJECT_ROOT, df["locality"])
assert len(gdf) == df["locality"].nunique() == 19
assert set(df["locality"].map(locality_key)) == set(gdf["locality_key"])
print(f"Geometrías: {len(gdf)} | CRS para Plotly: {gdf.crs}")
gdf[["CMIULOCAL", "locality"]].sort_values("CMIULOCAL")"""),
        markdown("## 3. Disposición inadecuada de basura por localidad"),
        code("""fig_mapa_disposicion = create_disposition_map(df, geojson)
assert fig_mapa_disposicion.data[0].type == "choropleth"
fig_mapa_disposicion.show(config={"displaylogo": False, "scrollZoom": True, "responsive": True})"""),
        markdown("## 4. Brecha entre percepción de inseguridad y delitos por localidad"),
        code("""fig_mapa_inseguridad = create_insecurity_map(df, geojson)
assert fig_mapa_inseguridad.data[0].type == "choropleth"
fig_mapa_inseguridad.show(config={"displaylogo": False, "scrollZoom": True, "responsive": True})"""),
        markdown("El patrón territorial es descriptivo y corresponde a la unidad localidad; no debe extrapolarse automáticamente a barrios o personas."),
    ],
    "05_ranking_localidades.ipynb": [
        markdown("""# 05 — Ranking de localidades

El selector Plotly permite alternar entre disposición inadecuada y percepción de inseguridad. Las barras horizontales se leen de arriba hacia abajo, desde el valor más alto."""),
        markdown("## 1. Importaciones, rutas y datos"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Ranking interactivo Plotly"),
        code("""from src.dashboard_utils import create_ranking

fig_ranking = create_ranking(df)
assert len(fig_ranking.data) == 2
assert len(fig_ranking.layout.updatemenus[0].buttons) == 2
fig_ranking.show(config={"displaylogo": False, "responsive": True})"""),
        markdown("El orden se recalcula para cada indicador; el selector no duplica gráficas y conserva el hover con el valor exacto."),
    ],
    "06_hallazgos.ipynb": [
        markdown("""# 06 — Hallazgos e interpretación

La conclusión se genera desde los resultados observados. Para describir la magnitud absoluta de Pearson se usan estos umbrales: menor que 0,20 muy débil; 0,20–0,39 débil; 0,40–0,59 moderada; 0,60–0,79 fuerte; y 0,80 o más muy fuerte."""),
        markdown("## 1. Importaciones, rutas y datos"),
        code(SETUP),
        code(LOAD),
        markdown("## 2. Estadísticas y extremos territoriales"),
        code("""from IPython.display import Markdown, display
from src.dashboard_utils import generate_findings

findings = generate_findings(df)
summary = {
    "Pearson": round(findings["pearson_r"], 3),
    "Spearman": round(findings["spearman_r"], 3),
    "R²": round(findings["r_squared"], 3),
    "Dirección": findings["direction"],
    "Magnitud": findings["strength"],
    "Mayor disposición": findings["high_disposition"],
    "Mayor inseguridad": findings["high_insecurity"],
    "Mayor brecha positiva": findings["high_excess"],
}
summary"""),
        markdown("## 3. Hallazgo principal generado"),
        code("""assert "no demuestra causalidad" in findings["text"]
display(Markdown(f"> {findings['text']}"))"""),
        markdown("La lectura combina Pearson, Spearman, ajuste lineal y extremos por localidad. Mantiene explícita la diferencia entre asociación estadística y causalidad."),
    ],
    "07_dashboard_integrado_exportacion.ipynb": [
        markdown("""# Dashboard integrado y exportación

## 1. Objetivo

Responder de forma visual y reproducible la pregunta:

> **¿Existe una relación entre la proporción de hogares con disposición inadecuada de basura y la brecha de percepción de inseguridad en las localidades de Bogotá D.C.?**

Este notebook es el punto de entrada final: carga el dataset analítico común y las geometrías locales, reconstruye todos los componentes Plotly, integra una sola figura y exporta HTML, PDF y PNG."""),
        markdown("## 2. Importaciones"),
        code("""from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots"""),
        markdown("## 3. Configuración de rutas"),
        code(SETUP),
        code("""from src.dashboard_utils import (
    calculate_metrics,
    create_crime_rate_dotplot,
    create_disposition_map,
    create_indicators,
    create_insecurity_map,
    create_integrated_dashboard,
    create_ranking,
    create_scatter_relationship,
    export_dashboard_artifacts,
    generate_findings,
    generate_results_summary,
    load_dataset,
    load_geography,
    locality_key,
    validate_dataset,
)"""),
        markdown("## 4. Carga de datos"),
        code("""df = load_dataset(PROJECT_ROOT)
gdf, geojson = load_geography(PROJECT_ROOT, df["locality"])
print(f"Dataset: {len(df)} registros | Geometrías: {len(gdf)}")
df.head()"""),
        markdown("## 5. Validaciones finales"),
        code("""validation_report = validate_dataset(df)
assert len(df) == df["locality"].nunique() == len(gdf) == 19
assert set(df["locality"].map(locality_key)) == set(gdf["locality_key"])
assert df[["disposicion_inadecuada_pct", "insecurity_noche_pct"]].apply(lambda s: s.between(0, 100).all()).all()
validation_report"""),
        markdown("## 6. Cálculo de métricas"),
        code("""metrics = calculate_metrics(df)
initial_analysis = {
    "Localidades analizadas": len(df),
    "Hogares con disposición inadecuada, en promedio": f"{metrics['mean_disposition']:.1f} %",
    "Personas inseguras al caminar de noche, en promedio": f"{metrics['mean_insecurity']:.1f} %",
}
pd.Series(initial_analysis, name="Panorama general").to_frame()"""),
        markdown("## 7. Construcción de componentes"),
        code("""fig_kpis = create_indicators(df)
fig_scatter = create_scatter_relationship(df)
fig_delitos = create_crime_rate_dotplot(df)
fig_mapa_disposicion = create_disposition_map(df, geojson)
fig_mapa_inseguridad = create_insecurity_map(df, geojson)
fig_ranking = create_ranking(df)

assert [len(fig_kpis.data), len(fig_scatter.data)] == [4, 2]
assert fig_delitos.data[0].type == "scatter"
assert fig_mapa_disposicion.data[0].type == fig_mapa_inseguridad.data[0].type == "choropleth"
assert len(fig_ranking.layout.updatemenus[0].buttons) == 2
print("Componentes Plotly reconstruidos y validados.")"""),
        markdown("## 8. Integración del dashboard"),
        code("""fig_dashboard = create_integrated_dashboard(df, geojson)
assert len(fig_dashboard.data) == 10
assert "heatmap" not in {trace.type for trace in fig_dashboard.data}
assert [trace.type for trace in fig_dashboard.data[4:6]] == ["bar", "scatter"]
fig_dashboard.show(config={"displaylogo": False, "scrollZoom": True, "responsive": True})"""),
        markdown("## 9. Interpretación"),
        code("""from IPython.display import Markdown, display

results = generate_results_summary(df)
assert "no demuestra causa y efecto" in results
display(Markdown(f"> **Resultados.** {results}"))"""),
        markdown("""## 10. Exportación

El HTML incorpora Plotly completo (`include_plotlyjs=True`) y puede abrirse sin internet, Python, Jupyter, Dash o servidor. El PDF y el PNG son representaciones estáticas generadas con Kaleido. También se exportan las figuras documentales de respaldo."""),
        code("""exported_paths = export_dashboard_artifacts(fig_dashboard, df, geojson, PROJECT_ROOT)
for path in exported_paths:
    print(f"{path.relative_to(PROJECT_ROOT)}: {path.stat().st_size:,} bytes")"""),
        markdown("## 11. Verificación"),
        code("""required_outputs = [
    OUTPUTS_DIR / "dashboard_bogota.html",
    OUTPUTS_DIR / "dashboard_bogota.pdf",
    OUTPUTS_DIR / "dashboard_bogota_preview.png",
    FIGURES_DIR / "kpis.pdf",
    FIGURES_DIR / "relacion_scatter.pdf",
    FIGURES_DIR / "delitos_100k_localidad.pdf",
    FIGURES_DIR / "mapa_disposicion.pdf",
    FIGURES_DIR / "mapa_inseguridad.pdf",
    FIGURES_DIR / "ranking_localidades.pdf",
]
for output in required_outputs:
    assert output.exists(), f"Falta {output}"
    assert output.stat().st_size > 0, f"El archivo está vacío: {output}"

html_text = required_outputs[0].read_text(encoding="utf-8")
assert "plotly.js" in html_text.lower()
assert '<script src="https://cdn.plot.ly' not in html_text.lower()
assert "inadecuada de basura" in html_text.lower()
assert "causa y efecto" in html_text
print("Verificación aprobada: HTML autocontenido y todos los artefactos existen y no están vacíos.")"""),
        markdown("""### Alcance interpretativo

El análisis es ecológico y exploratorio a escala de localidad. La asociación observada no identifica mecanismos causales ni debe trasladarse automáticamente a hogares, personas o barrios."""),
    ],
}


def main() -> None:
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)
    for filename, cells in NOTEBOOK_DEFINITIONS.items():
        path = NOTEBOOKS / filename
        path.write_text(json.dumps(notebook(cells), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Creado: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

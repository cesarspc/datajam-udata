"""Funciones compartidas para el dashboard Plotly de Bogotá.

La capa de visualización reutiliza el producto analítico existente
``indice_localidad_disposicion_inadecuada.csv``. No reconstruye las fuentes
originales ni modifica la metodología del proyecto.
"""

from __future__ import annotations

import json
import re
import textwrap
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import linregress, pearsonr, spearmanr


SOURCE_DATASET = "indice_localidad_disposicion_inadecuada.csv"
DASHBOARD_DATASET = "dashboard_dataset.csv"
NUMERIC_COLUMNS = [
    "official_crimes_2025",
    "estimated_crimes_2025",
    "population_2025",
    "crime_rate_100k",
    "insecurity_noche_pct",
    "crime_z",
    "insecurity_z",
    "perception_excess_index",
    "disposicion_inadecuada_pct",
]
REQUIRED_COLUMNS = ["locality", *NUMERIC_COLUMNS]

DISPLAY_NAMES = {
    "disposicion_inadecuada_pct": "Disposición inadecuada",
    "insecurity_noche_pct": "Percepción de inseguridad",
    "crime_rate_100k": "Tasa de delitos",
    "perception_excess_index": "Brecha de percepción",
}

LOCALITY_NAMES = {
    "USAQUEN": "Usaquén",
    "CHAPINERO": "Chapinero",
    "SANTAFE": "Santa Fe",
    "SANCRISTOBAL": "San Cristóbal",
    "USME": "Usme",
    "TUNJUELITO": "Tunjuelito",
    "BOSA": "Bosa",
    "KENNEDY": "Kennedy",
    "FONTIBON": "Fontibón",
    "ENGATIVA": "Engativá",
    "SUBA": "Suba",
    "BARRIOSUNIDOS": "Barrios Unidos",
    "TEUSAQUILLO": "Teusaquillo",
    "LOSMARTIRES": "Los Mártires",
    "ANTONIONARINO": "Antonio Nariño",
    "PUENTEARANDA": "Puente Aranda",
    "LACANDELARIA": "La Candelaria",
    "CANDELARIA": "La Candelaria",
    "RAFAELURIBEURIBE": "Rafael Uribe Uribe",
    "CIUDADBOLIVAR": "Ciudad Bolívar",
    "SUMAPAZ": "Sumapaz",
}

COLORS = {
    "navy": "#14213D",
    "blue": "#1677A8",
    "teal": "#00A6A6",
    "orange": "#F28E2B",
    "red": "#C84C61",
    "gray": "#5F6B7A",
    "grid": "#E1E7ED",
    "paper": "#F4F6F8",
}


def project_root(start: Path | None = None) -> Path:
    """Resuelve la raíz sin rutas personales o absolutas codificadas."""
    root = Path.cwd() if start is None else Path(start)
    if root.name == "notebooks":
        root = root.parent
    if not (root / "data" / "processed").exists():
        raise FileNotFoundError("No se encontró data/processed desde el directorio actual.")
    return root


def locality_key(value: object) -> str:
    clean = re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()
    return re.sub(
        r"[^A-Z0-9]",
        "",
        unicodedata.normalize("NFKD", clean)
        .encode("ascii", "ignore")
        .decode()
        .upper(),
    )


def normalize_locality(value: object) -> str:
    """Devuelve el nombre oficial legible que corresponde a una localidad."""
    key = locality_key(value)
    if key not in LOCALITY_NAMES:
        raise ValueError(f"Localidad no reconocida: {value!r}")
    return LOCALITY_NAMES[key]


def validate_dataset(df: pd.DataFrame) -> dict:
    """Aplica las reglas de consistencia del dataset analítico común."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")
    if df.empty:
        raise ValueError("El dataset analítico está vacío.")
    if df["locality"].isna().any():
        raise ValueError("Existen localidades nulas.")
    duplicate_count = int(df["locality"].duplicated().sum())
    if duplicate_count:
        raise ValueError(f"Hay {duplicate_count} localidades duplicadas.")
    for column in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise TypeError(f"{column} no es una variable numérica.")
    if df[REQUIRED_COLUMNS].isna().any().any():
        nulls = df[REQUIRED_COLUMNS].isna().sum()
        raise ValueError(f"Hay valores faltantes:\n{nulls[nulls.gt(0)]}")
    for column in ["disposicion_inadecuada_pct", "insecurity_noche_pct"]:
        if not df[column].between(0, 100).all():
            raise ValueError(f"{column} debe estar en escala 0–100.")
    if df["locality"].nunique() != len(df):
        raise ValueError("Cada fila debe corresponder a una localidad.")
    return {
        "filas": int(len(df)),
        "localidades": int(df["locality"].nunique()),
        "duplicados": duplicate_count,
        "nulos": int(df[REQUIRED_COLUMNS].isna().sum().sum()),
        "escala_porcentajes": "0–100",
    }


def prepare_dashboard_dataset(root: Path | None = None) -> tuple[pd.DataFrame, dict, Path]:
    """Consolida de forma mínima el CSV procesado existente para el dashboard."""
    root = project_root(root)
    source = root / "data" / "processed" / SOURCE_DATASET
    destination = root / "data" / "processed" / DASHBOARD_DATASET
    if not source.exists():
        raise FileNotFoundError(f"No existe el insumo procesado: {source}")
    df = pd.read_csv(source)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"El insumo procesado no contiene: {missing_columns}")
    df = df[REQUIRED_COLUMNS].copy()
    df["locality"] = df["locality"].map(normalize_locality)
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.sort_values("locality").reset_index(drop=True)
    report = validate_dataset(df)
    df.to_csv(destination, index=False, encoding="utf-8")
    return df, report, destination


def load_dataset(root: Path | None = None) -> pd.DataFrame:
    root = project_root(root)
    path = root / "data" / "processed" / DASHBOARD_DATASET
    if not path.exists():
        raise FileNotFoundError(
            "Falta dashboard_dataset.csv. Ejecute primero 00_preparacion_y_validacion.ipynb."
        )
    df = pd.read_csv(path)
    df["locality"] = df["locality"].map(normalize_locality)
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="raise")
    validate_dataset(df)
    return df


def calculate_metrics(df: pd.DataFrame) -> dict:
    x = df["disposicion_inadecuada_pct"].to_numpy()
    y = df["perception_excess_index"].to_numpy()
    pearson_r, pearson_p = pearsonr(x, y)
    spearman_r, spearman_p = spearmanr(x, y)
    regression = linregress(x, y)
    return {
        "mean_disposition": float(df["disposicion_inadecuada_pct"].mean()),
        "mean_insecurity": float(df["insecurity_noche_pct"].mean()),
        "mean_excess": float(df["perception_excess_index"].mean()),
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "spearman_r": float(spearman_r),
        "spearman_p": float(spearman_p),
        "slope": float(regression.slope),
        "intercept": float(regression.intercept),
        "r_squared": float(regression.rvalue**2),
        "n": int(len(df)),
    }


def create_indicators(df: pd.DataFrame) -> go.Figure:
    metrics = calculate_metrics(df)
    fig = make_subplots(
        rows=1,
        cols=4,
        specs=[[{"type": "indicator"}] * 4],
        horizontal_spacing=0.05,
    )
    definitions = [
        (metrics["mean_disposition"], "Hogares con disposición<br>inadecuada, en promedio", ".1f", "%"),
        (metrics["mean_insecurity"], "Personas inseguras<br>al caminar de noche", ".1f", "%"),
        (metrics["pearson_r"], "Relación lineal<br>(Pearson)", ".2f", ""),
        (metrics["spearman_r"], "Orden similar entre localidades<br>(Spearman)", ".2f", ""),
    ]
    for col, (value, title, valueformat, suffix) in enumerate(definitions, start=1):
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value,
                number={"valueformat": valueformat, "suffix": suffix, "font": {"size": 36, "color": COLORS["navy"]}},
                title={"text": title, "font": {"size": 14, "color": COLORS["gray"]}},
            ),
            row=1,
            col=col,
        )
    fig.update_layout(
        title="Lo esencial en cifras",
        height=260,
        paper_bgcolor=COLORS["paper"],
        font={"family": "Arial", "color": COLORS["navy"]},
        margin={"l": 35, "r": 35, "t": 75, "b": 25},
    )
    return fig


def _quadrant_annotations(fig: go.Figure, df: pd.DataFrame, row=None, col=None) -> None:
    x = df["disposicion_inadecuada_pct"]
    y = df["perception_excess_index"]
    positions = [
        ((x.mean() + x.max()) / 2, (y.mean() + y.max()) / 2, "Más disposición / brecha alta"),
        ((x.mean() + x.max()) / 2, (y.mean() + y.min()) / 2, "Más disposición / brecha baja"),
        ((x.mean() + x.min()) / 2, (y.mean() + y.max()) / 2, "Menos disposición / brecha alta"),
        ((x.mean() + x.min()) / 2, (y.mean() + y.min()) / 2, "Menos disposición / brecha baja"),
    ]
    for xpos, ypos, label in positions:
        kwargs = {"row": row, "col": col} if row is not None else {}
        fig.add_annotation(
            x=xpos,
            y=ypos,
            text=label,
            showarrow=False,
            font={"size": 18, "color": COLORS["gray"]},
            bgcolor="rgba(255,255,255,0.70)",
            borderpad=2,
            **kwargs,
        )


def create_scatter_relationship(df: pd.DataFrame) -> go.Figure:
    metrics = calculate_metrics(df)
    x = df["disposicion_inadecuada_pct"]
    y = df["perception_excess_index"]
    xline = np.linspace(x.min(), x.max(), 100)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            name="Localidades",
            customdata=np.column_stack([df["locality"], df["insecurity_noche_pct"]]),
            marker={"size": 12, "color": y, "colorscale": "RdBu", "reversescale": True,
                    "line": {"width": 1, "color": "white"}, "showscale": False},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Disposición inadecuada: %{x:.1f} %"
                "<br>Brecha de percepción: %{y:.2f}"
                "<br>Inseguridad nocturna: %{customdata[1]:.1f} %<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xline,
            y=metrics["intercept"] + metrics["slope"] * xline,
            mode="lines",
            name="Tendencia lineal",
            line={"color": COLORS["orange"], "width": 3},
            hoverinfo="skip",
        )
    )
    fig.add_vline(x=x.mean(), line_dash="dash", line_color=COLORS["gray"], opacity=0.75)
    fig.add_hline(y=y.mean(), line_dash="dash", line_color=COLORS["gray"], opacity=0.75)
    _quadrant_annotations(fig, df)
    fig.add_annotation(
        x=0.01,
        y=0.99,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        showarrow=False,
        text=(f"Pearson: r = {metrics['pearson_r']:.2f} | "
              f"Spearman: ρ = {metrics['spearman_r']:.2f} | R² = {metrics['r_squared']:.2f}"),
        bgcolor="rgba(255,255,255,0.85)",
        font={"size": 12, "color": COLORS["navy"]},
    )
    fig.update_layout(
        title="Relación entre disposición inadecuada y brecha de percepción",
        xaxis_title="Hogares con disposición inadecuada (%)",
        yaxis_title="Brecha de percepción (inseguridad − delitos, índice estandarizado)",
        template="plotly_white",
        height=620,
        font={"family": "Arial", "color": COLORS["navy"]},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        margin={"l": 80, "r": 35, "t": 100, "b": 75},
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])
    return fig


def create_direct_relationship(df: pd.DataFrame) -> go.Figure:
    """Muestra la relación directa entre disposición e inseguridad nocturna.

    El gráfico de dispersión es la forma estándar y más familiar de mostrar
    la relación entre dos variables cuantitativas. Cada punto conserva la
    localidad y la recta se calcula directamente desde los datos.
    """
    x = df["disposicion_inadecuada_pct"].to_numpy()
    y = df["insecurity_noche_pct"].to_numpy()
    relationship, _ = pearsonr(x, y)
    regression = linregress(x, y)
    xline = np.linspace(x.min(), x.max(), 100)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            name="Localidades",
            customdata=df[["locality"]],
            marker={
                "size": 12,
                "color": COLORS["teal"],
                "line": {"width": 1.2, "color": "white"},
            },
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Hogares con disposición inadecuada: %{x:.1f} %"
                "<br>Personas que se sienten inseguras de noche: %{y:.1f} %<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xline,
            y=regression.intercept + regression.slope * xline,
            mode="lines",
            name="Tendencia general",
            line={"color": COLORS["navy"], "width": 3},
            hoverinfo="skip",
        )
    )
    fig.add_annotation(
        x=0.02,
        y=0.98,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        text=(
            f"<b>Relación positiva moderada</b> (r = {relationship:.2f})<br>"
            "Cada punto representa una localidad."
        ),
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=COLORS["grid"],
        borderwidth=1,
        borderpad=8,
        font={"size": 13, "color": COLORS["navy"]},
    )
    fig.update_layout(
        title="Disposición inadecuada e inseguridad al caminar de noche",
        xaxis_title="Hogares con disposición inadecuada (%)",
        yaxis_title="Personas que se sienten inseguras de noche (%)",
        template="plotly_white",
        height=600,
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor="white",
        font={"family": "Arial", "color": COLORS["navy"]},
        legend={"orientation": "h", "y": 1.10, "x": 0},
        margin={"l": 80, "r": 35, "t": 105, "b": 75},
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False)
    return fig


def load_geography(root: Path | None = None, localities: pd.Series | None = None) -> tuple[gpd.GeoDataFrame, dict]:
    root = project_root(root)
    path = root / "data" / "raw" / "dai_shp" / "DAILoc.shp"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el shapefile local: {path}")
    gdf = gpd.read_file(path)[["CMIULOCAL", "CMNOMLOCAL", "geometry"]].copy()
    gdf = gdf[gdf["CMIULOCAL"].astype(str).str.zfill(2).ne("99")]
    gdf["locality"] = gdf["CMNOMLOCAL"].map(normalize_locality)
    gdf["locality_key"] = gdf["locality"].map(locality_key)
    if localities is not None:
        allowed = {locality_key(value) for value in localities}
        gdf = gdf[gdf["locality_key"].isin(allowed)].copy()
    if gdf["locality_key"].duplicated().any():
        raise ValueError("El shapefile contiene localidades duplicadas.")
    gdf = gdf.to_crs(epsg=4326)
    geojson = json.loads(gdf.to_json(drop_id=True))
    return gdf, geojson


def _create_map(df: pd.DataFrame, geojson: dict, variable: str, title: str, colorscale: str) -> go.Figure:
    map_df = df.assign(locality_key=df["locality"].map(locality_key))
    suffix = " %" if variable.endswith("_pct") else ""
    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            locations=map_df["locality_key"],
            z=map_df[variable],
            featureidkey="properties.locality_key",
            customdata=map_df[["locality", variable]],
            colorscale=colorscale,
            marker_line_color="white",
            marker_line_width=0.8,
            colorbar={"title": "%" if suffix else "Índice", "thickness": 14},
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>{title}: %{{customdata[1]:.1f}}{suffix}<extra></extra>",
        )
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title=title,
        height=650,
        font={"family": "Arial", "color": COLORS["navy"]},
        margin={"l": 15, "r": 30, "t": 80, "b": 20},
    )
    return fig


def create_disposition_map(df: pd.DataFrame, geojson: dict) -> go.Figure:
    return _create_map(
        df,
        geojson,
        "disposicion_inadecuada_pct",
        "Disposición inadecuada de basura por localidad",
        [[0.0, "#FFF4E6"], [0.5, "#F4A261"], [1.0, "#B54708"]],
    )


def create_insecurity_map(df: pd.DataFrame, geojson: dict) -> go.Figure:
    """Mapa de la brecha estandarizada entre percepción y delitos."""
    map_df = df.assign(locality_key=df["locality"].map(locality_key))
    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            locations=map_df["locality_key"],
            z=map_df["perception_excess_index"],
            zmid=0,
            featureidkey="properties.locality_key",
            customdata=map_df[["locality", "perception_excess_index"]],
            colorscale=[[0.0, "#1677A8"], [0.5, "#F7F8FA"], [1.0, "#C84C61"]],
            marker_line_color="white",
            marker_line_width=0.8,
            colorbar={"title": "Desv.<br>estándar", "thickness": 14},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Brecha de percepción: "
                "%{customdata[1]:.2f} desviaciones estándar<extra></extra>"
            ),
        )
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title="Brecha entre percepción de inseguridad y delitos por localidad",
        height=650,
        font={"family": "Arial", "color": COLORS["navy"]},
        margin={"l": 15, "r": 30, "t": 80, "b": 20},
    )
    return fig


def create_crime_rate_dotplot(df: pd.DataFrame) -> go.Figure:
    """Compara la tasa estimada de delitos mediante puntos, sin otra variable."""
    ordered = df.sort_values("crime_rate_100k")
    mean_rate = float(ordered["crime_rate_100k"].mean())
    fig = go.Figure(
        go.Scatter(
            x=ordered["crime_rate_100k"],
            y=ordered["locality"],
            mode="markers",
            marker={"size": 16, "color": COLORS["teal"], "line": {"width": 2, "color": "white"}},
            customdata=ordered[["locality"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Delitos estimados por cada 100.000 habitantes: "
                "%{x:,.0f}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.add_vline(x=mean_rate, line_dash="dash", line_color=COLORS["gray"])
    fig.add_annotation(
        x=mean_rate,
        y=1.04,
        xref="x",
        yref="paper",
        text=f"Promedio: {mean_rate:,.0f}",
        showarrow=False,
        font={"size": 15, "color": COLORS["gray"]},
    )
    fig.update_layout(
        title="Delitos estimados por cada 100.000 habitantes",
        xaxis_title="Delitos estimados por cada 100.000 habitantes",
        yaxis_title="Localidad",
        height=720,
        template="plotly_white",
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor="white",
        font={"family": "Arial", "color": COLORS["navy"]},
        margin={"l": 140, "r": 40, "t": 100, "b": 70},
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig


def create_ranking(df: pd.DataFrame) -> go.Figure:
    disposition = df.sort_values("disposicion_inadecuada_pct")
    insecurity = df.sort_values("insecurity_noche_pct")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=disposition["disposicion_inadecuada_pct"],
            y=disposition["locality"],
            orientation="h",
            name="Disposición inadecuada",
            marker_color=COLORS["orange"],
            customdata=disposition[["locality"]],
            hovertemplate="<b>%{customdata[0]}</b><br>Disposición inadecuada: %{x:.1f} %<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=insecurity["insecurity_noche_pct"],
            y=insecurity["locality"],
            orientation="h",
            name="Percepción de inseguridad",
            marker_color=COLORS["blue"],
            customdata=insecurity[["locality"]],
            hovertemplate="<b>%{customdata[0]}</b><br>Percepción de inseguridad: %{x:.1f} %<extra></extra>",
            visible=False,
        )
    )
    fig.update_layout(
        title="Ranking de localidades: disposición inadecuada",
        xaxis_title="Hogares con disposición inadecuada (%)",
        yaxis_title="Localidad",
        height=720,
        template="plotly_white",
        font={"family": "Arial", "color": COLORS["navy"]},
        showlegend=False,
        margin={"l": 135, "r": 40, "t": 100, "b": 70},
        updatemenus=[
            {
                "type": "dropdown",
                "direction": "down",
                "x": 1,
                "xanchor": "right",
                "y": 1.14,
                "buttons": [
                    {
                        "label": "Disposición inadecuada",
                        "method": "update",
                        "args": [
                            {"visible": [True, False]},
                            {
                                "title": "Ranking de localidades: disposición inadecuada",
                                "xaxis": {"title": "Hogares con disposición inadecuada (%)"},
                                "yaxis": {"categoryorder": "array", "categoryarray": disposition["locality"].tolist()},
                            },
                        ],
                    },
                    {
                        "label": "Percepción de inseguridad",
                        "method": "update",
                        "args": [
                            {"visible": [False, True]},
                            {
                                "title": "Ranking de localidades: percepción de inseguridad",
                                "xaxis": {"title": "Personas que se sienten inseguras de noche (%)"},
                                "yaxis": {"categoryorder": "array", "categoryarray": insecurity["locality"].tolist()},
                            },
                        ],
                    },
                ],
            }
        ],
    )
    return fig


def correlation_strength(value: float) -> str:
    """Clasificación descriptiva documentada por magnitud absoluta."""
    magnitude = abs(value)
    if magnitude < 0.2:
        return "muy débil"
    if magnitude < 0.4:
        return "débil"
    if magnitude < 0.6:
        return "moderada"
    if magnitude < 0.8:
        return "fuerte"
    return "muy fuerte"


def generate_findings(df: pd.DataFrame) -> dict:
    metrics = calculate_metrics(df)
    direction = "positiva" if metrics["pearson_r"] > 0 else "negativa" if metrics["pearson_r"] < 0 else "nula"
    strength = correlation_strength(metrics["pearson_r"])
    high_disposition = df.nlargest(3, "disposicion_inadecuada_pct")["locality"].tolist()
    high_insecurity = df.nlargest(3, "insecurity_noche_pct")["locality"].tolist()
    high_excess = df.nlargest(1, "perception_excess_index").iloc[0]
    text = (
        f"En las {metrics['n']} localidades analizadas, una mayor disposición inadecuada tiende a coincidir "
        f"con una mayor brecha entre la inseguridad que percibe la ciudadanía y los delitos estimados. "
        f"La relación es {direction} y de intensidad {strength}. "
        f"{high_disposition[0]} registra la mayor proporción de disposición inadecuada y "
        f"{high_insecurity[0]} la mayor percepción de inseguridad nocturna. "
        "Este patrón territorial no demuestra causalidad: no permite concluir que una variable cause la otra. "
        f"Respaldo estadístico: Pearson = {metrics['pearson_r']:.2f}; "
        f"Spearman = {metrics['spearman_r']:.2f}; R² = {metrics['r_squared']:.2f}."
    )
    return {
        "text": text,
        "direction": direction,
        "strength": strength,
        "high_disposition": high_disposition,
        "high_insecurity": high_insecurity,
        "high_excess": str(high_excess["locality"]),
        **metrics,
    }


def generate_results_summary(df: pd.DataFrame) -> str:
    """Resultado breve y ciudadano, calculado desde los indicadores finales."""
    metrics = calculate_metrics(df)
    direction = "en el mismo sentido" if metrics["pearson_r"] > 0 else "en sentidos opuestos"
    strength = correlation_strength(metrics["pearson_r"])
    return (
        "Donde aumenta la disposición inadecuada, también tiende a aumentar la brecha entre "
        "inseguridad percibida y delitos estimados. "
        f"La relación es {strength} y va {direction} "
        f"(Pearson {metrics['pearson_r']:.2f}; Spearman {metrics['spearman_r']:.2f}); "
        "no demuestra causa y efecto."
    )


def _wrap_html(text: str, width: int = 145) -> str:
    return "<br>".join(textwrap.wrap(text, width=width, break_long_words=False))


def create_integrated_dashboard(df: pd.DataFrame, geojson: dict) -> go.Figure:
    """Construye la figura única usada por HTML, PDF y PNG."""
    metrics = calculate_metrics(df)
    results_text = generate_results_summary(df)
    fig = make_subplots(
        rows=4,
        cols=4,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
            [{"type": "xy", "colspan": 2}, None, {"type": "xy", "colspan": 2}, None],
            [{"type": "choropleth", "colspan": 2}, None, {"type": "choropleth", "colspan": 2}, None],
            [{"type": "xy", "colspan": 4}, None, None, None],
        ],
        row_heights=[0.10, 0.31, 0.25, 0.34],
        vertical_spacing=0.085,
        horizontal_spacing=0.08,
        subplot_titles=(
            "", "", "", "",
            "Hogares con disposición inadecuada por localidad",
            "Delitos estimados por cada 100.000 habitantes",
            "¿Dónde hay más disposición inadecuada?",
            "¿Dónde es mayor la brecha de percepción?",
            "Relación entre disposición inadecuada y brecha de percepción",
        ),
    )
    for annotation in fig.layout.annotations:
        annotation.font = {"size": 26, "color": COLORS["navy"]}

    indicator_definitions = [
        (metrics["mean_disposition"], "Hogares con disposición<br>inadecuada, en promedio", ".1f", "%"),
        (metrics["mean_insecurity"], "Personas inseguras<br>al caminar de noche", ".1f", "%"),
        (metrics["pearson_r"], "Relación lineal<br>(Pearson)", ".2f", ""),
        (metrics["spearman_r"], "Orden similar entre localidades<br>(Spearman)", ".2f", ""),
    ]
    for col, (value, title, valueformat, suffix) in enumerate(indicator_definitions, start=1):
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value,
                number={"valueformat": valueformat, "suffix": suffix, "font": {"size": 58, "color": COLORS["navy"]}},
                title={"text": title, "font": {"size": 24, "color": COLORS["gray"]}},
            ),
            row=1,
            col=col,
        )

    # Primero se presentan las variables por separado.
    disposition = df.sort_values("disposicion_inadecuada_pct")
    fig.add_trace(
        go.Bar(
            x=disposition["disposicion_inadecuada_pct"],
            y=disposition["locality"],
            orientation="h",
            marker_color=COLORS["orange"],
            customdata=disposition[["locality"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Hogares con disposición inadecuada: "
                "%{x:.1f} %<extra></extra>"
            ),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    crimes = df.sort_values("crime_rate_100k")
    mean_crime_rate = float(crimes["crime_rate_100k"].mean())
    fig.add_trace(
        go.Scatter(
            x=crimes["crime_rate_100k"],
            y=crimes["locality"],
            mode="markers",
            marker={"size": 19, "color": COLORS["teal"], "line": {"width": 2, "color": "white"}},
            customdata=crimes[["locality"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Delitos estimados por cada 100.000 habitantes: "
                "%{x:,.0f}<extra></extra>"
            ),
            showlegend=False,
        ),
        row=2,
        col=3,
    )
    fig.add_shape(
        type="line", x0=mean_crime_rate, x1=mean_crime_rate, y0=0, y1=1,
        xref="x2", yref="y2 domain",
        line={"dash": "dash", "width": 3, "color": COLORS["gray"]},
    )
    fig.add_annotation(
        x=mean_crime_rate,
        y=0.99,
        xref="x2",
        yref="y2 domain",
        text=f"<b>Promedio: {mean_crime_rate:,.0f}</b>",
        showarrow=False,
        xanchor="right",
        yanchor="top",
        font={"size": 21, "color": COLORS["gray"]},
    )

    map_df = df.assign(locality_key=df["locality"].map(locality_key))
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_df["locality_key"],
            z=map_df["disposicion_inadecuada_pct"],
            featureidkey="properties.locality_key",
            customdata=map_df[["locality", "disposicion_inadecuada_pct"]],
            colorscale=[[0.0, "#FFF4E6"], [0.5, "#F4A261"], [1.0, "#B54708"]],
            marker_line_color="white",
            marker_line_width=0.7,
            colorbar={"title": {"text": "%", "font": {"size": 22}}, "tickfont": {"size": 19},
                      "thickness": 15, "len": 0.17, "y": 0.43, "x": 0.46},
            hovertemplate="<b>%{customdata[0]}</b><br>Disposición inadecuada: %{customdata[1]:.1f} %<extra></extra>",
            name="Disposición inadecuada",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=map_df["locality_key"],
            z=map_df["perception_excess_index"],
            zmid=0,
            featureidkey="properties.locality_key",
            customdata=map_df[["locality", "perception_excess_index"]],
            colorscale=[[0.0, "#1677A8"], [0.5, "#F7F8FA"], [1.0, "#C84C61"]],
            marker_line_color="white",
            marker_line_width=0.7,
            colorbar={"title": {"text": "Desv.<br>estándar", "font": {"size": 20}}, "tickfont": {"size": 19},
                      "thickness": 15, "len": 0.17, "y": 0.43, "x": 1.01},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Brecha de percepción: "
                "%{customdata[1]:.2f} desviaciones estándar<extra></extra>"
            ),
            name="Brecha de percepción",
        ),
        row=3,
        col=3,
    )

    # Finalmente se cruzan los dos índices principales.
    x = df["disposicion_inadecuada_pct"]
    y = df["perception_excess_index"]
    xline = np.linspace(x.min(), x.max(), 100)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker={"size": 19, "color": COLORS["blue"], "line": {"width": 2, "color": "white"}},
            customdata=np.column_stack([df["locality"], df["insecurity_noche_pct"]]),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Disposición inadecuada: %{x:.1f} %"
                "<br>Brecha de percepción: %{y:.2f} desviaciones estándar"
                "<br>Inseguridad nocturna: %{customdata[1]:.1f} %<extra></extra>"
            ),
            showlegend=False,
        ),
        row=4,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xline,
            y=metrics["intercept"] + metrics["slope"] * xline,
            mode="lines",
            line={"color": COLORS["orange"], "width": 5},
            hoverinfo="skip",
            showlegend=False,
        ),
        row=4,
        col=1,
    )
    fig.add_shape(
        type="line", x0=x.mean(), x1=x.mean(), y0=0, y1=1,
        xref="x3", yref="y3 domain", line={"dash": "dash", "width": 3, "color": COLORS["gray"]},
    )
    fig.add_shape(
        type="line", x0=0, x1=1, y0=y.mean(), y1=y.mean(),
        xref="x3 domain", yref="y3", line={"dash": "dash", "width": 3, "color": COLORS["gray"]},
    )
    _quadrant_annotations(fig, df, row=4, col=1)
    fig.add_annotation(
        x=0.015,
        y=0.98,
        xref="x3 domain",
        yref="y3 domain",
        xanchor="left",
        yanchor="top",
        align="left",
        showarrow=False,
        text=(
            f"<b>Asociación positiva {correlation_strength(metrics['pearson_r'])}</b><br>"
            f"Pearson {metrics['pearson_r']:.2f} · Spearman {metrics['spearman_r']:.2f}<br>"
            "<b>Cómo leer la unidad:</b> 0 es la brecha promedio; +1 es una desviación estándar "
            "por encima y −1 una por debajo."
        ),
        bgcolor="rgba(255,255,255,0.94)",
        bordercolor=COLORS["grid"],
        borderwidth=1,
        borderpad=12,
        font={"size": 21, "color": COLORS["navy"]},
    )

    fig.update_layout(
        width=1800,
        height=3200,
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor="white",
        font={"family": "Arial", "color": COLORS["navy"], "size": 26},
        margin={"l": 225, "r": 150, "t": 500, "b": 430},
        showlegend=False,
    )
    fig.update_geos(fitbounds="locations", visible=False)
    axis_title_font = {"size": 24, "color": COLORS["navy"]}
    axis_tick_font = {"size": 20, "color": COLORS["navy"]}
    fig.update_xaxes(
        title_text="Hogares con disposición inadecuada (%)",
        title_font=axis_title_font, tickfont=axis_tick_font,
        row=2, col=1,
        gridcolor=COLORS["grid"],
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="", tickfont={"size": 19, "color": COLORS["navy"]},
        row=2, col=1,
    )
    fig.update_xaxes(
        title_text="Delitos estimados por cada 100.000 habitantes",
        title_font=axis_title_font, tickfont=axis_tick_font,
        row=2, col=3,
        gridcolor=COLORS["grid"],
        zeroline=False,
    )
    fig.update_yaxes(title_text="", tickfont={"size": 19, "color": COLORS["navy"]}, row=2, col=3)
    fig.update_xaxes(
        title_text="Hogares con disposición inadecuada (%)",
        title_font=axis_title_font, tickfont=axis_tick_font,
        row=4, col=1, gridcolor=COLORS["grid"], zeroline=False,
    )
    fig.update_yaxes(
        title_text="Brecha de percepción (desviaciones estándar)",
        title_font=axis_title_font, tickfont=axis_tick_font,
        row=4, col=1, gridcolor=COLORS["grid"], zeroline=False,
    )

    # Tarjetas blancas y dos mensajes iniciales, uno por línea.
    for x0, x1 in [(0.0, 0.19), (0.27, 0.46), (0.54, 0.73), (0.81, 1.0)]:
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=0.925,
            y1=1.006,
            xref="paper",
            yref="paper",
            fillcolor="white",
            line={"color": COLORS["grid"], "width": 1},
            layer="below",
        )
    fig.add_shape(
        type="rect",
        x0=0,
        x1=1,
        y0=0.852,
        y1=0.914,
        xref="paper",
        yref="paper",
        fillcolor="white",
        line={"color": COLORS["grid"], "width": 1},
        layer="below",
    )
    fig.add_annotation(
        x=0.02,
        y=0.895,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="middle",
        align="left",
        showarrow=False,
        text=f"<b>{metrics['mean_disposition']:.0f} de cada 100 hogares</b> reportan disposición inadecuada de basura.",
        font={"size": 27, "color": COLORS["navy"]},
    )
    fig.add_annotation(
        x=0.02, y=0.869, xref="paper", yref="paper",
        xanchor="left", yanchor="middle", align="left", showarrow=False,
        text=f"<b>{metrics['mean_insecurity']:.0f} de cada 100 personas</b> se sienten inseguras al caminar de noche.",
        font={"size": 27, "color": COLORS["navy"]},
    )
    # Encabezado alineado a la izquierda, con jerarquía similar a los tableros
    # institucionales usados como referencia visual.
    fig.add_annotation(
        x=0,
        y=1.17,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        align="left",
        showarrow=False,
        text=(
            "<b>Disposición inadecuada de basura<br>y percepción de inseguridad</b><br>"
            f"<span style='font-size:30px;color:{COLORS['teal']}'>Bogotá D.C. · {metrics['n']} localidades analizadas</span><br>"
            "<span style='font-size:26px'>¿En qué medida ambas situaciones tienden a presentarse juntas en las localidades?</span>"
        ),
        font={"size": 52, "color": COLORS["navy"]},
    )
    fig.add_annotation(
        x=0,
        y=-0.055,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        align="left",
        showarrow=False,
        text=(
            "<span style='font-size:34px'><b>Resultados</b></span><br>"
            + _wrap_html(results_text, width=110)
            + "<br><br><span style='font-size:20px'>Fuentes: datos procesados del proyecto y límites de localidades DAILoc.</span>"
        ),
        font={"size": 25, "color": COLORS["navy"]},
        bgcolor="white",
        bordercolor=COLORS["grid"],
        borderwidth=1,
        borderpad=12,
    )
    return fig


def export_dashboard_artifacts(fig: go.Figure, df: pd.DataFrame, geojson: dict, root: Path | None = None) -> list[Path]:
    """Exporta la figura integrada y las vistas estáticas documentales."""
    root = project_root(root)
    outputs = root / "outputs"
    figures = outputs / "figures"
    outputs.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    obsolete_heatmap = figures / "heatmap_correlaciones.pdf"
    if obsolete_heatmap.exists():
        obsolete_heatmap.unlink()
    obsolete_direct = figures / "relacion_directa_inseguridad.pdf"
    if obsolete_direct.exists():
        obsolete_direct.unlink()

    html_path = outputs / "dashboard_bogota.html"
    pdf_path = outputs / "dashboard_bogota.pdf"
    png_path = outputs / "dashboard_bogota_preview.png"
    fig.write_html(html_path, include_plotlyjs=True, full_html=True)
    fig.write_image(pdf_path, format="pdf", width=1800, height=3200, scale=1)
    fig.write_image(png_path, format="png", width=1800, height=3200, scale=1)

    individual = [
        (create_indicators(df), figures / "kpis.pdf", 1400, 280),
        (create_scatter_relationship(df), figures / "relacion_scatter.pdf", 1100, 700),
        (create_crime_rate_dotplot(df), figures / "delitos_100k_localidad.pdf", 1100, 800),
        (create_disposition_map(df, geojson), figures / "mapa_disposicion.pdf", 900, 700),
        (create_insecurity_map(df, geojson), figures / "mapa_inseguridad.pdf", 900, 700),
        (create_ranking(df), figures / "ranking_localidades.pdf", 1000, 800),
    ]
    for component, path, width, height in individual:
        component.write_image(path, format="pdf", width=width, height=height, scale=1)

    paths = [html_path, pdf_path, png_path, *(item[1] for item in individual)]
    for path in paths:
        if not path.exists() or path.stat().st_size <= 0:
            raise AssertionError(f"La exportación no generó un archivo válido: {path}")
    return paths

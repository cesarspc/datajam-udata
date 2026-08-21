# Basura, percepción y crimen en Bogotá D.C.

Dashboard territorial interactivo para explorar la disposición inadecuada de basura, los delitos de alto impacto y la percepción de inseguridad en 19 localidades de Bogotá D.C. durante 2025.

El producto principal es un único archivo HTML construido con Plotly, sin Dash ni servidor. La versión publicada está disponible en:

**[Abrir dashboard interactivo en línea](https://udata.cesaraupc.workers.dev/)**

Para utilizar la copia generada dentro del repositorio, abra `outputs/dashboard_bogota.html` en el navegador.

![Pantalla principal del dashboard](outputs/capturas/01_inicio.png)

## Descripción del problema abordado

El proyecto busca responder la siguiente pregunta:

> **¿Existe una relación entre la proporción de hogares con disposición inadecuada de basura y la brecha de percepción de inseguridad en las localidades de Bogotá D.C.?**

La inseguridad que percibe la ciudadanía no necesariamente coincide con el número de delitos registrados. Además, los conteos administrativos no incluyen los hechos que no fueron denunciados y los valores absolutos están influidos por el tamaño de la población de cada localidad.

Por esta razón, la herramienta integra información ambiental, delictiva, demográfica y de percepción. El dashboard permite examinar por separado cada componente y posteriormente analizar su relación territorial. Los resultados describen asociaciones y no demuestran causalidad.

## Principales funcionalidades

La pantalla inicial permite acceder a cuatro paneles:

1. **Crímenes de alto impacto:** mapas de delitos registrados, tasa oficial por cada 100.000 habitantes y tasa estimada al incorporar la no denuncia. La selección de una localidad actualiza el desglose por tipo de delito y muestra sus valores territoriales.
2. **Disposición inadecuada de basura:** comparación del porcentaje de hogares por localidad mediante barras seleccionables.
3. **Percepción frente a la tasa de crímenes:** respuestas de denuncia, percepción de inseguridad nocturna y construcción territorial del índice de brecha perceptual.
4. **Brecha de percepción y disposición inadecuada:** diagrama de dispersión, tendencia general y mapa del aporte de cada localidad a la asociación observada.

Todas las gráficas permiten consultar valores mediante hover. Los mapas y las barras incorporan selecciones enlazadas mediante JavaScript embebido en el mismo HTML.

## Fuentes de datos utilizadas

| Fuente local | Contenido utilizado |
|---|---|
| `data/raw/botaderos_inadecuados.csv` | Hogares que reportan disposición inadecuada de basura por localidad. |
| `data/raw/delitos_alto_impacto.geojson` | Conteos de delitos de alto impacto registrados durante 2025 y su desglose por tipo. |
| `data/raw/encuesta_distrital_percepcion_2025.xlsx` | Personas y hogares que reportaron denunciar, porcentaje de denuncia y percepción de inseguridad al caminar de noche. |
| `data/raw/proyecciones_poblacion_localidad_2005_2035.ods` | Población proyectada para 2025, utilizada para calcular tasas por cada 100.000 habitantes. |
| `data/raw/dai_shp/DAILoc.shp` | Límites geográficos de las localidades de Bogotá. |

Los archivos procesados reutilizados son:

- `data/processed/botaderos_inadecuados-procesado.csv`;
- `data/processed/indice_localidad_disposicion_inadecuada.csv`;
- `data/processed/dashboard_dataset.csv`.

El notebook final genera dos tablas auxiliares necesarias para las interacciones que no estaban disponibles en el dataset analítico principal:

- `data/processed/dashboard_crime_detail.csv`;
- `data/processed/dashboard_reporting_summary.csv`.

La trazabilidad metodológica de las fuentes también se documenta en [`docs/Nota técnica sobre integración de datos públicos.pdf`](docs/Nota%20técnica%20sobre%20integración%20de%20datos%20públicos.pdf).

## Metodología general

1. **Integración territorial:** se normalizan los nombres de las localidades y se conserva una fila por localidad en el dataset analítico común.
2. **Crímenes registrados:** se suman ocho categorías de delitos de alto impacto disponibles para 2025.
3. **Ajuste por no denuncia:** cada tipo de delito se ajusta con la proporción de hogares que afirmó haber denunciado. La metodología existente limita estas proporciones entre 10 % y 95 % para evitar estimaciones inestables por celdas pequeñas.
4. **Tasas comparables:** los delitos registrados y estimados se relacionan con la población proyectada y se expresan por cada 100.000 habitantes.
5. **Percepción nocturna:** se suman las respuestas «Inseguro/a» y «Muy inseguro» a la pregunta sobre caminar solo por el barrio de noche.
6. **Estandarización:** la percepción de inseguridad y el logaritmo de la tasa estimada de delitos se convierten en puntuaciones z. Una unidad representa una desviación estándar respecto al promedio de las localidades.
7. **Brecha perceptual:** se calcula como `inseguridad estandarizada − tasa de delitos estandarizada`. Un valor positivo indica que la percepción de inseguridad se encuentra por encima de lo sugerido por la tasa estimada relativa.
8. **Análisis de asociación:** se calculan las correlaciones de Pearson y Spearman entre la disposición inadecuada y la brecha perceptual, junto con una tendencia lineal. No se realizan afirmaciones causales.

En las 19 localidades analizadas se obtuvo una asociación positiva moderada: Pearson `0,59` y Spearman `0,71`.

## Instrucciones de despliegue

### Uso local

Después de ejecutar el proyecto, no es necesario iniciar un servidor. Abra en Chrome, Edge o Firefox:

```text
outputs/dashboard_bogota.html
```

El archivo contiene Plotly y todos los datos necesarios. Funciona sin conexión a internet, Python o Jupyter.

### Publicación web

La versión pública de este proyecto se encuentra desplegada en Cloudflare Workers:

**<https://udata.cesaraupc.workers.dev/>**

## Instrucciones de ejecución

### Requisitos previos

- Python 3 con acceso a `venv` y `pip`;
- Git, si se va a clonar el repositorio;
- espacio libre suficiente para instalar las dependencias y generar el HTML autocontenido;
- ejecutar los comandos desde la raíz `datajam-udata/`.

No se necesitan credenciales, API, conexión a una base de datos ni descarga adicional de datos.

### 1. Obtener el proyecto y crear el entorno

```bash
git clone https://github.com/cesarspc/datajam-udata.git
cd datajam-udata

python -m venv .venv
```

Active el entorno según el sistema operativo:

```bash
# Linux o macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bat
:: Windows CMD
.venv\Scripts\activate.bat
```

Instale todas las dependencias declaradas por el proyecto:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Ejecución mínima recomendada

El repositorio ya incluye `data/processed/dashboard_dataset.csv`. Por tanto, para reproducir el producto final solo se ejecuta el notebook `07` con un kernel limpio:

```bash
python scripts/execute_dashboard_notebooks.py \
  notebooks/07_dashboard_integrado_exportacion.ipynb
```

El script abre el notebook, ejecuta todas sus celdas desde cero, detiene la ejecución si encuentra un error y guarda en el mismo notebook las salidas producidas. Al finalizar debe mostrar un mensaje similar a:

```text
APROBADO 07_dashboard_integrado_exportacion.ipynb: 12 celdas de código, kernel limpio, sin errores
```

Como alternativa, puede hacerse desde Jupyter:

```bash
jupyter lab
```

Abra `notebooks/07_dashboard_integrado_exportacion.ipynb`, seleccione **Kernel > Restart Kernel and Run All Cells** y espere la confirmación de verificación de la última celda.

### 3. Ejecución cuando cambia el insumo analítico

Si `data/processed/dashboard_dataset.csv` no existe o se modificó `data/processed/indice_localidad_disposicion_inadecuada.csv`, ejecute preparación y dashboard, en ese orden:

```bash
python scripts/execute_dashboard_notebooks.py \
  notebooks/00_preparacion_y_validacion.ipynb \
  notebooks/07_dashboard_integrado_exportacion.ipynb
```

El notebook `00` realiza la integración mínima y valida 19 localidades; no reconstruye los archivos raw ni el procesamiento analítico original.

Los notebooks `01` a `06` contienen componentes, análisis y comprobaciones independientes. El notebook `07` **no los carga ni depende de sus variables**, por lo que no es necesario ejecutarlos para abrir o regenerar el dashboard. Si se desea verificarlos todos, puede usarse:

```bash
python scripts/execute_dashboard_notebooks.py \
  notebooks/00_preparacion_y_validacion.ipynb \
  notebooks/01_kpis.ipynb \
  notebooks/02_relacion_scatter.ipynb \
  notebooks/03_heatmap_correlaciones.ipynb \
  notebooks/04_mapas_territoriales.ipynb \
  notebooks/05_ranking_localidades.ipynb \
  notebooks/06_hallazgos.ipynb \
  notebooks/07_dashboard_integrado_exportacion.ipynb
```

### 4. Salidas generadas

| Archivo | Notebook que lo genera | Descripción |
|---|---|---|
| `data/processed/dashboard_dataset.csv` | `00` | Dataset analítico común: una fila por cada una de las 19 localidades. Solo se regenera cuando es necesario. |
| `data/processed/dashboard_crime_detail.csv` | `07` | Desglose interactivo de ocho tipos de delito para cada localidad: 152 filas. |
| `data/processed/dashboard_reporting_summary.csv` | `07` | Resumen de denuncia utilizado en el panel de percepción: 19 filas. |
| `outputs/dashboard_bogota.html` | `07` | Dashboard final, interactivo y autocontenido, con cinco vistas, diez visualizaciones y selecciones enlazadas. |

La ejecución mínima del notebook `07` reconstruye exactamente estos tres archivos:

```text
outputs/dashboard_bogota.html
data/processed/dashboard_crime_detail.csv
data/processed/dashboard_reporting_summary.csv
```

El notebook `07` valida que el HTML incluya Plotly sin depender de una CDN, que contenga los cinco paneles y que estén incorporados los eventos de selección. El tamaño del HTML puede variar entre versiones, pero no debe ser cero.

Las imágenes de `outputs/capturas/` son material de documentación y **no** se regeneran al ejecutar el notebook. La versión actual tampoco exporta automáticamente PDF ni PNG del dashboard: el entregable reproducible es el HTML interactivo.

### 5. Verificar las salidas

Después de la ejecución, compruebe que los archivos existan y no estén vacíos:

```bash
python -c "from pathlib import Path; paths=[Path('outputs/dashboard_bogota.html'),Path('data/processed/dashboard_crime_detail.csv'),Path('data/processed/dashboard_reporting_summary.csv')]; assert all(p.is_file() and p.stat().st_size>0 for p in paths); print('Salidas verificadas correctamente')"
```

También puede revisar sus tamaños:

```bash
ls -lh outputs/dashboard_bogota.html \
  data/processed/dashboard_crime_detail.csv \
  data/processed/dashboard_reporting_summary.csv
```

Por último, abra `outputs/dashboard_bogota.html` en el navegador y compruebe la navegación entre los cuatro temas, los valores emergentes y la selección de localidades.

## Estructura del repositorio

```text
datajam-udata/
├── data/
│   ├── raw/                         # Fuentes originales y geometrías
│   │   └── dai_shp/                 # Límites de localidades
│   └── processed/                   # Dataset analítico y tablas auxiliares
├── docs/                            # Documentación metodológica
├── notebooks/
│   ├── procesar_botaderos_basura.ipynb
│   ├── reconstruccion_disposicion_inadecuada.ipynb
│   ├── 00_preparacion_y_validacion.ipynb
│   ├── 01_kpis.ipynb
│   ├── 02_relacion_scatter.ipynb
│   ├── 03_heatmap_correlaciones.ipynb
│   ├── 04_mapas_territoriales.ipynb
│   ├── 05_ranking_localidades.ipynb
│   ├── 06_hallazgos.ipynb
│   └── 07_dashboard_integrado_exportacion.ipynb
├── outputs/
│   ├── dashboard_bogota.html        # Producto interactivo final
│   └── capturas/                    # Imágenes documentales; no las genera el notebook 07
├── rules/                           # Especificaciones del proyecto
├── scripts/
│   ├── build_dashboard_notebooks.py
│   └── execute_dashboard_notebooks.py
├── src/
│   ├── dashboard_utils.py           # Carga, validación y componentes comunes
│   └── multipanel_dashboard.py      # Paneles, navegación y eventos interactivos
├── README.md
└── requirements.txt
```

## Reproducibilidad y alcance

- Los cálculos se obtienen de los datos incluidos en el repositorio; las estadísticas no están codificadas manualmente.
- Las rutas se resuelven respecto a la raíz del proyecto mediante `pathlib`.
- El producto cubre las 19 localidades con información completa en todas las fuentes utilizadas.
- El análisis es ecológico y exploratorio a escala de localidad. Sus resultados no deben trasladarse automáticamente a hogares, personas o barrios ni interpretarse como evidencia causal.

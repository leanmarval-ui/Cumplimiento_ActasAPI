import streamlit as st
import pandas as pd
from logica import procesar_todo, limpiar_texto
from parametros import get_festivos, ARCHIVOS, SHEET_NAMES
import calendar
import requests
import urllib3
import plotly.graph_objects as go

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Cumplimiento Actas", layout="wide")

# =========================
# SUCURSAL DESDE URL
# =========================
query_params = st.query_params
sucursal = query_params.get("sucursal", "barranquilla").lower()

st.title(f"📊 Dashboard Cumplimiento Actas - {sucursal.capitalize()}")
st.info(f"📍 Sucursal seleccionada: {sucursal.upper()}")

# =========================
# ARCHIVOS
# =========================
archivo    = ARCHIVOS.get(sucursal)
sheet_name = SHEET_NAMES.get(sucursal)

if archivo is None:
    st.error("❌ Sucursal no válida")
    st.stop()

# =========================
# CONFIG API
# =========================
cookie = st.secrets["API_COOKIE"]

CONFIG_API = {
    "barranquilla": {"cookie": cookie, "id": 3},
    "bogota":       {"cookie": cookie, "id": 2},
    "bucaramanga":  {"cookie": cookie, "id": 1},
    "cali":         {"cookie": cookie, "id": 4},
    "cartagena":    {"cookie": cookie, "id": 5},
}
config = CONFIG_API.get(sucursal)

# =========================
# CARGAR PROYECTOS
# =========================
@st.cache_data
def cargar_proyectos(archivo, sheet_name):
    df = pd.read_excel(archivo, sheet_name=sheet_name)
    df["Proyecto"] = df["Proyecto"].apply(limpiar_texto)
    return df

df_proyectos = cargar_proyectos(archivo, sheet_name)

# =========================
# TRAER API
# =========================
@st.cache_data
def traer_datos_api(cookie, id_sucursal):
    url = "https://analytics.app.marval.com.co/api/planificacion/gethistoricoreunionestotal"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://analytics.app.marval.com.co",
        "Referer": "https://analytics.app.marval.com.co/portal"
    }

    cookies = {"connect.sid": cookie}
    payload = {"idSucursal": id_sucursal}

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            json=payload,
            verify=False,
            timeout=15
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        st.error("⏱️ La API tardó demasiado. Intenta de nuevo.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            st.error("🔐 La sesión expiró. Actualiza la cookie en CONFIG_API.")
        else:
            st.error(f"❌ Error en la API: {e}")
        st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ No se pudo conectar a la API: {e}")
        st.stop()

    data = response.json()
    if isinstance(data, dict):
        data = data.get("data", data)

    df_api = pd.DataFrame(data)
    df_api["fechaInicio"] = pd.to_datetime(df_api["fechaInicio"], errors="coerce")
    df_api["fechaFin"]    = pd.to_datetime(df_api["fechaFin"],    errors="coerce")
    df_api = df_api[df_api["estadoReunion"] == "CERRADA"]

    df_intermedia = df_api[df_api["idTipoReunion"] == 1].copy()
    df_semanal    = df_api[df_api["idTipoReunion"] == 2].copy()

    df_intermedia["Proyecto"] = df_intermedia["descProyecto"].apply(limpiar_texto)
    df_semanal["Proyecto"]    = df_semanal["descProyecto"].apply(limpiar_texto)

    return df_intermedia, df_semanal

df_intermedia, df_semanal = traer_datos_api(config["cookie"], config["id"])

# =========================
# PARAMETROS SIDEBAR
# =========================
ANIO = st.sidebar.number_input("Año", value=2026, step=1)
MES  = st.sidebar.number_input("Mes", value=3, min_value=1, max_value=12)

# ✅ Botón para limpiar caché manualmente
if st.sidebar.button("🔄 Actualizar datos API"):
    st.cache_data.clear()
    st.rerun()

fechas_mes = pd.date_range(
    start=f"{ANIO}-{MES:02d}-01",
    end=f"{ANIO}-{MES:02d}-{calendar.monthrange(ANIO, MES)[1]}"
)

festivos = get_festivos(int(ANIO))

# =========================
# PROCESO
# =========================
df_detallado, df_resumen = procesar_todo(
    df_proyectos,
    df_intermedia,
    df_semanal,
    fechas_mes,
    anio=int(ANIO),
    mes=int(MES),
    festivos=festivos
)

# =========================
# FILTRO PROYECTO
# =========================
proyectos = ["Todos"] + sorted(df_detallado["Proyecto"].dropna().unique().tolist())
seleccion = st.selectbox("🔎 Filtrar proyecto", proyectos)

if seleccion != "Todos":
    df_view = df_detallado[df_detallado["Proyecto"] == seleccion].copy()
else:
    df_view = df_detallado.copy()

# =========================
# PORCENTAJES
# =========================
df_view["CumplimientoIntermediaPct"] = (df_view["CumplimientoIntermedia"] * 100).round(1)
df_view["CumplimientoSemanalPct"]    = (df_view["CumplimientoSemanal"]    * 100).round(1)

# =========================
# KPIs
# =========================
col1, col2, col3, col4 = st.columns(4)

promedio = (df_view["CumplimientoIntermediaPct"].mean() +
            df_view["CumplimientoSemanalPct"].mean()) / 2

col1.metric("📊 Promedio", f"{promedio:.1f}%")

col2.metric("🟢 Óptimo ≥90%",
    len(df_view[df_view["CumplimientoIntermediaPct"] >= 90]) +
    len(df_view[df_view["CumplimientoSemanalPct"]    >= 90]))

col3.metric("🟡 Medio 80–89%",
    len(df_view[(df_view["CumplimientoIntermediaPct"] >= 80) & (df_view["CumplimientoIntermediaPct"] < 90)]) +
    len(df_view[(df_view["CumplimientoSemanalPct"]    >= 80) & (df_view["CumplimientoSemanalPct"]    < 90)]))

col4.metric("🔴 Crítico <80%",
    len(df_view[df_view["CumplimientoIntermediaPct"] < 80]) +
    len(df_view[df_view["CumplimientoSemanalPct"]    < 80]))

# =========================
# TABLA
# =========================
tabla = []
for _, row in df_view.iterrows():
    tabla.append({
        "Proyecto":       row["Proyecto"],
        "Tipo":           "Intermedia",
        "Día":            row["DiaIntermedia"],
        "Posible":        row["PosibleIntermedia"],
        "Real":           row.get("RealIntermedia", ""),
        "Coincidencias":  row.get("CoincidenciasIntermedia", ""),
        "Conteo":         row.get("ConteoCoincidenciasIntermedia", 0),
        "Cumplimiento %": row["CumplimientoIntermediaPct"]
    })
    tabla.append({
        "Proyecto":       row["Proyecto"],
        "Tipo":           "Semanal",
        "Día":            row["DiaSemanal"],
        "Posible":        row["PosibleSemanal"],
        "Real":           row.get("RealSemanal", ""),
        "Coincidencias":  row.get("CoincidenciasSemanal", ""),
        "Conteo":         row.get("ConteoCoincidenciasSemanal", 0),
        "Cumplimiento %": row["CumplimientoSemanalPct"]
    })

df_tabla = pd.DataFrame(tabla)
st.dataframe(df_tabla, use_container_width=True)

# =========================
# GRAFICA
# =========================
st.subheader("📊 Cumplimiento por Proyecto (Intermedia vs Semanal)")

df_grafico = df_view[["Proyecto", "CumplimientoIntermediaPct", "CumplimientoSemanalPct"]].copy()

df_grafico["Promedio"] = (
    df_grafico["CumplimientoIntermediaPct"] +
    df_grafico["CumplimientoSemanalPct"]
) / 2

df_grafico = df_grafico.sort_values("Promedio")

def color(v):
    if v >= 90:   return "#27ae60"
    elif v >= 80: return "#f1c40f"
    else:         return "#c0392b"

fig = go.Figure()

fig.add_trace(go.Bar(
    y=df_grafico["Proyecto"],
    x=df_grafico["CumplimientoSemanalPct"],
    orientation="h",
    marker_color=[color(v) for v in df_grafico["CumplimientoSemanalPct"]],
    text=[f"Semanal  {v:.0f}%" for v in df_grafico["CumplimientoSemanalPct"]],
    textposition="inside",
    textfont=dict(color="white", size=16),
    insidetextanchor="start",
    name="Semanal",
    showlegend=False  # ✅ elimina el cuadro de color
))

fig.add_trace(go.Bar(
    y=df_grafico["Proyecto"],
    x=df_grafico["CumplimientoIntermediaPct"],
    orientation="h",
    marker_color=[color(v) for v in df_grafico["CumplimientoIntermediaPct"]],
    text=[f"Intermedia  {v:.0f}%" for v in df_grafico["CumplimientoIntermediaPct"]],
    textposition="inside",
    textfont=dict(color="white", size=16),
    insidetextanchor="start",
    name="Intermedia",
    showlegend=False  # ✅ elimina el cuadro de color
))
fig.add_vline(x=80, line_width=2, line_dash="dash", line_color="black")

fig.update_layout(
    barmode="group",
    yaxis=dict(autorange="reversed"),
    xaxis=dict(title="Cumplimiento (%)", range=[0, 120]),
    template="plotly_white",
    height=max(600, len(df_grafico) * 80),
    showlegend=True
)

st.plotly_chart(fig, use_container_width=True)
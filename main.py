import pandas as pd
import os
import calendar
import requests
import urllib3

from parametros import *
from logica import *
from grafica import generar_grafico

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("🔥 EJECUTANDO MAIN CON API 🔥")

# =========================
# 1. CONSUMIR API
# =========================
url = "https://analytics.app.marval.com.co/api/planificacion/gethistoricoreunionestotal"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://analytics.app.marval.com.co",
    "Referer": "https://analytics.app.marval.com.co/portal"
}

cookies = {
    "connect.sid": "s:qeKhCNUtAD383evo8WQxLvvF1NcWvUwe.XxnvOE%2BPK+STntrtWLWVU9b7rzGlyGEHL4Ju6xFUxVw"
}

payload = {"idSucursal": 3}

response = requests.post(
    url,
    headers=headers,
    cookies=cookies,
    json=payload,
    verify=False
)

print("STATUS:", response.status_code)

data = response.json()

# normalizar respuesta API
if isinstance(data, dict):
    data = data.get("data", data)

df_api = pd.DataFrame(data)

print("📊 API shape:", df_api.shape)

# =========================
# 2. LIMPIEZA BASE API
# =========================
df_api["fechaInicio"] = pd.to_datetime(df_api["fechaInicio"], errors="coerce")
df_api["fechaFin"] = pd.to_datetime(df_api["fechaFin"], errors="coerce")

df_api = df_api[df_api["estadoReunion"] == "CERRADA"]

# =========================
# 3. SPLIT INTERMEDIA / SEMANAL
# =========================
df_intermedia = df_api[df_api["idTipoReunion"] == 1].copy()
df_semanal = df_api[df_api["idTipoReunion"] == 2].copy()

# =========================
# 4. LEER PROYECTOS (EXCEL)
# =========================
df_proyectos = pd.read_excel(archivo, sheet_name="ProyectosBquilla")

# =========================
# 5. LIMPIEZA
# =========================
df_proyectos["Proyecto"] = df_proyectos["Proyecto"].apply(limpiar_texto)
df_intermedia["Proyecto"] = df_intermedia["descProyecto"].apply(limpiar_texto)
df_semanal["Proyecto"] = df_semanal["descProyecto"].apply(limpiar_texto)

# =========================
# 6. CALENDARIO MES
# =========================
fechas_mes = pd.date_range(
    start=f"{ANIO}-{MES:02d}-01",
    end=f"{ANIO}-{MES:02d}-{calendar.monthrange(ANIO, MES)[1]}"
)

print("📅 Calculando calendario...")

# =========================
# 7. PROCESO PRINCIPAL (GITHUB LOGIC)
# =========================
comparacion, df_detallado = procesar_todo(
    df_proyectos,
    df_intermedia,
    df_semanal,
    fechas_mes
)

# =========================
# 8. OUTPUT
# =========================
os.makedirs("output", exist_ok=True)

df_detallado.to_excel("output/calendario_comparado.xlsx", index=False)
comparacion.to_excel("output/resumen.xlsx", index=False)

# opcionales
comparacion[["Proyecto", "PosibleIntermedia", "PosibleSemanal"]].to_excel(
    "output/calendario_teorico.xlsx", index=False
)

comparacion[["Proyecto", "RealIntermedia", "RealSemanal"]].to_excel(
    "output/calendario_real.xlsx", index=False
)

# =========================
# 9. GRAFICO
# =========================
generar_grafico(comparacion)

print("✅ PROCESO FINALIZADO CORRECTAMENTE")
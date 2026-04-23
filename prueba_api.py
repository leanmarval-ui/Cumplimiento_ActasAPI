import requests
import pandas as pd
import numpy as np
import urllib3
from datetime import timedelta
from parametros import festivos, mapa_dias, ANIO, MES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================
# API
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
    "connect.sid": "s:6CbxZigh4NaGOuhN4SbOWlAzpLhl5fbf.NS5Si1DEWIwV+AoFfV9BOCw9NQOOPa99UJK0LhPvwcg"
}

response = requests.post(url, headers=headers, cookies=cookies, json={"idSucursal": 3}, verify=False)

data = response.json()
if isinstance(data, dict):
    data = data.get("data", data)

df = pd.DataFrame(data)

# =========================
# FECHAS
# =========================

df["fechaInicio"] = pd.to_datetime(df["fechaInicio"], errors="coerce")
df["fechaFin"] = pd.to_datetime(df["fechaFin"], errors="coerce")

df = df[df["estadoReunion"] == "CERRADA"]

df = df[
    (df["fechaInicio"].dt.year == ANIO) &
    (df["fechaInicio"].dt.month == MES)
]

df["Proyecto"] = df["descProyecto"].astype(str).str.strip().str.upper()

# =========================
# BASE EXCEL
# =========================

df_base = pd.read_excel("input/Reuniones.xlsx", sheet_name="ProyectosBquilla")
df_base["Proyecto"] = df_base["Proyecto"].astype(str).str.strip().str.upper()

# =========================
# FUNCIONES GITHUB (REPLICADAS)
# =========================

def es_habil(fecha):
    if fecha.weekday() == 6:
        return False
    if fecha in festivos:
        return False
    return True

def siguiente_habil(fecha):
    siguiente = fecha + timedelta(days=1)
    while not es_habil(siguiente):
        siguiente += timedelta(days=1)
    return siguiente

def calcular_posibles(dia_base, fechas_mes):
    if pd.isna(dia_base):
        return ""

    dia_base = str(dia_base).upper().strip()
    if dia_base not in mapa_dias:
        return ""

    numero_dia = mapa_dias[dia_base]
    posibles = []

    for fecha in fechas_mes:
        fecha = pd.to_datetime(fecha).normalize()

        # 🔥 día programado
        if fecha.weekday() == numero_dia:

            # 👉 ejecución real = siguiente día hábil (gabela +1)
            siguiente = siguiente_habil(fecha)

            # asegurar que no sea festivo ni domingo
            if siguiente.month == MES:
                posibles.append(siguiente)

    # eliminar duplicados
    posibles = sorted(set(posibles))

    return ", ".join([f.strftime("%Y-%m-%d") for f in posibles])

# =========================
# CALENDARIO TEÓRICO
# =========================

fechas_mes = pd.date_range(
    start=f"{ANIO}-{MES:02d}-01",
    end=f"{ANIO}-{MES:02d}-28"
)

df_base["PosibleIntermedia"] = df_base["DiaIntermedia"].apply(
    lambda x: calcular_posibles(x, fechas_mes)
)

df_base["PosibleSemanal"] = df_base["DiaSemanal"].apply(
    lambda x: calcular_posibles(x, fechas_mes)
)

# =========================
# REALES
# =========================

df_intermedia = df[df["idTipoReunion"] == 1]
df_semanal = df[df["idTipoReunion"] == 2]

df_intermedia_group = df_intermedia.groupby("Proyecto")["fechaInicio"].apply(
    lambda x: ", ".join(sorted(x.dt.strftime("%Y-%m-%d")))
).reset_index().rename(columns={"fechaInicio": "RealIntermedia"})

df_semanal_group = df_semanal.groupby("Proyecto")["fechaInicio"].apply(
    lambda x: ", ".join(sorted(x.dt.strftime("%Y-%m-%d")))
).reset_index().rename(columns={"fechaInicio": "RealSemanal"})

# =========================
# MERGE FINAL
# =========================

df_final = df_base.merge(df_intermedia_group, on="Proyecto", how="left")
df_final = df_final.merge(df_semanal_group, on="Proyecto", how="left")

df_final["RealIntermedia"] = df_final["RealIntermedia"].fillna("")
df_final["RealSemanal"] = df_final["RealSemanal"].fillna("")

# =========================
# CONTEOS
# =========================

def contar(valor):
    if valor == "":
        return 0
    return len(valor.split(","))

df_final["ConteoIntermedia"] = df_final["RealIntermedia"].apply(contar)
df_final["ConteoSemanal"] = df_final["RealSemanal"].apply(contar)

# =========================
# COINCIDENCIAS (SIMPLE BASE)
# =========================

def es_coincidencia(real, posibles):
    if pd.isna(real) or pd.isna(posibles):
        return ""

    reales = set(
        pd.to_datetime(x.strip()).normalize()
        for x in str(real).split(",") if x.strip()
    )

    teoricas = set(
        pd.to_datetime(x.strip()).normalize()
        for x in str(posibles).split(",") if x.strip()
    )

    # 🔥 CLAVE: excluir festivos SOLO en comparación
    reales_validos = {r for r in reales if r not in festivos}

    coincidencias = reales_validos.intersection(teoricas)

    return ", ".join(sorted([f.strftime("%Y-%m-%d") for f in coincidencias]))

df_final["CoincidenciasIntermedia"] = df_final.apply(
    lambda row: es_coincidencia(row["RealIntermedia"], row["PosibleIntermedia"]),
    axis=1
)

df_final["CoincidenciasSemanal"] = df_final.apply(
    lambda row: es_coincidencia(row["RealSemanal"], row["PosibleSemanal"]),
    axis=1
)

# =========================
# CUMPLIMIENTO
# =========================

df_final["CumplimientoIntermedia"] = np.where(
    df_final["ConteoIntermedia"] == 0,
    0,
    df_final["ConteoCoincidenciasIntermedia"] / df_final["ConteoIntermedia"]
)

df_final["CumplimientoSemanal"] = np.where(
    df_final["ConteoSemanal"] == 0,
    0,
    df_final["ConteoCoincidenciasSemanal"] / df_final["ConteoSemanal"]
)

df_final["CumplimientoIntermedia"] = df_final["CumplimientoIntermedia"].clip(upper=1)
df_final["CumplimientoSemanal"] = df_final["CumplimientoSemanal"].clip(upper=1)

# =========================
# EXPORT
# =========================

df_final.to_excel("output/calendario_comparado.xlsx", index=False)

print("✅ archivo generado: calendario_comparado.xlsx")
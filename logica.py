import pandas as pd
import numpy as np
from datetime import timedelta
from parametros import mapa_dias

# =========================
# LIMPIEZA
# =========================
def limpiar_texto(texto):
    if pd.isna(texto):
        return texto
    return str(texto).strip().upper()

# =========================
# FUNCIONES BASE
# =========================
def es_habil(fecha, festivos):
    fecha = pd.to_datetime(fecha).normalize()
    if fecha.weekday() == 6:
        return False
    if fecha in festivos:
        return False
    return True

def siguiente_habil(fecha, festivos):
    siguiente = pd.to_datetime(fecha).normalize() + timedelta(days=1)
    while not es_habil(siguiente, festivos):
        siguiente += timedelta(days=1)
    return siguiente

# =========================
# FIX FECHAS (conserva hora para comparar correctamente)
# =========================
def convertir_fecha_correcta(col):
    return (
        pd.to_datetime(col, errors="coerce", utc=True)
        .dt.tz_convert("America/Bogota")
        .dt.tz_localize(None)
        # ✅ SIN .dt.normalize() — conserva la hora
    )

# =========================
# CALCULO POSIBLES
# =========================
def calcular_posibles(dia_base, fechas_mes, festivos, mes):
    if pd.isna(dia_base):
        return ""
    dia_base = str(dia_base).upper().strip()
    if dia_base not in mapa_dias:
        return ""

    numero_dia = mapa_dias[dia_base]
    posibles = []

    for fecha in fechas_mes:
        fecha = pd.to_datetime(fecha).normalize()
        if fecha.weekday() == numero_dia:
            if fecha in festivos:
                siguiente = siguiente_habil(fecha, festivos)
                if siguiente.month == mes:
                    posibles.append(siguiente)
                    # ✅ agrega también la holgura del día rodado
                    siguiente_2 = siguiente_habil(siguiente, festivos)
                    if siguiente_2.month == mes:
                        posibles.append(siguiente_2)
            else:
                posibles.append(fecha)
                siguiente = siguiente_habil(fecha, festivos)
                if siguiente.month == mes:
                    posibles.append(siguiente)

    posibles = sorted(set(posibles))
    return ", ".join([f.strftime("%Y-%m-%d") for f in posibles])

# =========================
# CONTEO POR SEMANA
# =========================
def contar_eventos_teoricos(valor):
    if pd.isna(valor) or valor == "":
        return 0
    fechas = sorted(set(
        pd.to_datetime(x.strip()).normalize()
        for x in str(valor).split(",") if x.strip()
    ))
    semanas = set()
    for f in fechas:
        semanas.add((f.isocalendar().year, f.isocalendar().week))
    return len(semanas)

# =========================
# CONTEO SIMPLE
# =========================
def contar_fechas(valor):
    if pd.isna(valor) or valor == "":
        return 0
    return len([x for x in str(valor).split(",") if x.strip() != ""])

# =========================
# COINCIDENCIAS (con hora)
# =========================
def coincidencias_por_semana(lista_teorica, lista_real_str, reales_con_hora):
    if pd.isna(lista_teorica) or pd.isna(lista_real_str):
        return ""

    teoricas = sorted(set(
        pd.to_datetime(x.strip()).normalize()
        for x in str(lista_teorica).split(",") if x.strip()
    ))

    coincidencias = []
    for i in range(0, len(teoricas), 2):
        inicio = teoricas[i]

        try:
            fin = teoricas[i + 1]
        except IndexError:
            fin = inicio

        # ✅ Ventana: desde inicio 00:00 hasta fin 23:59:59
        ventana_inicio = inicio
        ventana_fin    = fin + timedelta(hours=23, minutes=59, seconds=59)

        match = None
        for r in reales_con_hora:
            r_norm = pd.to_datetime(r)
            if r_norm.weekday() == 6:
                continue
            if ventana_inicio <= r_norm <= ventana_fin:
                match = r_norm.normalize()
                break

        if match is not None:
            coincidencias.append(match)

    return ", ".join([f.strftime("%Y-%m-%d") for f in coincidencias])

# =========================
# PROCESO PRINCIPAL
# =========================
def procesar_todo(df_proyectos, df_intermedia, df_semanal, fechas_mes, anio, mes, festivos):

    df_proyectos  = df_proyectos.copy()
    df_intermedia = df_intermedia.copy()
    df_semanal    = df_semanal.copy()

    df_proyectos["Proyecto"]  = df_proyectos["Proyecto"].apply(limpiar_texto)
    df_intermedia["Proyecto"] = df_intermedia["Proyecto"].apply(limpiar_texto)
    df_semanal["Proyecto"]    = df_semanal["Proyecto"].apply(limpiar_texto)

    # POSIBLES
    df_proyectos["PosibleIntermedia"] = df_proyectos["DiaIntermedia"].apply(
        lambda x: calcular_posibles(x, fechas_mes, festivos, mes)
    )
    df_proyectos["PosibleSemanal"] = df_proyectos["DiaSemanal"].apply(
        lambda x: calcular_posibles(x, fechas_mes, festivos, mes)
    )

    # CONTEO
    df_proyectos["ConteoIntermedia"] = df_proyectos["PosibleIntermedia"].apply(contar_eventos_teoricos)
    df_proyectos["ConteoSemanal"]    = df_proyectos["PosibleSemanal"].apply(contar_eventos_teoricos)

    # FECHAS REALES — conserva hora
    col_fecha_intermedia = "fechaFin"
    col_fecha_semanal    = "fechaFin"

    df_intermedia[col_fecha_intermedia] = convertir_fecha_correcta(df_intermedia[col_fecha_intermedia])
    df_semanal[col_fecha_semanal]       = convertir_fecha_correcta(df_semanal[col_fecha_semanal])

    df_intermedia = df_intermedia[
        (df_intermedia[col_fecha_intermedia].dt.year  == anio) &
        (df_intermedia[col_fecha_intermedia].dt.month == mes)
    ]
    df_semanal = df_semanal[
        (df_semanal[col_fecha_semanal].dt.year  == anio) &
        (df_semanal[col_fecha_semanal].dt.month == mes)
    ]

    df_intermedia = df_intermedia.drop_duplicates(subset=["Proyecto", col_fecha_intermedia])
    df_semanal    = df_semanal.drop_duplicates(subset=["Proyecto", col_fecha_semanal])

    # AGRUPAR fechas para mostrar en tabla (solo fecha, sin hora)
    df_intermedia_group = df_intermedia.groupby("Proyecto")[col_fecha_intermedia].apply(
        lambda x: ", ".join(sorted(set(x.dt.normalize().dt.strftime("%Y-%m-%d"))))
    ).reset_index()
    df_semanal_group = df_semanal.groupby("Proyecto")[col_fecha_semanal].apply(
        lambda x: ", ".join(sorted(set(x.dt.normalize().dt.strftime("%Y-%m-%d"))))
    ).reset_index()

    df_intermedia_group.rename(columns={col_fecha_intermedia: "RealIntermedia"}, inplace=True)
    df_semanal_group.rename(columns={col_fecha_semanal:       "RealSemanal"},    inplace=True)

    # AGRUPAR fechas CON hora para comparar coincidencias
    df_intermedia_hora = df_intermedia.groupby("Proyecto")[col_fecha_intermedia].apply(list).reset_index()
    df_semanal_hora    = df_semanal.groupby("Proyecto")[col_fecha_semanal].apply(list).reset_index()

    df_intermedia_hora.rename(columns={col_fecha_intermedia: "RealIntermedaHora"}, inplace=True)
    df_semanal_hora.rename(columns={col_fecha_semanal:       "RealSemanalHora"},   inplace=True)

    # MERGE
    df_detallado = df_proyectos.merge(df_intermedia_group, on="Proyecto", how="left")
    df_detallado = df_detallado.merge(df_semanal_group,    on="Proyecto", how="left")
    df_detallado = df_detallado.merge(df_intermedia_hora,  on="Proyecto", how="left")
    df_detallado = df_detallado.merge(df_semanal_hora,     on="Proyecto", how="left")

    # COINCIDENCIAS con hora
    df_detallado["CoincidenciasIntermedia"] = df_detallado.apply(
        lambda row: coincidencias_por_semana(
            row["PosibleIntermedia"],
            row["RealIntermedia"],
            row["RealIntermedaHora"] if isinstance(row["RealIntermedaHora"], list) else []
        ), axis=1
    )
    df_detallado["CoincidenciasSemanal"] = df_detallado.apply(
        lambda row: coincidencias_por_semana(
            row["PosibleSemanal"],
            row["RealSemanal"],
            row["RealSemanalHora"] if isinstance(row["RealSemanalHora"], list) else []
        ), axis=1
    )

    df_detallado["ConteoCoincidenciasIntermedia"] = df_detallado["CoincidenciasIntermedia"].apply(contar_fechas)
    df_detallado["ConteoCoincidenciasSemanal"]    = df_detallado["CoincidenciasSemanal"].apply(contar_fechas)

    # CUMPLIMIENTO
    df_detallado["CumplimientoIntermedia"] = np.where(
        df_detallado["ConteoIntermedia"] == 0, 0,
        df_detallado["ConteoCoincidenciasIntermedia"] / df_detallado["ConteoIntermedia"]
    )
    df_detallado["CumplimientoSemanal"] = np.where(
        df_detallado["ConteoSemanal"] == 0, 0,
        df_detallado["ConteoCoincidenciasSemanal"] / df_detallado["ConteoSemanal"]
    )

    df_detallado["CumplimientoIntermedia"] = df_detallado["CumplimientoIntermedia"].clip(upper=1)
    df_detallado["CumplimientoSemanal"]    = df_detallado["CumplimientoSemanal"].clip(upper=1)

    # RESUMEN
    df_resumen = df_detallado[[
        "Proyecto", "CumplimientoIntermedia", "CumplimientoSemanal"
    ]].copy()

    return df_detallado, df_resumen
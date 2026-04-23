import pandas as pd

# =========================
# ARCHIVOS POR SUCURSAL
# =========================
ARCHIVOS = {
    "barranquilla": "input/Reuniones_Bquilla.xlsx",
    "bogota":       "input/Reuniones_Bogota.xlsx",
    "bucaramanga":  "input/Reuniones_Bucaramanga.xlsx",
    "cali":         "input/Reuniones_Cali.xlsx",
    "cartagena":    "input/Reuniones_Ctga.xlsx",
}

SHEET_NAMES = {
    "barranquilla": "ProyectosBquilla",
    "bogota":       "ProyectosBogota",
    "bucaramanga":  "ProyectosBGA",
    "cali":         "ProyectosCali",
    "cartagena":    "ProyectosCtga",
}

SALIDAS = {
    "teorico":   "output/calendario_teorico.xlsx",
    "real":      "output/calendario_real.xlsx",
    "comparado": "output/calendario_comparado.xlsx",
}

# =========================
# FESTIVOS POR AÑO (Colombia)
# =========================
FESTIVOS_POR_ANIO = {
    2025: [
        "2025-01-01", "2025-01-06", "2025-03-24", "2025-04-17",
        "2025-04-18", "2025-05-01", "2025-06-02", "2025-06-23",
        "2025-06-30", "2025-07-20", "2025-08-07", "2025-08-18",
        "2025-10-13", "2025-11-03", "2025-11-17", "2025-12-08",
        "2025-12-25",
    ],
    2026: [
        "2026-01-01", "2026-01-12", "2026-03-23", "2026-03-30", "2026-03-31", "2026-04-02",
        "2026-04-03", "2026-05-01", "2026-05-18", "2026-06-08",
        "2026-06-29", "2026-07-20", "2026-08-07", "2026-08-17",
        "2026-10-12", "2026-11-02", "2026-11-16", "2026-12-08",
        "2026-12-25",
    ],
}

def get_festivos(anio):
    fechas = FESTIVOS_POR_ANIO.get(anio, [])
    return set(pd.to_datetime(f).normalize() for f in fechas)

# =========================
# MAPA DIAS
# =========================
mapa_dias = {
    "LUNES": 0, "MARTES": 1, "MIERCOLES": 2, "MIÉRCOLES": 2,
    "JUEVES": 3, "VIERNES": 4, "SABADO": 5, "SÁBADO": 5, "DOMINGO": 6
}
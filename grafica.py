import matplotlib.pyplot as plt
import numpy as np
import os

def generar_grafico(comparacion):

    print("Generando gráfico...")

    df_grafico = comparacion.copy()

    # =========================
    # FILTRO SOLO EJECUCIÓN
    # =========================
    if "Estado" in df_grafico.columns:
        df_grafico = df_grafico[
            df_grafico["Estado"].fillna("").str.upper() == "EJECUCIÓN"
        ]

    # =========================
    # PASAR A %
    # =========================
    df_grafico["CumplimientoSemanal"] *= 100
    df_grafico["CumplimientoIntermedia"] *= 100

    # PROMEDIO PARA ORDENAR
    df_grafico["Promedio"] = (
        df_grafico["CumplimientoSemanal"] +
        df_grafico["CumplimientoIntermedia"]
    ) / 2

    df_grafico = df_grafico.sort_values("Promedio")

    # =========================
    # COLORES
    # =========================
    def color(v):
        if v >= 90:
            return "#27ae60"
        elif v >= 80:
            return "#f1c40f"
        else:
            return "#c0392b"

    def color_texto(v):
        if v >= 90:
            return "#1e8449"
        elif v >= 80:
            return "#b7950b"
        else:
            return "#922b21"

    proyectos = df_grafico["Proyecto"]

    y = np.arange(len(proyectos))
    h = 0.32

    # =========================
    # FIGURA
    # =========================
    fig, ax = plt.subplots(figsize=(13, max(6, len(proyectos)*0.6)))

    # =========================
    # BARRAS (SIN LABEL)
    # =========================
    bars1 = ax.barh(
        y - h/2,
        df_grafico["CumplimientoSemanal"],
        h,
        color=[color(v) for v in df_grafico["CumplimientoSemanal"]],
        edgecolor="none",
        alpha=0.85
    )

    bars2 = ax.barh(
        y + h/2,
        df_grafico["CumplimientoIntermedia"],
        h,
        color=[color(v) for v in df_grafico["CumplimientoIntermedia"]],
        edgecolor="none",
        alpha=0.85
    )

    # =========================
    # TEXTO DENTRO
    # =========================
    for bar in bars1:
        ax.text(
            3,
            bar.get_y() + bar.get_height()/2,
            "Semanal",
            va="center",
            ha="left",
            fontsize=8,
            color="white",
            fontweight="bold"
        )

    for bar in bars2:
        ax.text(
            3,
            bar.get_y() + bar.get_height()/2,
            "Intermedia",
            va="center",
            ha="left",
            fontsize=8,
            color="white",
            fontweight="bold"
        )

    # =========================
    # PORCENTAJES AFUERA
    # =========================
    for i, bar in enumerate(bars1):
        width = bar.get_width()
        valor = df_grafico["CumplimientoSemanal"].iloc[i]

        ax.text(
            width + 2,
            bar.get_y() + bar.get_height()/2,
            f"{width:.0f}%",
            va="center",
            fontsize=9,
            color=color_texto(valor)
        )

    for i, bar in enumerate(bars2):
        width = bar.get_width()
        valor = df_grafico["CumplimientoIntermedia"].iloc[i]

        ax.text(
            width + 2,
            bar.get_y() + bar.get_height()/2,
            f"{width:.0f}%",
            va="center",
            fontsize=9,
            color=color_texto(valor)
        )

    # =========================
    # META (ÚNICA LEYENDA)
    # =========================
    ax.axvline(80, linestyle="--", linewidth=2, color="black", label="Meta 80%")
    ax.legend(["Meta 80%"])

    # =========================
    # EJES
    # =========================
    ax.set_yticks(y)
    ax.set_yticklabels(proyectos)

    max_val = max(
        df_grafico["CumplimientoSemanal"].max(),
        df_grafico["CumplimientoIntermedia"].max()
    )

    ax.set_xlim(0, max_val + 15)

    ax.set_xlabel("Cumplimiento (%)")
    ax.set_title("Cumplimiento de Reuniones por Proyecto", fontsize=14, fontweight="bold")

    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()

    # =========================
    # GUARDAR
    # =========================
    os.makedirs("output", exist_ok=True)
    plt.savefig("output/grafico.png", dpi=300)

    plt.close()

    print("Gráfico generado correctamente")
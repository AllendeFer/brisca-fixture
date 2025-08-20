#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App web (Streamlit) para generar el fixture de un campeonato de Brisca.
Se publica tal cual en Streamlit Cloud / Hugging Face Spaces.

Uso local:
    pip install streamlit
    streamlit run briscas.py

Características:
- Entrada principal: número de equipos (par o impar; si es impar, agrega DESCANSA).
- Opcionales: nombres personalizados, ida/vuelta, balance de local/visita.
- Salida: tabla en pantalla + descargas CSV/HTML (sin Excel), lista para simultáneas por ronda.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Dict
import csv
import io
import datetime as _dt
import streamlit as st

BYE_LABEL = "DESCANSA"

# ==========================
# Núcleo: generación fixture
# ==========================

def generar_fixture(
    n: int,
    names: Optional[List[str]] = None,
    double_round: bool = False,
    balance_home_away: bool = True,
    bye_label: str = BYE_LABEL,
) -> List[Tuple[int, int, str, str, str]]:
    """Genera fixture round-robin (método del círculo).

    Retorna lista de tuplas: (ronda, mesa, local, visita, nota)
    Si hay descanso: visita = "" y nota = "DESCANSA".
    """
    if n < 2:
        raise ValueError("Se requieren al menos 2 equipos.")

    if names is not None and len(names) != n:
        raise ValueError("Si usas nombres personalizados, deben ser exactamente n.")

    equipos = names[:] if names else [f"E{i}" for i in range(1, n + 1)]

    impar = (n % 2 == 1)
    if impar:
        equipos.append(bye_label)
        n += 1

    rondas = n - 1
    mitad = n // 2

    work = equipos[:]
    filas: List[Tuple[int, int, str, str, str]] = []

    # Ida
    for r in range(1, rondas + 1):
        pares = [(work[i], work[-(i + 1)]) for i in range(mitad)]
        mesa = 1
        for a, b in pares:
            if a == bye_label or b == bye_label:
                descansa = a if b == bye_label else b
                filas.append((r, mesa, descansa, "", "DESCANSA"))
            else:
                if balance_home_away and (r % 2 == 0):  # alterna por paridad de ronda
                    a, b = b, a
                filas.append((r, mesa, a, b, ""))
            mesa += 1
        # Rotación (fijo el primero)
        fijo = work[0]
        cola = work[1:]
        work = [fijo] + [cola[-1]] + cola[:-1]

    # Vuelta (opcional) invirtiendo local/visita y sumando a la ronda
    if double_round:
        vuelta: List[Tuple[int, int, str, str, str]] = []
        for (r, mesa, local, visita, nota) in filas:
            r2 = r + rondas
            if nota == "DESCANSA":
                vuelta.append((r2, mesa, local, "", "DESCANSA"))
            else:
                vuelta.append((r2, mesa, visita, local, ""))
        filas.extend(vuelta)

    # Orden estable por Ronda y Mesa
    filas.sort(key=lambda x: (x[0], x[1]))
    return filas


# ======================
# Utilidades de salida
# ======================

def filas_a_dicts(filas: List[Tuple[int, int, str, str, str]]):
    return [
        {"Ronda": r, "Mesa": m, "Local": a, "Visita": b, "Nota": nota}
        for (r, m, a, b, nota) in filas
    ]


def dicts_a_csv_bytes(rows) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Ronda", "Mesa", "Local", "Visita", "Nota"])
    for row in rows:
        w.writerow([row["Ronda"], row["Mesa"], row["Local"], row["Visita"], row["Nota"]])
    return buf.getvalue().encode("utf-8-sig")


def dicts_a_html(rows, n: int) -> str:
    # HTML con estilos y botón de imprimir (standalone)
    filas_html = []
    for row in rows:
        if row["Nota"] == "DESCANSA":
            filas_html.append(
                f"<tr><td>{row['Ronda']}</td><td>{row['Mesa']}</td><td>{row['Local']}</td><td></td><td><span class='pill pill-rest'>DESCANSA</span></td></tr>"
            )
        else:
            filas_html.append(
                f"<tr><td>{row['Ronda']}</td><td>{row['Mesa']}</td><td>{row['Local']}</td><td>{row['Visita']}</td><td></td></tr>"
            )

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""
<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Fixture Brisca ({n} equipos)</title>
<style>
  :root {{ --bg:#0b0c0f; --card:#151823; --text:#e8eaf1; --muted:#9aa4b2; --rest:#ffd166; }}
  html,body {{ background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial; margin:0; padding:0; }}
  .wrap {{ max-width: 1100px; margin: 32px auto; padding: 0 16px; }}
  h1 {{ font-size: 22px; font-weight: 650; margin: 0 0 12px; }}
  .meta {{ color: var(--muted); margin-bottom: 16px; }}
  .card {{ background: var(--card); border-radius: 12px; padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,.25); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  thead th {{ text-align: left; font-weight: 600; color: var(--muted); padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,.08); position: sticky; top:0; background: var(--card); }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,.06); }}
  tbody tr:hover {{ background: rgba(255,255,255,.03); }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; color: #000; }}
  .pill-rest {{ background: var(--rest); }}
  .footer {{ color: var(--muted); font-size: 12px; margin-top: 12px; }}
  .actions {{ display:flex; gap:10px; margin-bottom:12px; }}
  .btn {{ display:inline-block; border:1px solid rgba(255,255,255,.12); padding:8px 10px; border-radius:8px; text-decoration:none; color:var(--text); }}
  .btn:hover {{ background: rgba(255,255,255,.06); }}
</style>
</head>
<body>
<div class='wrap'>
  <h1>Fixture de Brisca</h1>
  <div class='meta'>Participantes: <strong>{n}</strong> — Round-robin (método del círculo). Generado {now}.</div>
  <div class='card'>
    <div class='actions'>
      <a class='btn' href='#' onclick='window.print()'>Imprimir / Guardar PDF</a>
    </div>
    <table>
      <thead>
        <tr><th>Ronda</th><th>Mesa</th><th>Local</th><th>Visita</th><th>Nota</th></tr>
      </thead>
      <tbody>
        {''.join(filas_html)}
      </tbody>
    </table>
  </div>
  <div class='footer'>Generado automáticamente — Todas las mesas por ronda se pueden jugar en simultáneo.</div>
</div>
</body>
</html>
"""
    return html


# =============
# Interfaz (UI)
# =============
st.set_page_config(page_title="Fixture Brisca", page_icon="🃏", layout="centered")
st.title("🃏 Fixture para Campeonato de Brisca")
st.caption("Round-robin • Método del círculo • Partidas simultáneas por ronda")

# Entradas
n = st.number_input(
    "Número de equipos",
    min_value=2,
    value=6,
    step=1,
    help="Si es impar, se agregará un DESCANSA automáticamente.",
)

with st.expander("Opciones avanzadas", expanded=False):
    double_round = st.checkbox("Ida y vuelta (doble round-robin)", value=False)
    balance = st.checkbox("Balancear local/visita por paridad de ronda", value=True)
    names_text = st.text_area(
        "Nombres personalizados (opcional, separados por coma — deben ser EXACTAMENTE N)",
        value="",
        placeholder="Ej.: Tigres, Leones, Águilas, Cóndores",
    )
    names: Optional[List[str]] = None
    if names_text.strip():
        names = [x.strip() for x in names_text.split(",") if x.strip()]

if st.button("Generar fixture"):
    try:
        filas = generar_fixture(int(n), names=names, double_round=bool(double_round), balance_home_away=bool(balance))
        rows = filas_a_dicts(filas)

        st.subheader("Tabla de Fixtures")
        st.dataframe(rows, use_container_width=True, hide_index=True)

        csv_bytes = dicts_a_csv_bytes(rows)
        html_str = dicts_a_html(rows, int(n))

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv_bytes,
                file_name=f"briscas_fixture_{int(n)}{'_ida_vuelta' if double_round else ''}.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                label="⬇️ Descargar HTML",
                data=html_str,
                file_name=f"briscas_fixture_{int(n)}{'_ida_vuelta' if double_round else ''}.html",
                mime="text/html",
            )

        # Info de rondas/partidos
        total_rondas = (int(n) - 1) if int(n) % 2 == 0 else int(n)
        if double_round:
            total_rondas *= 2
        st.info(f"Rondas totales: {total_rondas} • Partidos por ronda: {int(n)//2 if int(n)%2==0 else (int(n)+1)//2}")
        st.success("Fixture generado correctamente.")
    except Exception as e:
        st.error(f"Error: {e}")

with st.expander("¿Cómo publicar en Streamlit Cloud?", expanded=False):
    st.markdown(
        """
        1. Sube este archivo `briscas.py` a un repositorio en GitHub.
        2. Ve a **streamlit.io -> Community Cloud** y conecta tu GitHub.
        3. Selecciona el repo y el archivo principal `briscas.py`.
        4. Deploy. Obtendrás una URL pública (HTTPS) accesible desde celular y computador.
        
        **Tip:** Si quieres un dominio propio, usa CNAME/redirect hacia la URL pública de Streamlit.
        """
    )
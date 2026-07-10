# -*- coding: utf-8 -*-
"""
Generador del Tablero de Cumplimiento para Gerencia — Proyecto HostDime.

Lee el checklist (sección 18) del documento maestro de continuidad,
calcula el porcentaje de avance por fase y global, los días restantes
hasta la fecha límite, y genera un tablero HTML pensado para una
persona NO técnica (números grandes, semáforos, lenguaje simple).

Uso:
    python3 generar_dashboard.py

No requiere librerías externas. Solo Python 3.
"""

import re
import os
from datetime import date, datetime

# ------------------------------------------------------------------ #
# CONFIGURACIÓN
# ------------------------------------------------------------------ #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# El documento maestro está en la carpeta superior (03. Implementacion)
DOC_MAESTRO = os.path.join(os.path.dirname(BASE_DIR), "00_Documento_Maestro_Continuidad.md")
SALIDA_HTML = os.path.join(BASE_DIR, "index.html")

FECHA_LIMITE = date(2026, 7, 30)
PROYECTO = "Migración de Infraestructura HostDime"
CLIENTE = "COUNT GROUP SAS"

# Traducción de los títulos técnicos del checklist a lenguaje de gerencia.
# clave = texto del encabezado en el documento (sin los **).
FRIENDLY = {
    "Preparación": (
        "Preparación y accesos",
        "Dejar listas las herramientas y accesos para trabajar de forma segura",
    ),
    "Tenant 1 — Active Directory": (
        "Control central de usuarios y seguridad",
        "El sistema que decide quién entra y a qué tiene permiso",
    ),
    "Red y perímetro (FortiGate)": (
        "Red y seguridad perimetral",
        "La protección de la empresa y la conexión remota segura",
    ),
    "VMs Core restantes (validación por Royal TS)": (
        "Servidores principales",
        "Verificar que los servidores clave respondan correctamente",
    ),
    "VMs Core (preparación)": (
        "Servidores principales",
        "Dejar listos los servidores clave (administración, monitoreo, archivos)",
    ),
    "Servicios compartidos": (
        "Servicios para los usuarios",
        "Archivos compartidos y el programa contable (Helisa)",
    ),
    "Clientes (Tenant 1)": (
        "Migración de las empresas del grupo",
        "Pasar cada empresa a la nueva infraestructura",
    ),
    "Tenant 2 — PPC": (
        "Cliente PPC (entorno aislado)",
        "Montar el entorno separado y dedicado del cliente PPC",
    ),
    "Cierre": (
        "Copias de seguridad y puesta en marcha",
        "Respaldos de información y salida final a producción",
    ),
}


# ------------------------------------------------------------------ #
# LECTURA Y PARSEO DEL CHECKLIST
# ------------------------------------------------------------------ #
def leer_seccion_checklist(texto):
    """Extrae el bloque de la sección 18 (checklist)."""
    m = re.search(r"##\s*18\.\s*CHECKLIST.*?(?=\n##\s*19\.)", texto, re.S | re.I)
    if not m:
        raise ValueError("No se encontró la sección 18 (CHECKLIST) en el documento.")
    return m.group(0)


def parsear_fases(bloque):
    """
    Devuelve una lista de fases:
    [{clave, titulo, subtitulo, hechos, total}], y los totales globales.
    """
    fases = []
    actual = None

    for linea in bloque.splitlines():
        # Encabezado de grupo en negrita: **Preparación**
        hdr = re.match(r"^\s*\*\*(.+?)\*\*\s*$", linea)
        if hdr:
            clave = hdr.group(1).strip()
            titulo, subtitulo = FRIENDLY.get(clave, (clave, ""))
            actual = {
                "clave": clave,
                "titulo": titulo,
                "subtitulo": subtitulo,
                "hechos": 0,
                "total": 0,
            }
            fases.append(actual)
            continue

        # Contar casillas [x] y [ ] (puede haber varias por línea)
        if actual is not None:
            hechos = len(re.findall(r"\[[xX]\]", linea))
            pend = len(re.findall(r"\[ \]", linea))
            actual["hechos"] += hechos
            actual["total"] += hechos + pend

    # Quitar fases sin casillas (por si algún encabezado no tiene ítems)
    fases = [f for f in fases if f["total"] > 0]

    tot_hechos = sum(f["hechos"] for f in fases)
    tot_total = sum(f["total"] for f in fases)
    return fases, tot_hechos, tot_total


# ------------------------------------------------------------------ #
# UTILIDADES DE PRESENTACIÓN
# ------------------------------------------------------------------ #
def color_por_pct(pct):
    if pct >= 100:
        return "#16a34a"  # verde completado
    if pct >= 50:
        return "#2563eb"  # azul en buen avance
    if pct > 0:
        return "#f59e0b"  # ámbar iniciado
    return "#cbd5e1"      # gris sin iniciar


def estado_texto(pct):
    if pct >= 100:
        return "Completado"
    if pct > 0:
        return "En avance"
    return "Sin iniciar"


def semaforo_dias(dias):
    if dias > 21:
        return "#16a34a", "En plazo"
    if dias > 7:
        return "#f59e0b", "Atención al plazo"
    return "#dc2626", "Plazo crítico"


# ------------------------------------------------------------------ #
# GENERACIÓN DEL HTML
# ------------------------------------------------------------------ #
def generar_html(fases, hechos, total, hoy):
    pct_global = round(hechos / total * 100) if total else 0
    dias = (FECHA_LIMITE - hoy).days
    fases_ok = sum(1 for f in fases if f["total"] and f["hechos"] == f["total"])
    color_dias, etiqueta_dias = semaforo_dias(dias)

    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    fecha_gen = f"{hoy.day} de {meses[hoy.month]} de {hoy.year}"
    fecha_lim = f"{FECHA_LIMITE.day} de {meses[FECHA_LIMITE.month]} de {FECHA_LIMITE.year}"

    # Tarjetas de fase
    tarjetas = []
    for f in fases:
        pct = round(f["hechos"] / f["total"] * 100) if f["total"] else 0
        color = color_por_pct(pct)
        tarjetas.append(f"""
        <div class="fase">
          <div class="fase-top">
            <div>
              <div class="fase-titulo">{f['titulo']}</div>
              <div class="fase-sub">{f['subtitulo']}</div>
            </div>
            <div class="fase-pct" style="color:{color}">{pct}%</div>
          </div>
          <div class="barra"><div class="barra-fill" style="width:{pct}%;background:{color}"></div></div>
          <div class="fase-bottom">
            <span class="estado" style="background:{color}1a;color:{color}">{estado_texto(pct)}</span>
            <span class="conteo">{f['hechos']} de {f['total']} puntos</span>
          </div>
        </div>""")

    tarjetas_html = "\n".join(tarjetas)

    # Anillo de progreso global (conic-gradient)
    anillo_color = color_por_pct(pct_global)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tablero de Avance · {PROYECTO}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f1f5f9; color: #0f172a; padding: 28px 20px 48px;
  }}
  .wrap {{ max-width: 1040px; margin: 0 auto; }}
  header {{ text-align: center; margin-bottom: 26px; }}
  header .kicker {{ color: #64748b; font-size: 13px; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; }}
  header h1 {{ font-size: 30px; margin: 6px 0 4px; }}
  header .cliente {{ color: #475569; font-size: 15px; }}

  .kpis {{ display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 16px; margin: 22px 0 26px; }}
  @media (max-width: 760px) {{ .kpis {{ grid-template-columns: 1fr; }} }}
  .card {{ background: #fff; border-radius: 18px; padding: 24px; box-shadow: 0 1px 3px rgba(15,23,42,.08); }}

  .anillo-card {{ display: flex; align-items: center; gap: 22px; }}
  .anillo {{
    width: 132px; height: 132px; border-radius: 50%; flex: none;
    background: conic-gradient({anillo_color} {pct_global*3.6}deg, #e2e8f0 0deg);
    display: flex; align-items: center; justify-content: center;
  }}
  .anillo-inner {{
    width: 100px; height: 100px; background: #fff; border-radius: 50%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }}
  .anillo-inner .num {{ font-size: 34px; font-weight: 800; color: {anillo_color}; line-height: 1; }}
  .anillo-inner .lbl {{ font-size: 11px; color: #64748b; margin-top: 3px; }}
  .anillo-text .t1 {{ font-size: 14px; color: #64748b; font-weight: 600; }}
  .anillo-text .t2 {{ font-size: 22px; font-weight: 800; margin-top: 2px; }}
  .anillo-text .t3 {{ font-size: 13px; color: #475569; margin-top: 6px; }}

  .big {{ text-align: center; display: flex; flex-direction: column; justify-content: center; }}
  .big .num {{ font-size: 52px; font-weight: 800; line-height: 1; }}
  .big .lbl {{ font-size: 13px; color: #64748b; margin-top: 8px; font-weight: 600; }}
  .badge {{ display: inline-block; margin: 10px auto 0; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }}

  .seccion-titulo {{ font-size: 15px; font-weight: 800; color: #334155; text-transform: uppercase; letter-spacing: .06em; margin: 8px 4px 14px; }}
  .fases {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 760px) {{ .fases {{ grid-template-columns: 1fr; }} }}
  .fase {{ background: #fff; border-radius: 16px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(15,23,42,.08); }}
  .fase-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .fase-titulo {{ font-size: 16px; font-weight: 700; }}
  .fase-sub {{ font-size: 12.5px; color: #64748b; margin-top: 3px; }}
  .fase-pct {{ font-size: 26px; font-weight: 800; flex: none; }}
  .barra {{ height: 12px; background: #e2e8f0; border-radius: 999px; overflow: hidden; margin: 14px 0 10px; }}
  .barra-fill {{ height: 100%; border-radius: 999px; }}
  .fase-bottom {{ display: flex; justify-content: space-between; align-items: center; }}
  .estado {{ font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
  .conteo {{ font-size: 12.5px; color: #64748b; }}

  footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 30px; line-height: 1.6; }}
  .leyenda {{ display: flex; gap: 18px; justify-content: center; flex-wrap: wrap; margin-top: 8px; }}
  .leyenda span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .dot {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Tablero de Avance para Gerencia</div>
    <h1>{PROYECTO}</h1>
    <div class="cliente">{CLIENTE}</div>
  </header>

  <div class="kpis">
    <div class="card anillo-card">
      <div class="anillo"><div class="anillo-inner">
        <div class="num">{pct_global}%</div><div class="lbl">completado</div>
      </div></div>
      <div class="anillo-text">
        <div class="t1">Avance general del proyecto</div>
        <div class="t2" style="color:{anillo_color}">{hechos} de {total} puntos</div>
        <div class="t3">Puntos de control cumplidos sobre el total del plan.</div>
      </div>
    </div>

    <div class="card big">
      <div class="num" style="color:{color_dias}">{dias}</div>
      <div class="lbl">días para la fecha límite</div>
      <span class="badge" style="background:{color_dias}1a;color:{color_dias}">{etiqueta_dias}</span>
      <div class="t3" style="font-size:12px;color:#94a3b8;margin-top:8px">Fecha límite: {fecha_lim}</div>
    </div>

    <div class="card big">
      <div class="num" style="color:#16a34a">{fases_ok}<span style="font-size:26px;color:#94a3b8">/{len(fases)}</span></div>
      <div class="lbl">fases 100% completadas</div>
      <span class="badge" style="background:#2563eb1a;color:#2563eb">{len(fases)} fases en total</span>
    </div>
  </div>

  <div class="seccion-titulo">Avance por fase</div>
  <div class="fases">
    {tarjetas_html}
  </div>

  <footer>
    <div class="leyenda">
      <span><i class="dot" style="background:#16a34a"></i>Completado</span>
      <span><i class="dot" style="background:#2563eb"></i>Buen avance</span>
      <span><i class="dot" style="background:#f59e0b"></i>Iniciado</span>
      <span><i class="dot" style="background:#cbd5e1"></i>Sin iniciar</span>
    </div>
    <div style="margin-top:12px">Actualizado el {fecha_gen} · Documento fuente: Documento Maestro de Continuidad<br>
    CONFIDENCIAL — Uso interno · Información generada automáticamente a partir del avance registrado.</div>
  </footer>
</div>
</body>
</html>"""
    return html, pct_global, dias, fases_ok


# ------------------------------------------------------------------ #
# MAIN
# ------------------------------------------------------------------ #
def main():
    with open(DOC_MAESTRO, "r", encoding="utf-8") as fh:
        texto = fh.read()

    bloque = leer_seccion_checklist(texto)
    fases, hechos, total = parsear_fases(bloque)
    hoy = date.today()
    html, pct, dias, fases_ok = generar_html(fases, hechos, total, hoy)

    with open(SALIDA_HTML, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"[OK] Dashboard generado: {SALIDA_HTML}")
    print(f"     Cumplimiento global: {pct}%  ({hechos}/{total} puntos)")
    print(f"     Fases completadas:   {fases_ok}/{len(fases)}")
    print(f"     Días restantes:      {dias}")
    for f in fases:
        p = round(f['hechos']/f['total']*100) if f['total'] else 0
        print(f"       - {f['titulo']}: {p}% ({f['hechos']}/{f['total']})")


if __name__ == "__main__":
    main()

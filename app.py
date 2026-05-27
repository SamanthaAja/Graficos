import warnings, os
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from scipy import stats as sp_stats

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Generación Solar",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA = r"c:\Users\ajasa\OneDrive\Documentos\Graficos"

PLANTS = {
    "FERCHEGAS EL VIEJÓN": {
        "daily_csv":  os.path.join(DATA, "Ferchegaselviejon_generacioncompleto.csv"),
        "hourly_xls": os.path.join(DATA, "Ferchegas_El_viejon_3años.xls"),
        "clima_csv":  os.path.join(DATA, "Clima_ferchegaselviejon.csv"),
        "fmt": "ferchegas",
        "cap_kw": 45,
    },
}

MESES  = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
          7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
MESES_L = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
           7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

VERDE      = "#1B5E20"
VERDE_MED  = "#2E7D32"
VERDE_LIGHT= "#4CAF50"
VERDE_PALE = "#E8F5E9"
PALETA_ANIOS = {2020:"#aec7e8",2021:"#4878cf",2022:"#6acc65",
                2023:"#d65f5f",2024:"#b47cc7",2025:"#d7191c",2026:"#ff7f0e"}
COLS12 = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b",
          "#e377c2","#7f7f7f","#bcbd22","#17becf","#aec7e8","#ffbb78"]

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ocultar sidebar */
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] {{ display:none !important; }}

  /* ── Green header bar (targets horizontal block containing .hdr-sentinel) ── */
  [data-testid="stHorizontalBlock"]:has(.hdr-sentinel) {{
      background:{VERDE} !important;
      border-radius:12px !important;
      padding:10px 20px !important;
      margin-bottom:0.5rem;
      align-items:center !important;
  }}
  .hdr-plant {{ display:flex; align-items:center; gap:10px; }}
  .hdr-icon  {{ font-size:1.6rem; line-height:1; }}
  .hdr-name  {{ font-size:1.05rem; font-weight:700; color:white; margin:0; line-height:1.3; }}
  .hdr-sub   {{ font-size:0.72rem; color:rgba(255,255,255,0.68); margin:0; }}
  .period-label {{
      text-align:center; font-weight:600; font-size:0.95rem;
      color:white !important; margin:0; padding:6px 0; white-space:nowrap;
  }}
  /* All buttons inside the header bar */
  [data-testid="stHorizontalBlock"]:has(.hdr-sentinel) .stButton>button {{
      background:transparent !important; color:white !important;
      border:1.5px solid rgba(255,255,255,0.50) !important;
      border-radius:20px !important; padding:3px 8px !important;
      font-size:0.82rem !important; width:100% !important;
      transition:background 0.12s;
  }}
  [data-testid="stHorizontalBlock"]:has(.hdr-sentinel) .stButton>button:hover {{
      background:rgba(255,255,255,0.18) !important; border-color:white !important;
  }}
  /* Active gran button — white pill with green text */
  [data-testid="stHorizontalBlock"]:has(.hdr-sentinel) [data-testid="column"]:has(.gran-is-active) .stButton>button {{
      background:white !important; color:{VERDE} !important;
      font-weight:700 !important; border-color:white !important;
  }}

  /* ── KPI cards ── */
  .kpi-card {{
      background:white; border-radius:8px;
      padding:0.9rem 1.1rem 0.7rem 1.1rem;
      box-shadow:0 1px 4px rgba(0,0,0,0.09);
      border-bottom:3px solid {VERDE_LIGHT};
      height:105px; box-sizing:border-box;
  }}
  .kpi-lbl  {{ font-size:0.72rem; color:#888; margin:0 0 2px; text-transform:uppercase; letter-spacing:.04em; }}
  .kpi-val  {{ font-size:1.55rem; font-weight:700; color:#111; margin:0; line-height:1.2; }}
  .kpi-unit {{ font-size:0.85rem; font-weight:400; color:#555; }}
  .kpi-delta-pos {{ font-size:0.78rem; color:{VERDE_LIGHT}; margin:3px 0 0; }}
  .kpi-delta-neg {{ font-size:0.78rem; color:#e53935; margin:3px 0 0; }}

  /* ── Streamlit tabs ── */
  [data-baseweb="tab-list"] {{
      background:white; padding:0 1rem;
      border-bottom:2px solid #e0e0e0; border-radius:8px 8px 0 0;
  }}
  [data-baseweb="tab"] {{ color:#666; font-size:0.88rem; padding:.55rem 1.1rem; }}
  [aria-selected="true"] {{ color:{VERDE} !important; font-weight:700 !important; }}
</style>
""", unsafe_allow_html=True)

# ─── Data loading (cached) ────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_daily(planta: str) -> pd.DataFrame:
    cfg = PLANTS[planta]
    if cfg["fmt"] == "ferchegas":
        dd = pd.read_csv(cfg["daily_csv"], header=None,
             names=["id","codigo","Gen_kWh","Fecha","ts","flag","extra"])
    else:
        dd = pd.read_csv(cfg["daily_csv"], header=None,
             names=["planta","Fecha","Gen_kWh"])
    dd["Fecha"]   = pd.to_datetime(dd["Fecha"], errors="coerce")
    dd["Gen_kWh"] = pd.to_numeric(dd["Gen_kWh"], errors="coerce")
    dd = (dd.dropna(subset=["Fecha","Gen_kWh"])
            .drop_duplicates("Fecha")
            .sort_values("Fecha")
            .reset_index(drop=True))
    dd["Anio"] = dd["Fecha"].dt.year
    dd["Mes"]  = dd["Fecha"].dt.month
    return dd

@st.cache_data(show_spinner=False)
def load_hourly(planta: str):
    path = PLANTS[planta]["hourly_xls"]
    if path is None:
        return None
    raw = pd.read_html(path)[0]
    raw.columns = ["Datetime_str","Gen_kWh","Pron_kWh"]
    raw["Gen_kWh"]  = pd.to_numeric(raw["Gen_kWh"],  errors="coerce").fillna(0.0)
    raw["Pron_kWh"] = pd.to_numeric(raw["Pron_kWh"], errors="coerce").fillna(0.0)
    raw["Datetime"] = pd.to_datetime(raw["Datetime_str"])
    dh = raw[["Datetime","Gen_kWh","Pron_kWh"]].sort_values("Datetime").reset_index(drop=True)
    dh["Hora"] = dh["Datetime"].dt.hour
    dh["Mes"]  = dh["Datetime"].dt.month
    dh["Anio"] = dh["Datetime"].dt.year
    return dh

@st.cache_data(show_spinner=False)
def train_gbm_model(planta: str):
    from sklearn.ensemble import GradientBoostingRegressor
    dh = load_hourly(planta)
    if dh is None:
        return None, None, None
    df = dh.copy()
    df["dow"] = df["Datetime"].dt.dayofweek
    for lag in [1,2,3,4]:
        df[f"lag{lag}"] = df["Gen_kWh"].shift(lag)
    df["rs3"]  = df["Gen_kWh"].shift(1).rolling(3).std()
    df["rs6"]  = df["Gen_kWh"].shift(1).rolling(6).std()
    df["rm6"]  = df["Gen_kWh"].shift(1).rolling(6).mean()
    df = df.dropna().reset_index(drop=True)
    FEATS = ["lag1","lag2","lag3","lag4","Hora","Mes","dow","rs3","rs6","rm6"]
    tr = df[df["Anio"] == df["Anio"].max() - 1].copy()
    gbm = GradientBoostingRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        subsample=0.8, min_samples_leaf=10, random_state=42)
    gbm.fit(tr[FEATS], tr["Gen_kWh"])
    tr["resid"] = tr["Gen_kWh"] - gbm.predict(tr[FEATS]).clip(min=0)
    sig = tr.groupby("Hora")["resid"].std().fillna(5)
    return gbm, sig, FEATS

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_period(gran: str, offset: int, max_d: date):
    if gran == "Día":
        fin = max_d + timedelta(days=offset)
        return fin, fin
    elif gran == "Semana":
        fin = max_d + timedelta(weeks=offset)
        return fin - timedelta(days=6), fin
    elif gran == "Mes":
        base = (max_d.replace(day=1)) + relativedelta(months=offset)
        fin  = base + relativedelta(months=1) - timedelta(days=1)
        return base, min(fin, max_d)
    else:
        yr = max_d.year + offset
        return date(yr,1,1), min(date(yr,12,31), max_d)

def fmt_period(gran: str, ini: date, fin: date) -> str:
    if gran == "Día":
        return f"{ini.day} {MESES[ini.month]} {ini.year}"
    elif gran == "Semana":
        return f"{ini.day} {MESES[ini.month]} – {fin.day} {MESES[fin.month]} {fin.year}"
    elif gran == "Mes":
        return f"{MESES[ini.month]} {ini.year}"
    return str(ini.year)

def kpi(label, value, unit="", delta=None, sub=""):
    if delta is not None:
        cls = "kpi-delta-pos" if delta >= 0 else "kpi-delta-neg"
        d_html = f'<p class="{cls}">{"+" if delta>=0 else ""}{delta:.1f}% {sub}</p>'
    else:
        d_html = '<p style="margin:3px 0 0;font-size:0.78rem;color:transparent;">-</p>'
    return (f'<div class="kpi-card">'
            f'<p class="kpi-lbl">{label}</p>'
            f'<p class="kpi-val">{value} <span class="kpi-unit">{unit}</span></p>'
            f'{d_html}</div>')

def chart_style(fig, h=380, bg="white", margin=(10,10,45,10)):
    l,r,t,b = margin
    fig.update_layout(
        height=h, plot_bgcolor=bg, paper_bgcolor="white",
        margin=dict(l=l,r=r,t=t,b=b),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=9)),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eee")
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    return fig

# ─── Sidebar ──────────────────────────────────────────────────────────────────

planta = "FERCHEGAS EL VIEJÓN"

with st.sidebar:
    st.markdown("### Plantas Solares")
    st.markdown(f"**{planta}**")
    st.divider()

# ─── Load data ────────────────────────────────────────────────────────────────

with st.spinner("Cargando datos..."):
    dd  = load_daily(planta)
    dh  = load_hourly(planta)

max_d  = dd["Fecha"].max().date()
cap_kw = PLANTS[planta]["cap_kw"]

# ─── Session state ─────────────────────────────────────────────────────────────

if "gran"   not in st.session_state: st.session_state.gran   = "Mes"
if "offset" not in st.session_state: st.session_state.offset = 0
if "plant_prev" not in st.session_state: st.session_state.plant_prev = planta

if st.session_state.plant_prev != planta:
    st.session_state.offset = 0
    st.session_state.plant_prev = planta

# ─── Header (single green bar) ────────────────────────────────────────────────

ini, fin = get_period(st.session_state.gran, st.session_state.offset, max_d)

hcol1, hcol2, hcol3 = st.columns([5, 4, 4])

with hcol1:
    st.markdown(
        f'<span class="hdr-sentinel"></span>'
        f'<div class="hdr-plant">'
        f'<div><p class="hdr-name">{planta}</p>'
        f'<p class="hdr-sub">Generación Solar · datos al {max_d.strftime("%d %b %Y")}</p></div>'
        f'</div>',
        unsafe_allow_html=True)

with hcol2:
    p1, p2, p3 = st.columns([1, 6, 1])
    with p1:
        if st.button("‹", key="prev"):
            st.session_state.offset -= 1
            st.rerun()
    with p2:
        st.markdown(
            f'<p class="period-label">{fmt_period(st.session_state.gran, ini, fin)}</p>',
            unsafe_allow_html=True)
    with p3:
        if st.button("›", key="next") and st.session_state.offset < 0:
            st.session_state.offset += 1
            st.rerun()

with hcol3:
    g1, g2, g3, g4 = st.columns(4)
    for col, g in zip([g1, g2, g3, g4], ["Día", "Semana", "Mes", "Año"]):
        with col:
            if g == st.session_state.gran:
                st.markdown('<span class="gran-is-active"></span>', unsafe_allow_html=True)
            if st.button(g, key=f"g_{g}"):
                st.session_state.gran = g
                st.session_state.offset = 0
                st.rerun()

ini, fin = get_period(st.session_state.gran, st.session_state.offset, max_d)

# ─── Filter data ──────────────────────────────────────────────────────────────

dd_p = dd[
    (dd["Fecha"].dt.date >= ini) &
    (dd["Fecha"].dt.date <= fin)
].copy()

dh_p = None
if dh is not None:
    dh_p = dh[
        (dh["Datetime"].dt.date >= ini) &
        (dh["Datetime"].dt.date <= fin)
    ].copy()

dd_all = dd.copy()

# ─── KPI cards ────────────────────────────────────────────────────────────────

gen_tot  = dd_p["Gen_kWh"].sum()
prom_dia = dd_p["Gen_kWh"].mean() if len(dd_p) > 0 else 0
variab   = (dd_p["Gen_kWh"].std() / prom_dia * 100) if prom_dia > 0 else 0

try:
    ini_prev = ini.replace(year=ini.year-1)
    fin_prev = fin.replace(year=fin.year-1)
except ValueError:
    ini_prev = ini - relativedelta(years=1)
    fin_prev = fin - relativedelta(years=1)

dd_prev  = dd[(dd["Fecha"].dt.date >= ini_prev) & (dd["Fecha"].dt.date <= fin_prev)]
gen_prev = dd_prev["Gen_kWh"].sum()
delta_yoy = (gen_tot/gen_prev-1)*100 if gen_prev > 0 else None

cumpl = None
if dh_p is not None and len(dh_p) > 0:
    diur = dh_p[dh_p["Gen_kWh"] > 1]
    if len(diur) > 0 and diur["Pron_kWh"].sum() > 0:
        cumpl = diur["Gen_kWh"].sum() / diur["Pron_kWh"].sum() * 100

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi("Generación total", f"{gen_tot:,.0f}", "kWh", delta_yoy, "vs año ant."),
                unsafe_allow_html=True)
with k2:
    st.markdown(kpi("Promedio diario", f"{prom_dia:,.1f}", "kWh/día"),
                unsafe_allow_html=True)
with k3:
    if cumpl is not None:
        st.markdown(kpi("Cumplimiento pronóstico", f"{cumpl:.1f}", "%",
                        cumpl-100, "vs objetivo"), unsafe_allow_html=True)
    elif cap_kw:
        y_val = gen_tot / cap_kw if cap_kw else 0
        st.markdown(kpi("Yield del período", f"{y_val:,.1f}", "kWh/kWp"),
                    unsafe_allow_html=True)
    else:
        st.markdown(kpi("Días con datos", f"{len(dd_p)}", "días"),
                    unsafe_allow_html=True)
with k4:
    st.markdown(kpi("Variabilidad", f"{variab:.1f}", "%"),
                unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Estado Actual",
    "Contexto Estacional",
    "Histórico",
    "Tendencia",
    "Pronóstico",
])

# ── TAB 1: Estado Actual ───────────────────────────────────────────────────────

with tab1:
    c_a, c_b = st.columns([3, 2])

    with c_a:
        if dh_p is not None and len(dh_p) > 0:
            fig = make_subplots(rows=2, cols=1, row_heights=[0.68, 0.32],
                shared_xaxes=True, vertical_spacing=0.04,
                subplot_titles=["Real vs Pronóstico oficial",
                                "Error (Pronóstico − Real)"])
            fig.add_trace(go.Scatter(
                x=dh_p["Datetime"], y=dh_p["Gen_kWh"],
                fill="tozeroy", fillcolor="rgba(76,175,80,0.10)",
                line=dict(color=VERDE_MED, width=2), name="Real",
                hovertemplate="%{x|%d %b %H:%M}<br>Real: %{y:.1f} kWh<extra></extra>"),
                row=1, col=1)
            fig.add_trace(go.Scatter(
                x=dh_p["Datetime"], y=dh_p["Pron_kWh"],
                line=dict(color="#e53935", width=1.8, dash="dash"),
                name="Pronóstico",
                hovertemplate="%{x|%d %b %H:%M}<br>Pron: %{y:.1f} kWh<extra></extra>"),
                row=1, col=1)
            err = dh_p["Pron_kWh"] - dh_p["Gen_kWh"]
            fig.add_trace(go.Bar(
                x=dh_p["Datetime"], y=err,
                marker_color=["#e53935" if e>0 else VERDE_MED for e in err],
                opacity=0.7, name="Error",
                hovertemplate="%{x|%d %b %H:%M}<br>%{y:+.1f} kWh<extra></extra>"),
                row=2, col=1)
            fig.add_hline(y=0, line_color="#333", line_width=1, row=2, col=1)
            fig.update_yaxes(title_text="kWh/h", row=1, col=1)
            fig.update_yaxes(title_text="Error kWh", row=2, col=1)
            chart_style(fig, h=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dd_p["Fecha"], y=dd_p["Gen_kWh"],
                marker_color=VERDE_MED, opacity=0.85, name="Generación",
                hovertemplate="%{x|%d %b %Y}: %{y:,.0f} kWh<extra></extra>"))
            if len(dd_p) > 0:
                avg = dd_p["Gen_kWh"].mean()
                fig.add_hline(y=avg, line_dash="dot", line_color="#e07b00",
                    annotation_text=f"Promedio {avg:.0f} kWh",
                    annotation_position="top right", annotation_font_size=10)
            fig.update_layout(title="Generación diaria en el período")
            fig.update_yaxes(rangemode="tozero")
            chart_style(fig, h=420)
            st.plotly_chart(fig, use_container_width=True)

    with c_b:
        if dh_p is not None and len(dh_p) > 0:
            perfil = (dh_p.groupby("Hora")["Gen_kWh"]
                      .agg(["median","std"]).reset_index())
            perfil["std"] = perfil["std"].fillna(0)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=list(perfil["Hora"])+list(perfil["Hora"])[::-1],
                y=list(perfil["median"]+perfil["std"])+
                  list((perfil["median"]-perfil["std"]).clip(lower=0))[::-1],
                fill="toself", fillcolor="rgba(76,175,80,0.12)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip"))
            fig2.add_trace(go.Scatter(
                x=perfil["Hora"], y=perfil["median"],
                line=dict(color=VERDE_MED, width=2.5),
                hovertemplate="%{x}:00 — %{y:.1f} kWh/h<extra></extra>",
                name="Mediana"))
            h_pico = int(perfil.loc[perfil["median"].idxmax(), "Hora"])
            fig2.update_layout(
                title=f"Perfil horario — pico a las {h_pico:02d}:00",
                showlegend=False)
            fig2.update_xaxes(title="Hora", tickmode="linear", tick0=5, dtick=2)
            fig2.update_yaxes(title="kWh/h", rangemode="tozero")
            chart_style(fig2, h=420)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            fig2 = go.Figure()
            if len(dd_p) > 0:
                fig2.add_trace(go.Histogram(
                    x=dd_p["Gen_kWh"], nbinsx=20,
                    marker_color=VERDE_MED, opacity=0.8,
                    hovertemplate="%{x:.0f} kWh: %{y} días<extra></extra>"))
            fig2.update_layout(title="Distribución generación diaria")
            fig2.update_xaxes(title="kWh/día")
            fig2.update_yaxes(title="Días")
            chart_style(fig2, h=420)
            st.plotly_chart(fig2, use_container_width=True)

# ── TAB 2: Contexto Estacional ─────────────────────────────────────────────────

with tab2:
    if dh is not None:
        dh_seas = dh.copy()

        s1, s2 = st.columns(2)
        with s1:
            pivot = (dh_seas.groupby(["Hora","Mes"])["Gen_kWh"]
                    .median().unstack("Mes").reindex(columns=range(1,13)))
            fig = go.Figure(go.Heatmap(
                z=pivot.values,
                x=[MESES[m] for m in pivot.columns],
                y=[f"{h:02d}:00" for h in pivot.index],
                colorscale=[[0,"#f7fbff"],[0.15,"#c6dbef"],[0.4,"#6baed6"],
                            [0.65,"#fdae6b"],[0.85,"#f16913"],[1,"#d94801"]],
                colorbar=dict(title="kWh/h", thickness=12), zmin=0,
                hovertemplate="%{y} · %{x}<br>%{z:.1f} kWh/h<extra></extra>"))
            fig.update_layout(title="Intensidad por hora y mes",
                              yaxis=dict(autorange="reversed", tickfont=dict(size=9)))
            chart_style(fig, h=380)
            st.plotly_chart(fig, use_container_width=True)

        with s2:
            diurno = dh_seas[(dh_seas["Hora"]>=5) & (dh_seas["Hora"]<=20)]
            pf = diurno.groupby(["Mes","Hora"])["Gen_kWh"].agg(["median","std"]).reset_index()
            fig2 = go.Figure()
            for mes in range(1,13):
                d = pf[pf["Mes"]==mes].sort_values("Hora")
                if d.empty: continue
                c = COLS12[mes-1]
                r2,g2,b2 = int(c[1:3],16),int(c[3:5],16),int(c[5:7],16)
                fig2.add_trace(go.Scatter(
                    x=list(d["Hora"])+list(d["Hora"])[::-1],
                    y=list(d["median"]+d["std"].fillna(0))+
                      list((d["median"]-d["std"].fillna(0)).clip(lower=0))[::-1],
                    fill="toself", fillcolor=f"rgba({r2},{g2},{b2},0.09)",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False, hoverinfo="skip"))
                fig2.add_trace(go.Scatter(
                    x=d["Hora"], y=d["median"], name=MESES[mes],
                    line=dict(color=c, width=1.8),
                    hovertemplate=f"{MESES[mes]} %{{x}}h: %{{y:.1f}} kWh<extra></extra>"))
            fig2.update_layout(title="Perfil horario por mes (±1σ)")
            fig2.update_xaxes(title="Hora", tickmode="linear", tick0=5, dtick=2)
            fig2.update_yaxes(title="kWh/h", rangemode="tozero")
            chart_style(fig2, h=380)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Datos horarios no disponibles — mostrando solo distribución mensual.")

    med_glob = dd_all["Gen_kWh"].median()
    fig3 = go.Figure()
    for mes in range(1,13):
        vals = dd_all[dd_all["Mes"]==mes]["Gen_kWh"]
        if vals.empty: continue
        fig3.add_trace(go.Box(
            y=vals, name=MESES[mes],
            marker=dict(color=VERDE_MED, size=2, opacity=0.4),
            line_color=VERDE_MED, fillcolor="rgba(46,125,50,0.12)",
            boxmean="sd",
            hovertemplate=f"{MESES[mes]}: %{{y:.0f}} kWh<extra></extra>"))
    fig3.add_hline(y=med_glob, line_color="#e07b00", line_dash="dash", line_width=1.5,
        annotation_text=f"Mediana {med_glob:.0f} kWh",
        annotation_position="top right", annotation_font_size=10)
    fig3.update_layout(title="Distribución de generación diaria por mes (histórico completo)",
                       showlegend=False)
    fig3.update_xaxes(title="Mes", showgrid=False)
    fig3.update_yaxes(title="kWh/día", rangemode="tozero")
    chart_style(fig3, h=360)
    st.plotly_chart(fig3, use_container_width=True)

# ── TAB 3: Histórico ───────────────────────────────────────────────────────────

with tab3:
    h1, h2 = st.columns(2)

    with h1:
        mens = dd[dd["Anio"]>=2021].groupby(["Anio","Mes"])["Gen_kWh"].sum().reset_index()
        anios_ord = sorted(mens["Anio"].unique(), reverse=True)
        max_anio  = anios_ord[0]
        # Verde degradado: año actual oscuro → años anteriores más claros
        VERDE_GRAD = ["#1B5E20","#2E7D32","#43A047","#66BB6A","#A5D6A7","#C8E6C9","#E8F5E9"]
        pal_grad = {a: VERDE_GRAD[min(i, len(VERDE_GRAD)-1)] for i, a in enumerate(anios_ord)}
        fig = go.Figure()
        for anio in sorted(mens["Anio"].unique()):
            d = mens[mens["Anio"]==anio].sort_values("Mes")
            es_actual = anio == max_anio
            fig.add_trace(go.Scatter(
                x=[MESES[m] for m in d["Mes"]], y=d["Gen_kWh"],
                name=str(anio)+(" *" if es_actual else ""),
                mode="lines+markers",
                line=dict(color=pal_grad.get(anio,"#888"),
                          width=2.8 if es_actual else 1.8,
                          dash="dot" if es_actual else "solid"),
                marker=dict(size=7 if es_actual else 5),
                hovertemplate=f"{anio} %{{x}}: %{{y:,.0f}} kWh<extra></extra>"))
        fig.update_layout(title="Generación mensual por año", hovermode="x unified")
        fig.update_xaxes(title="Mes")
        fig.update_yaxes(title="kWh", rangemode="tozero", tickformat=",.0f")
        chart_style(fig, h=360)
        st.plotly_chart(fig, use_container_width=True)

    with h2:
        mb = (dd[dd["Anio"]>=2021].groupby(["Anio","Mes"])["Gen_kWh"]
              .sum().reset_index()
              .sort_values(["Anio","Mes"]).reset_index(drop=True))
        mb["Label"] = mb.apply(
            lambda r: f"{MESES[r['Mes']]} {str(r['Anio'])[2:]}", axis=1)
        prom_mb = mb["Gen_kWh"].mean()
        mb["MM3"] = mb["Gen_kWh"].rolling(3, center=True, min_periods=2).mean()
        bar_c = ["#1a6b2e" if v>=prom_mb else "#a8d5a2" for v in mb["Gen_kWh"]]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=mb["Label"], y=mb["Gen_kWh"],
            marker_color=bar_c, name="Mensual",
            hovertemplate="%{x}: %{y:,.0f} kWh<extra></extra>"))
        fig2.add_trace(go.Scatter(
            x=mb["Label"], y=mb["MM3"],
            line=dict(color="#e07b00", width=2.2), name="MM3",
            hovertemplate="%{x}: %{y:,.0f} kWh<extra></extra>"))
        fig2.add_hline(y=prom_mb, line_dash="dot", line_color="#555", line_width=1.2,
            annotation_text=f"Prom {prom_mb/1000:.1f} MWh",
            annotation_position="top right", annotation_font_size=10)
        fig2.update_layout(title="Barras mensuales + media móvil 3 meses",
                           bargap=0.15)
        fig2.update_xaxes(tickangle=-45, tickfont=dict(size=9), showgrid=False)
        fig2.update_yaxes(title="kWh", rangemode="tozero", tickformat=",.0f")
        chart_style(fig2, h=360)
        st.plotly_chart(fig2, use_container_width=True)

    anio_v = dd["Anio"].max()
    pal2 = {anio_v-2:"#c6dbef", anio_v-1:"#6baed6", anio_v:"#08519c"}
    fig3 = go.Figure()
    for anio in [anio_v-2, anio_v-1, anio_v]:
        d = dd[dd["Anio"]==anio].sort_values("Fecha").copy()
        if d.empty: continue
        d["DiaAnio"] = d["Fecha"].dt.dayofyear
        d["Acum"]    = d["Gen_kWh"].cumsum()
        fig3.add_trace(go.Scatter(
            x=d["DiaAnio"], y=d["Acum"], name=str(anio),
            fill="tozeroy" if anio==anio_v else None,
            fillcolor="rgba(8,81,156,0.07)",
            line=dict(color=pal2.get(anio,"#888"), width=2.2,
                      dash="solid" if anio==anio_v else "dash"),
            hovertemplate=f"{anio} día %{{x}}: %{{y:,.0f}} kWh acum<extra></extra>"))
    fig3.update_layout(
        title=f"Generación acumulada anual — {anio_v-2} a {anio_v}")
    fig3.update_xaxes(title="Día del año")
    fig3.update_yaxes(title="kWh acumulados", tickformat=",.0f")
    chart_style(fig3, h=320)
    st.plotly_chart(fig3, use_container_width=True)

# ── TAB 4: Tendencia ───────────────────────────────────────────────────────────

with tab4:
    d_tend = dd[dd["Anio"]>=2021].sort_values("Fecha").copy()
    d_tend["t"] = (d_tend["Fecha"] - d_tend["Fecha"].min()).dt.days
    sl, ic, r_v, p_v, _ = sp_stats.linregress(d_tend["t"], d_tend["Gen_kWh"])
    d_tend["MM30"] = d_tend["Gen_kWh"].rolling(30, center=True, min_periods=10).mean()

    fig = go.Figure()
    for anio in sorted(d_tend["Anio"].unique()):
        s = d_tend[d_tend["Anio"]==anio]
        fig.add_trace(go.Scatter(
            x=s["Fecha"], y=s["Gen_kWh"], mode="markers",
            marker=dict(color=PALETA_ANIOS.get(anio,"#888"), size=3, opacity=0.4),
            name=str(anio),
            hovertemplate="%{x|%d %b %Y}: %{y:.0f} kWh<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=d_tend["Fecha"], y=d_tend["MM30"],
        line=dict(color="#222", width=2.5), name="MM30"))
    fig.add_trace(go.Scatter(
        x=[d_tend["Fecha"].min(), d_tend["Fecha"].max()],
        y=[ic, ic + sl*d_tend["t"].max()],
        line=dict(color="#e53935", width=2, dash="dash"),
        name=f"Tendencia {sl:+.2f} kWh/día"))
    fig.update_layout(
        title=f"Tendencia diaria — pendiente {sl:+.3f} kWh/día | R²={r_v**2:.3f} | p={p_v:.4f}")
    fig.update_yaxes(title="kWh/día", rangemode="tozero")
    chart_style(fig, h=400)
    st.plotly_chart(fig, use_container_width=True)

    t1, t2 = st.columns(2)
    with t1:
        mes_v  = dd["Fecha"].max().month
        anio_v = dd["Fecha"].max().year
        act  = dd[(dd["Mes"]==mes_v) & (dd["Anio"]==anio_v)]
        hist = dd[(dd["Mes"]==mes_v) & (dd["Anio"]<anio_v) & (dd["Anio"]>=2021)]
        hd   = hist.groupby(hist["Fecha"].dt.day)["Gen_kWh"].agg(["min","max","median"]).reset_index()
        hd.columns = ["Dia","Min","Max","Median"]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=list(hd["Dia"])+list(hd["Dia"])[::-1],
            y=list(hd["Max"])+list(hd["Min"])[::-1],
            fill="toself", fillcolor="rgba(150,150,150,0.12)",
            line=dict(color="rgba(0,0,0,0)"), name="Rango hist."))
        fig2.add_trace(go.Scatter(
            x=hd["Dia"], y=hd["Median"],
            line=dict(color="#888", width=1.5, dash="dash"), name="Mediana hist."))
        fig2.add_trace(go.Bar(
            x=act["Fecha"].dt.day, y=act["Gen_kWh"],
            marker_color=VERDE_MED, opacity=0.85,
            name=f"{MESES[mes_v]} {anio_v}",
            hovertemplate="Día %{x}: %{y:.0f} kWh<extra></extra>"))
        fig2.update_layout(
            title=f"Diario {MESES[mes_v]} {anio_v} vs histórico", barmode="overlay")
        fig2.update_xaxes(title="Día del mes", tickmode="linear", dtick=5)
        fig2.update_yaxes(title="kWh", rangemode="tozero")
        chart_style(fig2, h=320)
        st.plotly_chart(fig2, use_container_width=True)

    with t2:
        dd_ref   = dd[dd["Anio"]>=2021].copy()
        prom_g   = dd_ref["Gen_kWh"].mean()
        sobre    = dd_ref.groupby("Mes").apply(
            lambda x: (x["Gen_kWh"] >= prom_g).sum()).reset_index()
        sobre.columns = ["Mes","Sobre"]
        bar_sc = ["#1a6b2e" if v >= 15 else "#a8d5a2" for v in sobre["Sobre"]]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=[MESES[m] for m in sobre["Mes"]], y=sobre["Sobre"],
            marker_color=bar_sc,
            hovertemplate="%{x}: %{y} días sobre promedio<extra></extra>"))
        fig3.update_layout(
            title=f"Días sobre el promedio global ({prom_g:.0f} kWh) por mes",
            showlegend=False)
        fig3.update_xaxes(showgrid=False)
        fig3.update_yaxes(title="Días")
        chart_style(fig3, h=320)
        st.plotly_chart(fig3, use_container_width=True)

# ── TAB 5: Pronóstico ─────────────────────────────────────────────────────────

with tab5:
    if dh is None:
        st.info("El pronóstico probabilístico requiere datos horarios y pronóstico oficial. "
                "No disponible para esta planta.")
    else:
        with st.spinner("Entrenando modelo GBM (se cachea tras la primera carga)..."):
            gbm, sig_h, FEATS = train_gbm_model(planta)

        if gbm is None:
            st.warning("No se pudo entrenar el modelo.")
        else:
            # Build forecast for latest month in data
            df_full = dh.copy()
            df_full["dow"] = df_full["Datetime"].dt.dayofweek
            for lag in [1,2,3,4]:
                df_full[f"lag{lag}"] = df_full["Gen_kWh"].shift(lag)
            df_full["rs3"] = df_full["Gen_kWh"].shift(1).rolling(3).std()
            df_full["rs6"] = df_full["Gen_kWh"].shift(1).rolling(6).std()
            df_full["rm6"] = df_full["Gen_kWh"].shift(1).rolling(6).mean()
            df_full = df_full.dropna().reset_index(drop=True)

            from sklearn.metrics import mean_squared_error, mean_absolute_error

            train_yr   = dh["Anio"].max() - 1
            test_years = sorted(y for y in df_full["Anio"].unique() if y != train_yr)

            # ── Test set: años fuera de muestra ──
            test = df_full[df_full["Anio"] != train_yr].copy()
            test["gbm_pred"] = gbm.predict(test[FEATS]).clip(min=0)
            cmp_h = test[["Datetime","Anio","Mes","Hora","Gen_kWh","gbm_pred"]].merge(
                dh[["Datetime","Pron_kWh"]], on="Datetime", how="inner")
            cmp_d = cmp_h[cmp_h["Gen_kWh"] > 1.0].copy()
            cmp_d["err_gbm"] = cmp_d["gbm_pred"] - cmp_d["Gen_kWh"]
            cmp_d["err_of"]  = cmp_d["Pron_kWh"] - cmp_d["Gen_kWh"]
            cmp_d["pct_gbm"] = cmp_d["err_gbm"].abs() / cmp_d["Gen_kWh"] * 100
            cmp_d["pct_of"]  = cmp_d["err_of"].abs()  / cmp_d["Gen_kWh"] * 100

            def _met(real, pred):
                e = pred - real
                return dict(
                    RMSE    = float(np.sqrt(mean_squared_error(real, pred))),
                    MAE     = float(mean_absolute_error(real, pred)),
                    MAPE    = float((e.abs()/real*100).mean()),
                    Sesgo   = float(e.mean()),
                    R2      = float(1 - ((real-pred)**2).sum()/((real-real.mean())**2).sum()),
                    EnerErr = float((pred.sum()-real.sum())/real.sum()*100),
                )
            mg = _met(cmp_d["Gen_kWh"], cmp_d["gbm_pred"])
            mo = _met(cmp_d["Gen_kWh"], cmp_d["Pron_kWh"])

            # ── Fila 1: Tabla + barras de métricas ──
            tc1, tc2 = st.columns([1, 2])
            with tc1:
                FILAS = ["RMSE (kWh/h)","MAE (kWh/h)","MAPE (%)","Sesgo (kWh/h)","R²","Error energía (%)"]
                KEYS  = ["RMSE","MAE","MAPE","Sesgo","R2","EnerErr"]
                FMT   = ["{:.2f}","{:.2f}","{:.1f}","{:+.2f}","{:.3f}","{:+.1f}"]
                v_gbm = [FMT[i].format(mg[k]) for i, k in enumerate(KEYS)]
                v_of  = [FMT[i].format(mo[k]) for i, k in enumerate(KEYS)]
                v_dif = []
                ganador = []
                for k in KEYS:
                    g, o = mg[k], mo[k]
                    if k == "R2":
                        v_dif.append(f"{(g-o):+.3f} pp")
                        ganador.append("GBM" if g > o else "Oficial")
                    else:
                        v_dif.append(f"{(g/o-1)*100:+.1f}%" if o != 0 else "—")
                        ganador.append("GBM" if abs(g) < abs(o) else "Oficial")
                col_g = ["rgba(46,125,50,0.15)" if w=="GBM" else "white" for w in ganador]
                col_o = ["rgba(229,57,53,0.12)" if w=="Oficial" else "white" for w in ganador]
                fig_tbl = go.Figure(go.Table(
                    columnwidth=[160, 100, 115, 105],
                    header=dict(
                        values=["<b>Métrica</b>","<b>GBM Lean</b>","<b>Pron. Oficial</b>","<b>Diferencia</b>"],
                        fill_color=VERDE, font=dict(color="white", size=11),
                        align=["left","center","center","center"], height=30),
                    cells=dict(
                        values=[FILAS, v_gbm, v_of, v_dif],
                        fill_color=[["white"]*6, col_g, col_o, ["white"]*6],
                        font=dict(color="#111", size=11),
                        align=["left","center","center","center"], height=27)))
                fig_tbl.update_layout(
                    title=f"Período evaluado: {' + '.join(str(y) for y in test_years)} (fuera de muestra)",
                    height=330, margin=dict(l=0, r=0, t=45, b=0))
                st.plotly_chart(fig_tbl, use_container_width=True)

            with tc2:
                MBAR = [("RMSE","RMSE (kWh/h)"),("MAE","MAE (kWh/h)"),
                        ("MAPE","MAPE (%)"),("R2","R²")]
                fig_bar = make_subplots(rows=1, cols=4,
                    subplot_titles=[lbl for _, lbl in MBAR])
                for i, (k, _) in enumerate(MBAR, 1):
                    for modelo, vals, c in [("GBM", mg, VERDE_MED), ("Oficial", mo, "#e53935")]:
                        v = vals[k]
                        fig_bar.add_trace(go.Bar(
                            name=modelo, x=[modelo], y=[abs(v)],
                            marker_color=c,
                            text=[f"{v:.2f}"], textposition="outside",
                            showlegend=(i==1),
                            hovertemplate=f"{modelo}: {v:.3f}<extra></extra>"),
                            row=1, col=i)
                fig_bar.update_layout(
                    height=310, plot_bgcolor="white", barmode="group",
                    legend=dict(orientation="h", yanchor="bottom", y=1.10,
                                xanchor="center", x=0.5, font=dict(size=10)),
                    title="Comparación de métricas por modelo",
                    margin=dict(l=10, r=10, t=55, b=10))
                fig_bar.update_yaxes(showgrid=True, gridcolor="#eee",
                                     rangemode="tozero", tickfont=dict(size=9))
                fig_bar.update_xaxes(tickfont=dict(size=9))
                st.plotly_chart(fig_bar, use_container_width=True)

            # ── Fila 2: Evolución mensual del MAPE ──
            cmp_d["YM"]    = cmp_d["Datetime"].dt.to_period("M")
            men = cmp_d.groupby("YM").agg(
                mape_gbm=("pct_gbm","mean"),
                mape_of =("pct_of" ,"mean"),
            ).reset_index()
            men["YM_str"] = men["YM"].astype(str)
            men["dif"]    = men["mape_gbm"] - men["mape_of"]
            col_dif = [VERDE_MED if d < 0 else "#e53935" for d in men["dif"]]

            fig_men = make_subplots(
                rows=2, cols=1, row_heights=[0.62, 0.38],
                shared_xaxes=True, vertical_spacing=0.05,
                subplot_titles=["MAPE mensual (horas diurnas con gen > 1 kWh/h)",
                                "Δ MAPE: GBM − Oficial  (verde = GBM mejor)"])
            fig_men.add_trace(go.Scatter(
                x=men["YM_str"], y=men["mape_gbm"], name="GBM Lean",
                line=dict(color=VERDE_MED, width=2.5), marker=dict(size=7),
                hovertemplate="%{x}<br>MAPE GBM: %{y:.1f}%<extra></extra>"), row=1, col=1)
            fig_men.add_trace(go.Scatter(
                x=men["YM_str"], y=men["mape_of"], name="Pron. Oficial",
                line=dict(color="#e53935", width=2.5), marker=dict(size=7),
                hovertemplate="%{x}<br>MAPE Oficial: %{y:.1f}%<extra></extra>"), row=1, col=1)
            fig_men.add_trace(go.Bar(
                x=men["YM_str"], y=men["dif"], marker_color=col_dif,
                showlegend=False,
                hovertemplate="%{x}<br>Δ = %{y:+.1f} pp<extra></extra>"), row=2, col=1)
            fig_men.add_hline(y=0, line_color="#333", line_width=1.2, row=2, col=1)
            fig_men.update_layout(
                title="Evolución mensual del error de predicción",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.04,
                            xanchor="right", x=1, font=dict(size=10)),
                margin=dict(l=10, r=10, t=55, b=10))
            fig_men.update_yaxes(showgrid=True, gridcolor="#eee",
                                 title_text="MAPE (%)", row=1, col=1)
            fig_men.update_yaxes(showgrid=True, gridcolor="#eee",
                                 title_text="Δ pp", row=2, col=1)
            fig_men.update_xaxes(tickangle=-45, tickfont=dict(size=9), showgrid=False)
            chart_style(fig_men, h=500, margin=(10,10,55,10))
            st.plotly_chart(fig_men, use_container_width=True)

            # ── Fila 3: Generación diaria año actual vs GBM vs Oficial ──
            anio_test = dh["Anio"].max()
            cmp_ult = cmp_h[cmp_h["Anio"] == anio_test].copy()
            cmp_ult["Fecha"] = cmp_ult["Datetime"].dt.normalize()
            daily_ult = cmp_ult.groupby("Fecha").agg(
                Real   =("Gen_kWh","sum"),
                GBM    =("gbm_pred","sum"),
                Oficial=("Pron_kWh","sum"),
            ).reset_index()

            fig_d26 = go.Figure()
            fig_d26.add_trace(go.Bar(
                x=daily_ult["Fecha"], y=daily_ult["Real"],
                name="Real", marker_color=VERDE_MED, opacity=0.85,
                hovertemplate="%{x|%d %b}<br>Real: %{y:.0f} kWh<extra></extra>"))
            fig_d26.add_trace(go.Scatter(
                x=daily_ult["Fecha"], y=daily_ult["GBM"],
                name="GBM Lean", line=dict(color="#e53935", width=2.2),
                marker=dict(size=5),
                hovertemplate="%{x|%d %b}<br>GBM: %{y:.0f} kWh<extra></extra>"))
            fig_d26.add_trace(go.Scatter(
                x=daily_ult["Fecha"], y=daily_ult["Oficial"],
                name="Pron. Oficial", line=dict(color="#9E9E9E", width=1.8, dash="dash"),
                hovertemplate="%{x|%d %b}<br>Oficial: %{y:.0f} kWh<extra></extra>"))
            fig_d26.update_layout(
                title=f"GBM Lean — Generación diaria vs Real (test {anio_test})",
                barmode="overlay", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.04,
                            xanchor="center", x=0.5, font=dict(size=11)))
            fig_d26.update_xaxes(showgrid=True, gridcolor="#eee", tickformat="%d %b")
            fig_d26.update_yaxes(showgrid=True, gridcolor="#eee",
                                  title_text="kWh/día", rangemode="tozero")
            chart_style(fig_d26, h=400, margin=(10,10,65,10))
            st.plotly_chart(fig_d26, use_container_width=True)

            # ── Fila 4: Generación diaria mes actual (real + modelo + forecast) ──
            last_dt  = cmp_h["Datetime"].max()
            mes_fc   = int(last_dt.month)
            anio_fc  = int(last_dt.year)

            # Días con datos reales del mes actual
            mes_h = cmp_h[(cmp_h["Mes"] == mes_fc) & (cmp_h["Anio"] == anio_fc)].copy()
            mes_h["Fecha"] = mes_h["Datetime"].dt.normalize()
            real_d = mes_h.groupby("Fecha").agg(
                Real  =("Gen_kWh", "sum"),
                Modelo=("gbm_pred", "sum"),
            ).reset_index()
            prom_real = float(real_d["Real"].mean()) if len(real_d) else 0
            tot_real  = float(real_d["Real"].sum())

            # Perfil horario mismo mes año anterior + ratio de corrección
            lp_src2 = df_full[(df_full["Anio"] == anio_fc - 1) & (df_full["Mes"] == mes_fc)]
            lp2 = lp_src2.groupby("Hora")[["lag1","lag2","lag3","lag4",
                                            "rs3","rs6","rm6"]].median()
            real_mes2 = df_full[(df_full["Anio"] == anio_fc) & (df_full["Mes"] == mes_fc)].copy()
            if len(real_mes2) > 0:
                ratio2 = real_mes2["Gen_kWh"].sum() / max(
                    gbm.predict(real_mes2[FEATS]).clip(min=0).sum(), 1)
            else:
                ratio2 = 1.0

            # Irradiación diaria (factor variación por día)
            try:
                _clim = pd.read_csv(
                    PLANTS[planta].get("clima_csv",
                        "Clima_ferchegaselviejon.csv"),
                    header=None,
                    names=["id","np","id2","irr","hum","vv","nub","temp","fec","hor","fh","gen"])
                _clim["fh"] = pd.to_datetime(_clim["fh"], errors="coerce")
                _clim = (_clim.dropna(subset=["fh"])
                              .drop_duplicates("fh")
                              .set_index("fh").sort_index())
                _clim["irr"] = pd.to_numeric(_clim["irr"], errors="coerce").fillna(0)
                irr_ref = (_clim.loc[
                    f"{anio_fc-1}-{mes_fc:02d}-01":
                    f"{anio_fc-1}-{mes_fc:02d}-28", "irr"]
                    .resample("D").sum().mean())
                irr_ref = irr_ref if irr_ref > 0 else 1.0
                _inicio_fc = pd.Timestamp(anio_fc, mes_fc,
                    int(real_d["Fecha"].max().day) + 1 if len(real_d) else 1)
                _fin_fc = pd.Timestamp(anio_fc, mes_fc,
                    pd.Timestamp(anio_fc, mes_fc, 1).days_in_month)
                irr_fut = (_clim.loc[_inicio_fc:_fin_fc, "irr"]
                               .resample("D").sum().reset_index())
                irr_fut.columns = ["fh", "irr"]
                irr_fut["fac"] = (irr_fut["irr"] / irr_ref).clip(0.3, 1.5)
                irr_map = irr_fut.set_index("fh")["fac"].to_dict()
            except Exception:
                irr_map = {}

            # Tendencia lineal 2026 en datos diarios
            dd_tend = dd[dd["Anio"] == anio_fc].copy()
            dd_tend["t"] = (dd_tend["Fecha"] - dd_tend["Fecha"].min()).dt.days
            if len(dd_tend) >= 5:
                from scipy import stats as _stats
                _sl, _ic, _, _, _ = _stats.linregress(dd_tend["t"], dd_tend["Gen_kWh"])
                _fecha_ref = real_d["Fecha"].max() if len(real_d) else dd_tend["Fecha"].max()
                _dias_ref  = int((pd.Timestamp(_fecha_ref) - dd_tend["Fecha"].min()).days)
            else:
                _sl, _ic, _dias_ref = 0.0, 0.0, 0

            # Forecast días restantes con irradiación + tendencia
            days_in_month2 = pd.Timestamp(anio_fc, mes_fc, 1).days_in_month
            ultimo_dia = int(real_d["Fecha"].max().day) if len(real_d) else 0
            fc_d_rows = []
            for dia in range(ultimo_dia + 1, days_in_month2 + 1):
                fc_fecha = pd.Timestamp(anio_fc, mes_fc, dia)
                fac = irr_map.get(fc_fecha, 1.0)
                dias_fut = int((fc_fecha - dd_tend["Fecha"].min()).days) if len(dd_tend) >= 5 else 0
                delta_tend = _sl * (dias_fut - _dias_ref)
                dia_sum = 0.0
                for h in range(24):
                    row2 = lp2.loc[h] if h in lp2.index else lp2.iloc[0]
                    x2 = pd.DataFrame([{
                        "lag1": row2["lag1"], "lag2": row2["lag2"],
                        "lag3": row2["lag3"], "lag4": row2["lag4"],
                        "Hora": h, "Mes": mes_fc, "dow": fc_fecha.dayofweek,
                        "rs3": row2["rs3"], "rs6": row2["rs6"], "rm6": row2["rm6"]}])
                    pred_h = max(float(gbm.predict(x2[FEATS])[0]) * ratio2 * fac, 0.0)
                    tend_h = (_sl * (dias_fut - _dias_ref) / 16) if (5 <= h <= 20) else 0.0
                    dia_sum += max(pred_h + tend_h, 0.0)
                fc_d_rows.append({"Fecha": fc_fecha, "Pred": dia_sum})
            fut_d = pd.DataFrame(fc_d_rows)
            tot_fore = float(fut_d["Pred"].sum()) if len(fut_d) else 0

            fig_may = go.Figure()
            if len(real_d):
                fig_may.add_trace(go.Bar(
                    x=real_d["Fecha"], y=real_d["Real"],
                    name=f"Real (1-{ultimo_dia} {MESES[mes_fc]})",
                    marker_color=VERDE_MED,
                    hovertemplate="%{x|%d %b}<br>Real: %{y:.0f} kWh<extra></extra>"))
                fig_may.add_trace(go.Bar(
                    x=real_d["Fecha"], y=real_d["Modelo"],
                    name="GBM Lean (validación)",
                    marker_color="#e53935", opacity=0.55,
                    hovertemplate="%{x|%d %b}<br>Modelo: %{y:.0f} kWh<extra></extra>"))
            if len(fut_d):
                fig_may.add_trace(go.Bar(
                    x=fut_d["Fecha"], y=fut_d["Pred"],
                    name=f"Forecast ({ultimo_dia+1}-{days_in_month2} {MESES[mes_fc]})",
                    marker_color="#e53935",
                    hovertemplate="%{x|%d %b}<br>Forecast: %{y:.0f} kWh<extra></extra>"))
            if prom_real > 0:
                fig_may.add_hline(y=prom_real, line_dash="dash",
                                   line_color=VERDE_MED, line_width=1.8,
                                   annotation_text=f"Prom real: {prom_real:.0f} kWh/día",
                                   annotation_position="top left",
                                   annotation_font=dict(size=10))
            if ultimo_dia > 0 and ultimo_dia < days_in_month2:
                sep2 = pd.Timestamp(anio_fc, mes_fc, ultimo_dia) + pd.Timedelta(hours=12)
                fig_may.add_shape(type="line",
                    x0=sep2, x1=sep2, y0=0, y1=1, yref="paper",
                    line=dict(dash="dot", color="#888", width=1.5))

            fig_may.update_layout(
                title=(f"GBM Lean — Generación diaria {MESES[mes_fc]} {anio_fc}<br>"
                       f"<span style='font-size:10px;color:#777'>"
                       f"Real 1-{ultimo_dia}: {tot_real:.0f} kWh  ·  "
                       f"Forecast {ultimo_dia+1}-{days_in_month2}: {tot_fore:.0f} kWh  ·  "
                       f"Total estimado: {tot_real+tot_fore:.0f} kWh  ·  "
                       f"Ratio: {ratio2:.3f}x</span>"),
                barmode="overlay", hovermode="x",
                legend=dict(orientation="h", yanchor="bottom", y=1.06,
                            xanchor="right", x=1, font=dict(size=10)),
                bargap=0.15)
            fig_may.update_xaxes(showgrid=True, gridcolor="#eee",
                                  tickformat="%d %b", tickangle=-35, dtick="D2")
            fig_may.update_yaxes(showgrid=True, gridcolor="#eee",
                                  title_text="kWh/día", rangemode="tozero")
            chart_style(fig_may, h=460, margin=(10,10,80,10))
            st.plotly_chart(fig_may, use_container_width=True)

            # ── Validación: Real vs Pronóstico vs GBM (si hay reporte del período) ──
            import glob as _glob
            _mes_esp = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",
                        7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
            _mes_key = _mes_esp[mes_fc]
            _yr_str  = str(anio_fc)

            # Buscar archivos Reporte del mes actual (maneja ñ y variantes)
            _rpt_files = [
                os.path.join(DATA, f) for f in os.listdir(DATA)
                if f.lower().startswith("reporte_generacion_ferchegas")
                and _mes_key in f.lower()
                and _yr_str in f
                and f.endswith(".xls")
            ]

            if _rpt_files and len(fut_d) > 0:
                try:
                    _rpt = pd.read_html(_rpt_files[0])[0]
                    _rpt.columns = ["Fecha", "Real_kWh", "Pron_kWh"]
                    _rpt["Fecha"]    = pd.to_datetime(_rpt["Fecha"], errors="coerce")
                    _rpt["Real_kWh"] = pd.to_numeric(_rpt["Real_kWh"], errors="coerce")
                    _rpt["Pron_kWh"] = pd.to_numeric(_rpt["Pron_kWh"], errors="coerce")
                    _rpt = _rpt.dropna(subset=["Fecha", "Real_kWh"]).reset_index(drop=True)

                    # Solo días del período pronosticado que ya tienen real
                    _val = _rpt.merge(
                        fut_d.rename(columns={"Pred": "GBM_kWh"})[["Fecha", "GBM_kWh"]],
                        on="Fecha", how="inner")

                    if len(_val) > 0:
                        _val["Err_Pron"] = _val["Pron_kWh"] - _val["Real_kWh"]
                        _val["Err_GBM"]  = _val["GBM_kWh"]  - _val["Real_kWh"]
                        _val["Mejor"]    = _val.apply(
                            lambda r: "GBM Lean" if abs(r["Err_GBM"]) < abs(r["Err_Pron"])
                                      else "Pronóstico", axis=1)

                        _mape_p = (_val["Err_Pron"].abs() / _val["Real_kWh"] * 100).mean()
                        _mape_g = (_val["Err_GBM"].abs()  / _val["Real_kWh"] * 100).mean()
                        _tot    = {
                            "Real_kWh": _val["Real_kWh"].sum(),
                            "Pron_kWh": _val["Pron_kWh"].sum(),
                            "GBM_kWh":  _val["GBM_kWh"].sum(),
                            "Err_Pron": _val["Err_Pron"].sum(),
                            "Err_GBM":  _val["Err_GBM"].sum(),
                            "Mejor":    "GBM Lean" if abs(_val["Err_GBM"].sum()) <
                                        abs(_val["Err_Pron"].sum()) else "Pronóstico",
                        }

                        st.markdown(
                            f"<div style='margin-top:1.4rem;margin-bottom:0.2rem;"
                            f"font-weight:700;font-size:0.97rem;color:{VERDE};'>"
                            f"Validación — Real vs Pronóstico vs GBM Lean "
                            f"({_val['Fecha'].min().strftime('%d')}"
                            f"–{_val['Fecha'].max().strftime('%d')} "
                            f"{MESES[mes_fc]} {anio_fc})</div>",
                            unsafe_allow_html=True)

                        # ── Tabla ────────────────────────────────────────────
                        def _cell_color(err):
                            a = abs(err)
                            if a < 10:   return "rgba(165,214,167,0.55)"
                            if a < 30:   return "rgba(255,224,178,0.70)"
                            return "rgba(255,205,210,0.80)"

                        _n = len(_val) + 1  # +1 fila total
                        _dias   = [r["Fecha"].strftime("%a %d %b").capitalize()
                                   for _, r in _val.iterrows()] + ["TOTAL"]
                        _reals  = [f"{r['Real_kWh']:.1f}" for _, r in _val.iterrows()] \
                                  + [f"{_tot['Real_kWh']:.1f}"]
                        _prons  = [f"{r['Pron_kWh']:.1f}" for _, r in _val.iterrows()] \
                                  + [f"{_tot['Pron_kWh']:.1f}"]
                        _gbms   = [f"{r['GBM_kWh']:.1f}"  for _, r in _val.iterrows()] \
                                  + [f"{_tot['GBM_kWh']:.1f}"]
                        _ep     = [f"{r['Err_Pron']:+.1f}" for _, r in _val.iterrows()] \
                                  + [f"{_tot['Err_Pron']:+.1f}"]
                        _eg     = [f"{r['Err_GBM']:+.1f}"  for _, r in _val.iterrows()] \
                                  + [f"{_tot['Err_GBM']:+.1f}"]
                        _mejor  = list(_val["Mejor"]) + [_tot["Mejor"]]

                        _c_fecha = [f"rgba(46,125,50,0.10)"] * (_n-1) + ["rgba(46,125,50,0.22)"]
                        _c_real  = ["white"] * (_n-1) + ["rgba(46,125,50,0.12)"]
                        _c_pron  = ["white"] * (_n-1) + ["rgba(46,125,50,0.12)"]
                        _c_gbm   = ["white"] * (_n-1) + ["rgba(46,125,50,0.12)"]
                        _c_ep    = [_cell_color(r["Err_Pron"]) for _, r in _val.iterrows()] \
                                   + [_cell_color(_tot["Err_Pron"])]
                        _c_eg    = [_cell_color(r["Err_GBM"])  for _, r in _val.iterrows()] \
                                   + [_cell_color(_tot["Err_GBM"])]
                        _c_mejor = [
                            "rgba(165,214,167,0.65)" if m == "GBM Lean"
                            else "rgba(255,224,178,0.70)"
                            for m in _mejor]

                        fig_tbl = go.Figure(go.Table(
                            columnwidth=[85, 62, 72, 68, 72, 68, 72],
                            header=dict(
                                values=["<b>Fecha</b>",
                                        "<b>Real<br>(kWh)</b>",
                                        "<b>Pronóstico<br>oficial (kWh)</b>",
                                        "<b>GBM Lean<br>(kWh)</b>",
                                        "<b>Δ Pronóstico<br>(kWh)</b>",
                                        "<b>Δ GBM<br>(kWh)</b>",
                                        "<b>Mejor</b>"],
                                fill_color=VERDE,
                                font=dict(color="white", size=11),
                                align=["left","center","center",
                                       "center","center","center","center"],
                                height=34),
                            cells=dict(
                                values=[_dias, _reals, _prons, _gbms,
                                        _ep, _eg, _mejor],
                                fill_color=[_c_fecha, _c_real, _c_pron, _c_gbm,
                                            _c_ep, _c_eg, _c_mejor],
                                font=dict(color="#111", size=11),
                                align=["left","center","center",
                                       "center","center","center","center"],
                                height=28)))

                        fig_tbl.update_layout(
                            title=(f"<b>Validación {MESES[mes_fc]} {anio_fc}</b>  "
                                   f"<span style='font-size:10px;color:#777'>"
                                   f"Δ = Predicho − Real  ·  "
                                   f"MAPE Pronóstico: {_mape_p:.1f}%  ·  "
                                   f"MAPE GBM Lean: {_mape_g:.1f}%</span>"),
                            height=60 + 28 * _n + 34,
                            margin=dict(l=0, r=0, t=50, b=0))
                        st.plotly_chart(fig_tbl, use_container_width=True)

                        # ── Gráfico barras agrupadas ──────────────────────────
                        fig_val = go.Figure()
                        fig_val.add_trace(go.Bar(
                            x=_val["Fecha"], y=_val["Real_kWh"],
                            name="Real", marker_color=VERDE_MED,
                            hovertemplate="%{x|%d %b}<br>Real: %{y:.1f} kWh<extra></extra>"))
                        fig_val.add_trace(go.Bar(
                            x=_val["Fecha"], y=_val["Pron_kWh"],
                            name="Pronóstico oficial", marker_color="#1565C0", opacity=0.80,
                            hovertemplate="%{x|%d %b}<br>Pronóstico: %{y:.1f} kWh<extra></extra>"))
                        fig_val.add_trace(go.Bar(
                            x=_val["Fecha"], y=_val["GBM_kWh"],
                            name="GBM Lean", marker_color="#e53935", opacity=0.85,
                            hovertemplate="%{x|%d %b}<br>GBM: %{y:.1f} kWh<extra></extra>"))

                        fig_val.update_layout(
                            title=(f"<b>Real vs Pronóstico vs GBM Lean — "
                                   f"{MESES[mes_fc]} {anio_fc}</b><br>"
                                   f"<span style='font-size:10px;color:#777'>"
                                   f"MAPE Pronóstico: {_mape_p:.1f}%  ·  "
                                   f"MAPE GBM Lean: {_mape_g:.1f}%  ·  "
                                   f"GBM ganó {list(_val['Mejor']).count('GBM Lean')}"
                                   f"/{len(_val)} días</span>"),
                            barmode="group", hovermode="x unified",
                            xaxis=dict(tickformat="%a %d %b", showgrid=True,
                                       gridcolor="#eee", tickangle=-30),
                            yaxis=dict(title="kWh/día", rangemode="tozero",
                                       showgrid=True, gridcolor="#eee"),
                            legend=dict(orientation="h", yanchor="bottom", y=1.04,
                                        xanchor="right", x=1, font=dict(size=10)),
                            plot_bgcolor="white")
                        chart_style(fig_val, h=380, margin=(10, 10, 60, 10))
                        st.plotly_chart(fig_val, use_container_width=True)

                except Exception:
                    pass

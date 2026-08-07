"""Dashboard administrativo de control de compras de Barrio Pizza."""

from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.data_loader import DATASET_FILES, load_data_bundle
from src.forecasting import build_baseline_forecast, get_history_with_projection
from src.purchase_analysis import analyze_orders
from src.validations import validate_data

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ASSET_SLOTS = {
    "logo": ASSETS_DIR / "logo_wordmark.png",
    "logo_circle": ASSETS_DIR / "logo_barrio_transparente.png",
    "hero": ASSETS_DIR / "hero_dashboard.png",
    "overview": ASSETS_DIR / "panel_general.png",
    "alerts": ASSETS_DIR / "revision_ordenes.png",
    "corrected": ASSETS_DIR / "pedido_recomendado.png",
    "forecast": ASSETS_DIR / "pronostico.png",
    "quality": ASSETS_DIR / "calidad_datos.png",
}

PAGE_OPTIONS = ["Resumen", "Órdenes", "Recomendado", "Pronóstico", "Datos"]
PAGE_SHORT = {
    "Resumen": "RES",
    "Órdenes": "ORD",
    "Recomendado": "REC",
    "Pronóstico": "PRO",
    "Datos": "DAT",
}
PAGE_SLUG = {
    "Resumen": "resumen",
    "Órdenes": "ordenes",
    "Recomendado": "recomendado",
    "Pronóstico": "pronostico",
    "Datos": "datos",
}
PAGE_FROM_SLUG = {value: key for key, value in PAGE_SLUG.items()}
PAGE_ANCHORS = {page: f"section-{slug}" for page, slug in PAGE_SLUG.items()}
DATA_SUB_OPTIONS = ["Hallazgos", "Fuentes"]
DATA_SUB_SLUG = {"Hallazgos": "hallazgos", "Fuentes": "fuentes"}
DATA_SUB_FROM_SLUG = {value: key for key, value in DATA_SUB_SLUG.items()}

STATUS_LABELS = {
    "DATO_INVALIDO": "Dato inválido",
    "OMITIDO": "Omitido",
    "FALTANTE": "Faltante",
    "SOBREPEDIDO": "Sobrepedido",
    "CORRECTO": "Correcto",
}
STATUS_COLORS = {
    "DATO_INVALIDO": "#171717",
    "OMITIDO": "#A71919",
    "FALTANTE": "#E2372E",
    "SOBREPEDIDO": "#D97706",
    "CORRECTO": "#23825B",
}
PRIORITY_RANK = {"CRÍTICA": 0, "ALTA": 1, "MEDIA": 2, "OK": 3}

st.set_page_config(
    page_title="Barrio Pizza | Centro de compras",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)


def asset_data_uri(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    mime, _ = mimetypes.guess_type(path.name)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime or 'image/png'};base64,{encoded}"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --red:#E2372E;
            --red-dark:#B91C1C;
            --black:#171717;
            --paper:#F7F4EF;
            --white:#FFFFFF;
            --muted:#6D6862;
            --line:rgba(23,23,23,.10);
        }

        .stApp {
            background:linear-gradient(180deg,#FBF9F6 0%,#F2EEE8 100%);
            color:var(--black);
            font-family:'Inter',Segoe UI,Arial,sans-serif;
        }
        .block-container {max-width:1540px;padding-top:1.25rem;padding-bottom:2.5rem;}

        /* SIDEBAR */
        [data-testid="stSidebar"] {
            background:var(--black);
            border-right:1px solid rgba(255,255,255,.08);
            z-index:1000!important;
        }
        [data-testid="stSidebarUserContent"] {padding-top:.35rem!important;}
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {color:#F7F4EF!important;}

        /* Flecha de colapsar: siempre blanca y visible. */
        [data-testid="stSidebar"] button svg,
        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stSidebar"] button [data-testid="stIconMaterial"] {
            color:#FFFFFF!important;
            fill:#FFFFFF!important;
            stroke:#FFFFFF!important;
            opacity:1!important;
            filter:brightness(0) invert(1)!important;
        }
        [data-testid="stSidebar"] button {
            color:#FFFFFF!important;
        }

        .sidebar-logo {
            display:block;
            width:min(100%,122px);
            height:auto;
            margin:-.65rem auto .35rem;
            filter:invert(1);
        }
        .sidebar-kicker {
            color:#FF655B!important;
            font-size:.68rem;
            font-weight:800;
            letter-spacing:.14rem;
            text-transform:uppercase;
            margin:.2rem 0 .55rem;
        }
        .sidebar-help {
            background:#242424;
            border:1px solid rgba(255,255,255,.09);
            border-radius:14px;
            padding:.8rem .85rem;
            margin-top:.8rem;
            color:#F7F4EF!important;
            font-size:.79rem;
            line-height:1.55;
        }
        .sidebar-help strong {color:#FFFFFF!important;}
        .sidebar-stat-row {
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:.45rem;
            margin:.55rem 0 .35rem;
        }
        .sidebar-stat {
            background:#262626;
            border:1px solid rgba(255,255,255,.07);
            border-radius:12px;
            padding:.6rem .5rem;
            text-align:center;
        }
        .sidebar-stat strong {
            display:block;
            font-family:'Bebas Neue','Arial Narrow',sans-serif;
            font-size:1.6rem;
            line-height:1;
            color:white!important;
            font-weight:400;
        }
        .sidebar-stat span {
            display:block;
            font-size:.57rem;
            letter-spacing:.07rem;
            text-transform:uppercase;
            color:#C7C2BC!important;
            margin-top:.2rem;
        }
        .sidebar-stat.alert {background:var(--red);}

        /* Radio de navegación con apariencia de menú. */
        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap:.25rem!important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label {
            background:#222!important;
            border:1px solid rgba(255,255,255,.06)!important;
            border-radius:11px!important;
            padding:.48rem .62rem!important;
            min-height:42px!important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background:#2E2E2E!important;
            border-color:rgba(255,255,255,.15)!important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background:var(--red)!important;
            border-color:var(--red)!important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label p {
            font-weight:800!important;
            letter-spacing:.02rem;
        }

        /* Rail compacta al colapsar. */
        .sidebar-rail {
            position:fixed;left:0;top:76px;width:64px;
            background:#171717;border-radius:0 16px 16px 0;
            padding:.6rem .36rem .65rem;z-index:900;
            box-shadow:0 14px 30px rgba(0,0,0,.22);
            border:1px solid rgba(255,255,255,.08);border-left:0;
            display:flex;flex-direction:column;align-items:center;gap:.42rem;
        }
        .rail-logo {width:42px;height:42px;object-fit:contain;filter:invert(1);display:block;}
        .rail-divider {width:34px;height:1px;background:rgba(255,255,255,.16);margin:.08rem 0;}
        .rail-nav {
            width:47px;height:36px;border-radius:10px;background:#262626;
            display:flex;align-items:center;justify-content:center;
            color:#D9D5CF;font-family:'Bebas Neue','Arial Narrow',sans-serif;
            font-size:.95rem;letter-spacing:.04rem;border:1px solid rgba(255,255,255,.05);text-decoration:none!important;
            cursor:pointer;
        }
        .rail-nav.active {background:var(--red);color:white;}
        .rail-nav:hover {background:#303030;color:#FFFFFF;}
        .rail-alert {
            width:47px;min-height:44px;border-radius:11px;background:#262626;
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            color:white;border:1px solid rgba(255,255,255,.05);
        }
        .rail-alert strong {font-family:'Bebas Neue','Arial Narrow',sans-serif;font-size:1.35rem;font-weight:400;line-height:1;}
        .rail-alert span {font-size:.5rem;letter-spacing:.05rem;text-transform:uppercase;color:#C7C2BC;margin-top:.12rem;}
        .rail-alert.adjust {background:#3A3633;}
        .rail-subnav {
            width:47px;height:31px;border-radius:9px;background:#202020;
            display:flex;align-items:center;justify-content:center;color:#BEB9B2;
            font-family:'Bebas Neue','Arial Narrow',sans-serif;font-size:.78rem;
            letter-spacing:.035rem;text-decoration:none!important;border:1px dashed rgba(255,255,255,.12);
        }
        .rail-subnav:hover {background:#303030;color:#FFFFFF;}
        .rail-subnav.active {background:#FFFFFF;color:#171717;border-style:solid;}
        .sidebar-subnav-title {
            color:#FF655B!important;font-size:.62rem;font-weight:800;letter-spacing:.11rem;
            text-transform:uppercase;margin:.75rem 0 .35rem;
        }
        .sidebar-subnav {display:grid;grid-template-columns:1fr 1fr;gap:.4rem;}
        .sidebar-subnav a {
            display:flex;align-items:center;justify-content:center;min-height:36px;
            border-radius:10px;background:#242424;color:#E9E5DF!important;text-decoration:none!important;
            font-size:.72rem;font-weight:800;border:1px solid rgba(255,255,255,.07);
        }
        .sidebar-subnav a:hover {background:#303030;}
        .sidebar-subnav a.active {background:#FFFFFF;color:#171717!important;}

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            position:fixed!important;left:66px!important;top:90px!important;
            width:44px!important;height:44px!important;
            border-radius:0 13px 13px 0!important;
            background:var(--red)!important;color:white!important;
            box-shadow:0 9px 22px rgba(0,0,0,.25)!important;
            z-index:1100!important;border:0!important;
        }
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="collapsedControl"] svg {
            fill:white!important;color:white!important;stroke:white!important;opacity:1!important;
            width:22px!important;height:22px!important;filter:brightness(0) invert(1)!important;
        }
        [data-testid="stSidebarCollapsedControl"]::after,
        [data-testid="collapsedControl"]::after {
            content:"ABRIR";position:absolute;left:43px;top:9px;
            background:#171717;color:white;padding:.35rem .46rem;border-radius:0 8px 8px 0;
            font-size:.58rem;font-weight:800;letter-spacing:.07rem;
        }

        .location-header {
            position:fixed;top:.58rem;left:50%;transform:translateX(-50%);
            z-index:1000001;pointer-events:none;
            display:flex;align-items:center;gap:.42rem;padding:.38rem .72rem;
            background:rgba(255,253,249,.96);border:1px solid rgba(23,23,23,.10);
            border-radius:999px;box-shadow:0 5px 16px rgba(0,0,0,.07);
            color:#171717;font-size:.72rem;font-weight:800;letter-spacing:.055rem;text-transform:uppercase;
            backdrop-filter:blur(8px);
        }
        .location-header .dot {width:7px;height:7px;border-radius:50%;background:var(--red);display:inline-block;}
        .location-header .sub {color:#6D6862;font-weight:700;}

        /* BRAND TYPOGRAPHY */
        .display-font,.hero-title,.page-head-title,.kpi-value,.chart-title {
            font-family:'Bebas Neue','Arial Narrow',Impact,sans-serif!important;
            font-weight:400!important;letter-spacing:.03rem;
        }
        .hero {
            display:grid;grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr);
            min-height:350px;background:var(--black);border-radius:24px;overflow:hidden;
            box-shadow:0 22px 52px rgba(0,0,0,.17);margin-bottom:1rem;
        }
        .hero-copy {padding:clamp(1.8rem,4vw,3.8rem);display:flex;flex-direction:column;justify-content:center;}
        .hero-logo {width:min(100%,300px);height:auto;display:block;filter:invert(1);margin-bottom:1rem;}
        .eyebrow {color:#FF655B;font-size:.76rem;font-weight:800;letter-spacing:.22rem;text-transform:uppercase;}
        .hero-title {margin:.45rem 0 0;color:white;font-size:clamp(3.2rem,6.4vw,6.2rem);line-height:.88;}
        .hero-title span {color:var(--red);}
        .hero-text {max-width:680px;color:rgba(255,255,255,.76);font-size:1rem;line-height:1.58;margin-top:1rem;}
        .hero-slogan {color:white;font-size:.76rem;font-weight:800;letter-spacing:.22rem;text-transform:uppercase;margin-top:1.15rem;}
        .hero-media {position:relative;min-height:350px;background:#282828;}
        .hero-media::after {content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(23,23,23,.88),rgba(23,23,23,.08));}
        .hero-media img {width:100%;height:100%;min-height:350px;object-fit:cover;display:block;}

        .kpis {display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:.75rem;margin:.8rem 0 1.1rem;}
        .kpi {background:white;border:1px solid var(--line);border-radius:17px;padding:.9rem 1rem;box-shadow:0 8px 22px rgba(0,0,0,.045);min-width:0;}
        .kpi-label {font-size:.70rem;line-height:1.2;font-weight:800;letter-spacing:.04rem;text-transform:uppercase;color:#6B665F;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        .kpi-value {font-size:2.9rem;line-height:1;color:var(--black);margin-top:.32rem;white-space:nowrap;}
        .kpi.accent .kpi-value {color:var(--red);}
        .kpi-note {font-size:.75rem;color:#77716A;margin-top:.35rem;line-height:1.3;}

        .page-head {
            display:grid;grid-template-columns:minmax(0,1fr) 230px;overflow:hidden;
            min-height:145px;background:white;border:1px solid var(--line);border-radius:20px;
            box-shadow:0 9px 25px rgba(0,0,0,.045);margin-bottom:1rem;
        }
        .page-head-copy {padding:1.25rem 1.45rem;display:flex;flex-direction:column;justify-content:center;}
        .page-head-title {font-size:clamp(2.25rem,3.8vw,3.6rem);line-height:.96;color:var(--black);margin:.25rem 0;}
        .page-head-text {font-size:.9rem;line-height:1.5;color:#635E58;max-width:900px;}
        .page-head img {width:100%;height:100%;min-height:145px;object-fit:cover;display:block;}

        .filter-box {
            background:white;border:1px solid var(--line);border-radius:16px;
            padding:.8rem 1rem .25rem;margin:.35rem 0 1rem;
            box-shadow:0 7px 20px rgba(0,0,0,.035);
        }
        .filter-box-title {
            font-family:'Bebas Neue','Arial Narrow',sans-serif;
            font-size:1.25rem;letter-spacing:.04rem;color:var(--black);margin-bottom:.1rem;
        }
        .filter-box-note {font-size:.78rem;color:#756F68;margin-bottom:.4rem;}

        .alerts-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:.7rem;}
        .alert-card {background:white;border:1px solid var(--line);border-left:6px solid var(--red);border-radius:15px;padding:.85rem .9rem;box-shadow:0 7px 18px rgba(0,0,0,.04);min-width:0;}
        .alert-title {font-weight:800;color:var(--black);line-height:1.25;margin:.32rem 0;overflow-wrap:break-word;}
        .alert-text {font-size:.83rem;line-height:1.45;color:#625D57;overflow-wrap:break-word;}
        .badge {display:inline-flex;padding:.23rem .55rem;border-radius:999px;color:white;font-size:.64rem;font-weight:800;text-transform:uppercase;white-space:nowrap;margin-right:.2rem;}

        .priority-card {
            background:white;border:1px solid var(--line);border-left:6px solid var(--red);
            border-radius:15px;padding:.9rem 1rem 1rem;box-shadow:0 7px 18px rgba(0,0,0,.04);
            min-width:0;margin-bottom:.9rem;
        }
        .priority-card .title {font-weight:800;color:#171717;line-height:1.25;margin:.42rem 0 .25rem;}
        .priority-card .text {font-size:.82rem;color:#625D57;line-height:1.45;overflow-wrap:break-word;}
        .priority-card .priority-action {
            display:inline-flex;align-items:center;justify-content:center;
            margin-top:.75rem;padding:.56rem .8rem;border-radius:11px;
            color:#fff!important;text-decoration:none!important;font-size:.76rem;
            font-weight:800;letter-spacing:.02rem;width:100%;box-sizing:border-box;
        }
        .priority-card .priority-action:hover {filter:brightness(.96);}
        .section-mini-title {
            font-family:'Bebas Neue','Arial Narrow',sans-serif;
            font-size:1.7rem;letter-spacing:.04rem;color:var(--black);
            text-align:center;margin:.25rem 0 .15rem;
        }
        .section-mini-caption {
            text-align:center;color:#6E6962;font-size:.82rem;margin-bottom:.25rem;
        }
        .highlight-card {
            background:#FFFDF9;border:1px solid var(--line);border-radius:20px;
            padding:1.2rem 1.15rem;box-shadow:0 7px 18px rgba(0,0,0,.04);
            min-height:410px;display:flex;flex-direction:column;justify-content:center;
        }
        .highlight-card .highlight-value {
            font-family:'Bebas Neue','Arial Narrow',sans-serif;
            font-size:clamp(3rem,5vw,4.4rem);line-height:.9;color:var(--red);margin:.4rem 0 .3rem;
        }
        .highlight-card .highlight-title {
            font-size:1.35rem;font-weight:800;color:var(--black);margin-bottom:.45rem;
        }
        .highlight-card .highlight-text {
            color:#5F5A54;font-size:1rem;line-height:1.55;margin-bottom:1rem;
        }
        .highlight-card .highlight-list {
            display:grid;gap:.5rem;color:#3F3B37;font-size:.96rem;line-height:1.45;
        }

        .stDataFrame,.stPlotlyChart {border-radius:14px;overflow:hidden;}

        @media(max-width:900px){
            .hero {grid-template-columns:1fr;}
            .hero-media,.hero-media img {min-height:230px;max-height:300px;}
            .hero-media::after {background:linear-gradient(180deg,rgba(23,23,23,.08),rgba(23,23,23,.35));}
            .page-head {grid-template-columns:1fr;}
            .page-head img {max-height:210px;}
        }
        @media(max-width:640px){
            .block-container {padding-left:.7rem;padding-right:.7rem;}
            .hero-copy {padding:1.5rem 1.2rem;}
            .hero {border-radius:18px;}
            .kpis {grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem;}
            .kpi {padding:.75rem;}
            .kpi-label {font-size:.61rem;letter-spacing:.02rem;}
            .kpi-value {font-size:2.35rem;}
            .kpi-note {display:none;}
            .sidebar-rail {width:56px;}
            [data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"]{left:58px!important;}
            .location-header {font-size:.62rem;top:.55rem;max-width:58vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_logo() -> None:
    uri = asset_data_uri(ASSET_SLOTS["logo_circle"])
    if uri:
        st.markdown(
            f'<img class="sidebar-logo" src="{uri}" alt="Logo Barrio Pizza">',
            unsafe_allow_html=True,
        )


def build_query_href(
    page: str,
    *,
    branch: str | None = None,
    line: int | None = None,
    scroll_target: str | None = None,
    data_sub: str | None = None,
) -> str:
    params: dict[str, str] = {"page": PAGE_SLUG[page]}
    if branch:
        params["branch"] = branch
    if line is not None:
        params["line"] = str(line)
    if scroll_target:
        params["scroll"] = scroll_target
    if data_sub:
        params["sub"] = DATA_SUB_SLUG[data_sub]
    return "?" + urlencode(params)


def set_query_navigation(
    page: str,
    *,
    branch: str | None = None,
    line: int | None = None,
    scroll_target: str | None = None,
    data_sub: str | None = None,
) -> None:
    st.query_params.clear()
    st.query_params["page"] = PAGE_SLUG[page]
    if branch:
        st.query_params["branch"] = branch
    if line is not None:
        st.query_params["line"] = str(line)
    if scroll_target:
        st.query_params["scroll"] = scroll_target
    if data_sub:
        st.query_params["sub"] = DATA_SUB_SLUG[data_sub]


def emit_scroll_to(target_id: str) -> None:
    components.html(
        f"""
        <script>
        (() => {{
            let attempts = 0;
            const targetId = {target_id!r};
            const timer = setInterval(() => {{
                const doc = window.parent.document;
                const target = doc.getElementById(targetId);
                if (target) {{
                    target.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                    clearInterval(timer);
                }}
                attempts += 1;
                if (attempts > 40) clearInterval(timer);
            }}, 140);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def emit_scroll_to_bottom() -> None:
    components.html(
        """
        <script>
        (() => {
            const goToEnd = () => {
                const doc = window.parent.document;
                const target = doc.getElementById('orders-page-end');
                if (target) {
                    target.scrollIntoView({behavior: 'smooth', block: 'end'});
                    return;
                }

                const scrollHost =
                    doc.querySelector('[data-testid="stAppViewContainer"]') ||
                    doc.querySelector('[data-testid="stMain"]') ||
                    doc.scrollingElement ||
                    doc.documentElement;

                if (scrollHost) {
                    scrollHost.scrollTo({top: scrollHost.scrollHeight, behavior: 'smooth'});
                }
            };

            // Streamlit termina de montar tablas, KPIs y componentes de forma asíncrona.
            // Repetimos el salto para que el último intento ocurra cuando toda la vista ya esté cargada.
            [650, 1200, 1900, 2800, 3800].forEach(delay => setTimeout(goToEnd, delay));
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def render_location_header(current_page: str, data_view: str) -> None:
    subsection = f'<span class="sub">/ {html.escape(data_view)}</span>' if current_page == "Datos" else ""
    st.markdown(
        f'<div class="location-header"><span class="dot"></span>Barrio Pizza · {html.escape(current_page)} {subsection}</div>',
        unsafe_allow_html=True,
    )


def render_collapsed_rail(
    current_page: str,
    alert_count: int,
    actionable_count: int,
    data_view: str,
) -> None:
    logo = asset_data_uri(ASSET_SLOTS["logo_circle"])
    logo_html = f'<img class="rail-logo" src="{logo}" alt="Barrio Pizza">' if logo else ""
    nav_parts: list[str] = []
    for page in PAGE_OPTIONS:
        scroll = None if page == "Resumen" else PAGE_ANCHORS[page]
        nav_parts.append(
            f'<a class="rail-nav{" active" if page == current_page else ""}" '
            f'href="{build_query_href(page, scroll_target=scroll)}" target="_self" title="{page}">{PAGE_SHORT[page]}</a>'
        )
        if page == "Datos":
            for sub in DATA_SUB_OPTIONS:
                active = current_page == "Datos" and data_view == sub
                nav_parts.append(
                    f'<a class="rail-subnav{" active" if active else ""}" '
                    f'href="{build_query_href("Datos", scroll_target=PAGE_ANCHORS["Datos"], data_sub=sub)}" '
                    f'target="_self" title="Datos · {sub}">{"HAL" if sub == "Hallazgos" else "FUE"}</a>'
                )
    nav = "".join(nav_parts)
    st.markdown(
        f"""
        <aside class="sidebar-rail" aria-label="Navegación compacta">
            {logo_html}
            <div class="rail-divider"></div>
            {nav}
            <div class="rail-divider"></div>
            <div class="rail-alert" title="Alertas detectadas"><strong>{alert_count}</strong><span>Alertas</span></div>
            <div class="rail-alert adjust" title="Ajustes de compra"><strong>{actionable_count}</strong><span>Ajustes</span></div>
        </aside>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    logo = asset_data_uri(ASSET_SLOTS["logo"])
    image = asset_data_uri(ASSET_SLOTS["hero"])
    logo_html = f'<img class="hero-logo" src="{logo}" alt="Barrio Pizza">' if logo else ""
    image_html = f'<img src="{image}" alt="Barrio Pizza">' if image else ""
    st.markdown(
        f"""
        <section class="hero">
          <div class="hero-copy">
            {logo_html}
            <div class="eyebrow">Centro de abastecimiento</div>
            <h1 class="hero-title">CONTROL DE <span>COMPRAS</span></h1>
            <div class="hero-text">Supervisa las órdenes semanales, atiende incidencias y descarga una recomendación lista para revisión administrativa.</div>
            <div class="hero-slogan">DEL BARRIO · PARA EL BARRIO · CON DATA</div>
          </div>
          <div class="hero-media">{image_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_page_head(title: str, text: str, slot: str, eyebrow: str) -> None:
    uri = asset_data_uri(ASSET_SLOTS[slot])
    image = f'<img src="{uri}" alt="{html.escape(title)}">' if uri else ""
    st.markdown(
        f"""
        <section class="page-head">
          <div class="page-head-copy">
            <div class="eyebrow">{html.escape(eyebrow)}</div>
            <div class="page-head-title">{html.escape(title)}</div>
            <div class="page-head-text">{html.escape(text)}</div>
          </div>
          {image}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(items: list[tuple[str, str, str, bool]]) -> None:
    cards = []
    for label, value, note, accent in items:
        cards.append(
            f'<div class="kpi{" accent" if accent else ""}">'
            f'<div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div>'
            f'<div class="kpi-note">{html.escape(note)}</div></div>'
        )
    st.markdown('<div class="kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def safe_text(value: object, fallback: str) -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return text or fallback


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def build_hallazgos_display() -> pd.DataFrame:
    dataset_labels = {
        "ingredientes": "Ingredientes",
        "consumo_historico": "Consumo histórico",
        "inventario_actual": "Inventario actual",
        "orden_compra": "Orden de compra",
    }
    rows: list[dict[str, object]] = []

    for issue in report.issues:
        message = issue.message

        if issue.code == "INGREDIENTE_DESCONOCIDO" and not analysis.empty:
            invalid = analysis.loc[analysis["estado"].eq("DATO_INVALIDO")]
            if not invalid.empty:
                row = invalid.iloc[0]
                message = (
                    f"La orden de {row['sucursal']} incluye el ingrediente '{row['ingrediente_id']}', "
                    "pero no existe en el catálogo maestro. Debe registrarse o corregirse antes de aprobar la compra."
                )

        elif issue.code == "LINEA_ORDEN_OMITIDA" and not analysis.empty:
            omitted = analysis.loc[analysis["estado"].eq("OMITIDO")]
            if not omitted.empty:
                row = omitted.iloc[0]
                unit = safe_text(row.get("unidad_base"), "unidad")
                current_stock = row.get("inventario_actual")
                projected = row.get("consumo_proyectado")
                recommended = row.get("formatos_recomendados")
                purchase_format = safe_text(row.get("formato_compra"), "formato de compra")
                stock_text = "sin stock válido" if pd.isna(current_stock) else f"{current_stock:.2f} {unit}"
                projected_text = "sin pronóstico válido" if pd.isna(projected) else f"{projected:.2f} {unit}"
                recommended_text = "revisar la cantidad" if pd.isna(recommended) else f"agregar {int(recommended)} formato(s) de {purchase_format}"
                message = (
                    f"Se omitió la orden de {safe_text(row.get('nombre'), row.get('ingrediente_id'))} para {row['sucursal']}. "
                    f"El producto presenta consumo histórico y el stock actual ({stock_text}) no cubre el consumo proyectado "
                    f"({projected_text}); se recomienda {recommended_text}."
                )

        elif issue.examples:
            message = f"{message} Contexto detectado: {issue.examples[0]}."

        rows.append(
            {
                "Nivel": "Error" if issue.severity == "ERROR" else "Advertencia",
                "Código": issue.code,
                "Archivo": dataset_labels.get(issue.dataset, issue.dataset),
                "Filas afectadas": issue.row_count,
                "Mensaje": message,
            }
        )

    return pd.DataFrame(rows, columns=["Nivel", "Código", "Archivo", "Filas afectadas", "Mensaje"])


def set_page_from_sidebar() -> None:
    selected_page = st.session_state["_nav_selector"]
    st.session_state["nav_page"] = selected_page
    st.session_state["_pending_scroll_target"] = None
    scroll = None if selected_page == "Resumen" else PAGE_ANCHORS[selected_page]
    data_sub = st.session_state.get("data_view", "Hallazgos") if selected_page == "Datos" else None
    set_query_navigation(selected_page, scroll_target=scroll, data_sub=data_sub)


def render_clickable_priorities(frame: pd.DataFrame, limit: int = 8) -> None:
    if frame.empty:
        st.success("No hay incidencias para revisar con los filtros actuales.")
        return

    work = frame.copy()
    work["_rank"] = work["prioridad"].map(PRIORITY_RANK).fillna(99)
    work = work.sort_values(["_rank", "sucursal", "nombre"]).head(limit)
    records = list(work.iterrows())

    for start in range(0, len(records), 2):
        cols = st.columns(2, gap="medium")
        for col, (index, row) in zip(cols, records[start : start + 2]):
            with col:
                color = STATUS_COLORS.get(row["estado"], "#171717")
                href = build_query_href("Órdenes", branch=str(row["sucursal"]), line=int(index), scroll_target="orders-bottom")
                provider = safe_text(row.get("proveedor"), "Sin proveedor")
                st.markdown(
                    f"""
                    <div class="priority-card" style="border-left-color:{color}">
                        <span class="badge" style="background:{color}">{html.escape(STATUS_LABELS.get(row['estado'], row['estado']))}</span>
                        <span class="badge" style="background:#4A4642">{html.escape(str(row['prioridad']))}</span>
                        <div class="title">{html.escape(str(row['sucursal']))} · {html.escape(str(row['nombre']))}</div>
                        <div class="text"><strong>{html.escape(provider)}</strong><br>{html.escape(str(row['accion_recomendada']))}</div>
                        <a class="priority-action" style="background:{color}" href="{href}" target="_self">Revisar en Órdenes →</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def make_donut(
    labels: pd.Series,
    values: pd.Series,
    colors: list[str],
    *,
    title: str = "",
    center_label: str,
    height: int = 500,
) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=.62,
            marker={"colors": colors, "line": {"color": "#FBF9F6", "width": 3}},
            textinfo="label+value",
            textposition="outside",
            sort=False,
            hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            domain={"x": [0.10, 0.90], "y": [0.12, 0.88]},
            automargin=True,
            textfont={"size": 14, "color": "#6E7587"},
        )
    )
    fig.add_annotation(
        text=f"<b>{int(values.sum())}</b><br><span style='font-size:12px'>{center_label}</span>",
        x=.5,
        y=.5,
        showarrow=False,
        font={"family": "Bebas Neue, Arial Narrow, sans-serif", "size": 28, "color": "#171717"},
    )
    layout_kwargs = {
        "height": height,
        "margin": {"l": 85, "r": 85, "t": 90 if title else 55, "b": 55},
        "showlegend": False,
        "paper_bgcolor": "rgba(0,0,0,0)",
    }
    if title:
        layout_kwargs["title"] = title
    fig.update_layout(**layout_kwargs)
    return fig


inject_css()

try:
    data = load_data_bundle()
except (FileNotFoundError, ValueError) as exc:
    st.error("No fue posible cargar los archivos operativos.")
    st.code(str(exc), language="text")
    st.code("python scripts/download_data.py\npython -m streamlit run app.py", language="powershell")
    st.stop()

report = validate_data(data)
forecast = None
purchase_result = None
if not report.has_errors:
    forecast = build_baseline_forecast(report.cleaned_data)
    purchase_result = analyze_orders(report.cleaned_data, forecast)

analysis = purchase_result.analysis.copy() if purchase_result is not None else pd.DataFrame()
corrected_order = purchase_result.corrected_order() if purchase_result is not None else pd.DataFrame()
supplier_summary = purchase_result.supplier_summary() if purchase_result is not None else pd.DataFrame()

requested_page = PAGE_FROM_SLUG.get(str(st.query_params.get("page", "")).strip().lower())
if requested_page:
    st.session_state["nav_page"] = requested_page
elif "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Resumen"
    set_query_navigation("Resumen")

requested_branch = st.query_params.get("branch")
requested_line = st.query_params.get("line")
requested_scroll = st.query_params.get("scroll")
if st.session_state.get("nav_page") == "Resumen":
    requested_scroll = None
    st.session_state["_pending_scroll_target"] = None
requested_sub = DATA_SUB_FROM_SLUG.get(str(st.query_params.get("sub", "")).strip().lower())
if requested_sub:
    st.session_state["data_view"] = requested_sub
elif "data_view" not in st.session_state:
    st.session_state["data_view"] = "Hallazgos"
arrived_from_priority = False

# Los parámetros branch/line son una instrucción de llegada, no un estado permanente.
# Se consumen una sola vez para que los selectores vuelvan a quedar libres después.
if requested_branch:
    st.session_state["order_detail_branch"] = str(requested_branch)
    arrived_from_priority = True
if requested_line not in (None, ""):
    try:
        st.session_state["order_detail_line"] = int(str(requested_line))
        arrived_from_priority = True
    except ValueError:
        pass

# Una prioridad siempre debe terminar al final de Órdenes, aunque el parámetro
# de scroll se pierda durante un rerun de Streamlit.
if arrived_from_priority:
    st.session_state["_scroll_orders_bottom_once"] = True

if requested_scroll:
    st.session_state["_pending_scroll_target"] = str(requested_scroll)

if arrived_from_priority or requested_scroll:
    st.query_params.clear()
    st.query_params["page"] = PAGE_SLUG[st.session_state["nav_page"]]

st.session_state["_nav_selector"] = st.session_state["nav_page"]
scroll_target = st.session_state.get("_pending_scroll_target")
current_page = st.session_state["nav_page"]
data_view = st.session_state["data_view"]

alerts_count = 0 if purchase_result is None else purchase_result.alert_count
actionable_count = 0 if purchase_result is None else purchase_result.actionable_count

with st.sidebar:
    render_sidebar_logo()
    st.markdown('<div class="sidebar-kicker">Acceso rápido</div>', unsafe_allow_html=True)
    st.radio(
        "Navegación",
        PAGE_OPTIONS,
        key="_nav_selector",
        on_change=set_page_from_sidebar,
        label_visibility="collapsed",
    )
    sub_links = "".join(
        f'<a class="{"active" if current_page == "Datos" and data_view == sub else ""}" '
        f'href="{build_query_href("Datos", scroll_target=PAGE_ANCHORS["Datos"], data_sub=sub)}" target="_self">{sub}</a>'
        for sub in DATA_SUB_OPTIONS
    )
    st.markdown(
        '<div class="sidebar-subnav-title">Dentro de Datos</div>'
        f'<div class="sidebar-subnav">{sub_links}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="sidebar-stat-row">
            <div class="sidebar-stat alert"><strong>{alerts_count}</strong><span>Alertas</span></div>
            <div class="sidebar-stat"><strong>{actionable_count}</strong><span>Ajustes</span></div>
        </div>
        <div class="sidebar-help">
            <strong>Cómo usar el dashboard</strong><br>
            Elige una vista arriba. Los filtros aparecen dentro de la sección donde son necesarios.
            Desde <strong>Resumen</strong> puedes abrir una prioridad directamente en <strong>Órdenes</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )

render_collapsed_rail(current_page, alerts_count, actionable_count, data_view)
render_location_header(current_page, data_view)

# -----------------------------------------------------------------------------
# RESUMEN
# -----------------------------------------------------------------------------
if current_page == "Resumen":
    st.markdown(f'<div id="{PAGE_ANCHORS["Resumen"]}" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
    render_hero()

    if report.has_errors:
        st.error("Existen errores que bloquean el cálculo. Revisa la vista Datos.")
    elif report.warnings:
        st.warning("El análisis está disponible, pero existen advertencias para validar.")
    else:
        st.success("La información está lista para revisión.")

    render_kpis([
        ("Archivos", str(len(DATASET_FILES)), "Fuentes cargadas", False),
        ("Registros", str(data.total_rows), "Filas procesadas", False),
        ("Errores", str(len(report.errors)), "Bloquean cálculos", bool(report.errors)),
        ("Avisos", str(len(report.warnings)), "Requieren revisión", False),
        ("Alertas", str(alerts_count), "Líneas no correctas", alerts_count > 0),
        ("Ajustes", str(actionable_count), "Cambios de compra", actionable_count > 0),
    ])

    render_page_head(
        "SI HAY DATOS, HAY CONTROL",
        "Visualiza el estado de las órdenes y prioriza las sucursales que requieren intervención antes de aprobar la compra semanal.",
        "overview",
        "Supervisión administrativa",
    )
    if purchase_result is None:
        st.info("El resumen se habilitará cuando los errores estén corregidos.")
    else:
        branch_options = sorted(analysis["sucursal"].dropna().unique().tolist())
        status_options = ["DATO_INVALIDO", "OMITIDO", "FALTANTE", "SOBREPEDIDO", "CORRECTO"]

        st.markdown(
            '<div class="filter-box"><div class="filter-box-title">FILTRAR RESUMEN</div>'
            '<div class="filter-box-note">Los indicadores visuales y las prioridades se actualizan con esta selección.</div></div>',
            unsafe_allow_html=True,
        )
        f1, f2 = st.columns([1, 1.35])
        with f1:
            summary_branch = st.selectbox(
                "Sucursal",
                ["Todas las sucursales", *branch_options],
                key="summary_branch",
            )
        with f2:
            summary_statuses = st.multiselect(
                "Estado",
                status_options,
                default=status_options,
                format_func=lambda value: STATUS_LABELS.get(value, value),
                key="summary_statuses",
            )

        summary_view = analysis.copy()
        if summary_branch != "Todas las sucursales":
            summary_view = summary_view.loc[summary_view["sucursal"].eq(summary_branch)]
        summary_view = summary_view.loc[summary_view["estado"].isin(summary_statuses)]

        if summary_view.empty:
            st.info("No hay líneas para la combinación de filtros seleccionada.")
        else:
            status_frame = (
                summary_view.groupby("estado", dropna=False)
                .size()
                .reset_index(name="lineas")
            )
            status_frame["etiqueta"] = status_frame["estado"].map(STATUS_LABELS)
            status_frame["color"] = status_frame["estado"].map(STATUS_COLORS)
            chart_title = (
                "Estado general · todas las sucursales"
                if summary_branch == "Todas las sucursales"
                else f"Estado general · {summary_branch}"
            )
            center_col = st.columns([.14, .72, .14])[1]
            with center_col:
                st.markdown(f'<div class="section-mini-title">{html.escape(chart_title)}</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-mini-caption">Distribución de líneas según los filtros activos.</div>', unsafe_allow_html=True)
                donut = make_donut(
                    status_frame["etiqueta"],
                    status_frame["lineas"],
                    status_frame["color"].tolist(),
                    center_label="líneas",
                    height=560,
                )
                st.plotly_chart(donut, use_container_width=True)

            st.subheader("Prioridades de revisión")
            priority_view = summary_view.loc[~summary_view["estado"].eq("CORRECTO")]
            render_clickable_priorities(priority_view)

# -----------------------------------------------------------------------------
# ÓRDENES
# -----------------------------------------------------------------------------
elif current_page == "Órdenes":
    st.markdown(f'<div id="{PAGE_ANCHORS["Órdenes"]}" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
    render_page_head(
        "QUE NO FALTE NADA",
        "Compara pedido, necesidad e inventario. La acción recomendada indica si debes aprobar, aumentar, reducir o agregar una línea.",
        "alerts",
        "Control de excepciones",
    )
    if scroll_target == PAGE_ANCHORS["Órdenes"]:
        emit_scroll_to(PAGE_ANCHORS["Órdenes"])
        st.session_state["_pending_scroll_target"] = None

    if purchase_result is None:
        st.error("No es posible revisar órdenes mientras existan errores bloqueantes.")
    elif analysis.empty:
        st.info("No hay líneas para revisar.")
    else:
        branch_options = sorted(analysis["sucursal"].dropna().unique().tolist())
        provider_options = sorted(analysis["proveedor"].dropna().unique().tolist())
        status_options = ["DATO_INVALIDO", "OMITIDO", "FALTANTE", "SOBREPEDIDO", "CORRECTO"]

        st.markdown(
            '<div class="filter-box"><div class="filter-box-title">FILTRAR TABLA DE ÓRDENES</div>'
            '<div class="filter-box-note">Usa estos filtros para reducir la tabla antes de revisar una línea específica.</div></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            table_branch = st.selectbox(
                "Sucursal",
                ["Todas las sucursales", *branch_options],
                key="orders_table_branch",
            )
        with c2:
            table_statuses = st.multiselect(
                "Estado",
                status_options,
                default=status_options,
                format_func=lambda value: STATUS_LABELS.get(value, value),
                key="orders_table_statuses",
            )
        with c3:
            table_provider = st.selectbox(
                "Proveedor",
                ["Todos los proveedores", *provider_options],
                key="orders_table_provider",
            )

        table_view = analysis.copy()
        if table_branch != "Todas las sucursales":
            table_view = table_view.loc[table_view["sucursal"].eq(table_branch)]
        if table_provider != "Todos los proveedores":
            table_view = table_view.loc[table_view["proveedor"].eq(table_provider)]
        table_view = table_view.loc[table_view["estado"].isin(table_statuses)]

        if table_view.empty:
            st.info("No hay líneas para los filtros seleccionados.")
        else:
            display = table_view.rename(columns={
                "prioridad":"Prioridad","estado":"Estado","sucursal":"Sucursal","nombre":"Ingrediente",
                "proveedor":"Proveedor","consumo_proyectado":"Pronóstico","inventario_actual":"Inventario",
                "necesidad_real":"Necesidad","formatos_solicitados":"Pedido",
                "formatos_recomendados":"Recomendado","formato_compra":"Formato","accion_recomendada":"Acción",
            })
            st.dataframe(
                display[["Prioridad","Estado","Sucursal","Ingrediente","Proveedor","Pronóstico","Inventario","Necesidad","Pedido","Recomendado","Formato","Acción"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Pronóstico":st.column_config.NumberColumn(format="%.2f"),
                    "Inventario":st.column_config.NumberColumn(format="%.2f"),
                    "Necesidad":st.column_config.NumberColumn(format="%.2f"),
                    "Pedido":st.column_config.NumberColumn(format="%.0f"),
                    "Recomendado":st.column_config.NumberColumn(format="%.0f"),
                },
            )

        st.divider()
        st.markdown('<div id="detalle-linea" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
        st.subheader("Detalle de línea")
        st.caption("Selecciona primero la sucursal y luego la línea que quieres revisar.")

        # Si llegamos desde una tarjeta de prioridad, conservamos la sucursal y la línea.
        default_branch = st.session_state.get("order_detail_branch")
        if default_branch not in branch_options:
            default_branch = branch_options[0]
            st.session_state["order_detail_branch"] = default_branch

        detail_cols = st.columns([1, 1.7])
        with detail_cols[0]:
            detail_branch = st.selectbox(
                "Sucursal para detalle",
                branch_options,
                key="order_detail_branch",
            )

        detail_options = analysis.loc[analysis["sucursal"].eq(detail_branch)].index.tolist()
        desired_line = st.session_state.get("order_detail_line")
        if desired_line not in detail_options:
            st.session_state["order_detail_line"] = detail_options[0]

        with detail_cols[1]:
            selected_index = st.selectbox(
                "Línea de pedido",
                detail_options,
                format_func=lambda i: (
                    f"{analysis.loc[i,'nombre']} · "
                    f"{STATUS_LABELS.get(analysis.loc[i,'estado'], analysis.loc[i,'estado'])} · "
                    f"{safe_text(analysis.loc[i,'proveedor'], 'Sin proveedor')}"
                ),
                key="order_detail_line",
            )

        detail = analysis.loc[selected_index]
        render_kpis([
            ("Pronóstico", "—" if pd.isna(detail["consumo_proyectado"]) else f"{detail['consumo_proyectado']:.2f}", safe_text(detail.get("unidad_base"),"Unidad"), False),
            ("Inventario", "—" if pd.isna(detail["inventario_actual"]) else f"{detail['inventario_actual']:.2f}", safe_text(detail.get("unidad_base"),"Unidad"), False),
            ("Necesidad", "—" if pd.isna(detail["necesidad_real"]) else f"{detail['necesidad_real']:.2f}", safe_text(detail.get("unidad_base"),"Unidad"), False),
            ("Recomendado", "—" if pd.isna(detail["formatos_recomendados"]) else str(int(detail["formatos_recomendados"])), safe_text(detail.get("formato_compra"),"Formato"), True),
        ])
        message = detail["mensaje"]
        if detail["estado"] == "CORRECTO":
            st.success(message)
        elif detail["estado"] == "SOBREPEDIDO":
            st.warning(message)
        else:
            st.error(message)

        with st.expander("Trazabilidad del cálculo"):
            if detail["estado"] == "DATO_INVALIDO":
                st.write("No hay trazabilidad numérica hasta corregir los datos.")
            else:
                st.code(
                    f"necesidad = max({detail['consumo_proyectado']:.2f} - {detail['inventario_actual']:.2f}, 0)\n"
                    f"necesidad = {detail['necesidad_real']:.2f} {detail['unidad_base']}\n\n"
                    f"formatos recomendados = ceil({detail['necesidad_real']:.2f} / {detail['unidad_base_por_formato']:.2f})\n"
                    f"formatos recomendados = {int(detail['formatos_recomendados'])}",
                    language="text",
                )

        st.markdown('<div id="orders-page-end" style="height:1px;"></div>', unsafe_allow_html=True)

        if scroll_target == "orders-bottom" or st.session_state.pop("_scroll_orders_bottom_once", False):
            emit_scroll_to_bottom()
            st.session_state["_pending_scroll_target"] = None

# -----------------------------------------------------------------------------
# RECOMENDADO — se conserva la composición aprobada.
# -----------------------------------------------------------------------------
elif current_page == "Recomendado":
    st.markdown(f'<div id="{PAGE_ANCHORS["Recomendado"]}" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
    render_page_head(
        "PIDE LO JUSTO",
        "Revisa los formatos corregidos y exporta la propuesta para aprobación o distribución por proveedor.",
        "corrected",
        "Preparación de compra",
    )
    if scroll_target == PAGE_ANCHORS["Recomendado"]:
        emit_scroll_to(PAGE_ANCHORS["Recomendado"])
        st.session_state["_pending_scroll_target"] = None
    if purchase_result is None:
        st.error("No se puede generar la recomendación mientras existan errores bloqueantes.")
    elif corrected_order.empty:
        st.info("No hay líneas recomendadas.")
    else:
        corrected_filtered = corrected_order.copy()
        supplier_filtered = supplier_summary.copy()
        current_total = float(corrected_filtered["formatos_solicitados"].fillna(0).sum())
        recommended_total = float(corrected_filtered["formatos_recomendados"].fillna(0).sum())
        render_kpis([
            ("Actual", f"{current_total:.0f}", "Formatos solicitados", False),
            ("Recomendado", f"{recommended_total:.0f}", "Formatos corregidos", True),
            ("Ajuste", f"{recommended_total-current_total:+.0f}", "Diferencia neta", recommended_total != current_total),
            ("Líneas", str(int(corrected_filtered["ajuste_formatos"].fillna(0).ne(0).sum())), "Con modificación", True),
        ])

        chart_left, chart_right = st.columns([.9, 1.1], gap="large")
        with chart_left:
            adjustment = corrected_filtered.copy()
            adjustment["tipo_ajuste"] = "Sin cambio"
            adjustment.loc[adjustment["ajuste_formatos"].fillna(0).gt(0), "tipo_ajuste"] = "Aumentar"
            adjustment.loc[adjustment["ajuste_formatos"].fillna(0).lt(0), "tipo_ajuste"] = "Reducir"
            adjustment_mix = adjustment.groupby("tipo_ajuste").size().reset_index(name="lineas")
            adjustment_colors = {"Aumentar":"#E2372E","Reducir":"#171717","Sin cambio":"#AAA39B"}
            donut_adj = go.Figure(
                go.Pie(
                    labels=adjustment_mix["tipo_ajuste"],
                    values=adjustment_mix["lineas"],
                    hole=.60,
                    marker={"colors":[adjustment_colors.get(v,"#AAA39B") for v in adjustment_mix["tipo_ajuste"]],
                            "line":{"color":"#FBF9F6","width":3}},
                    textinfo="label+value",textposition="outside",sort=False,
                    hovertemplate="%{label}: %{value} líneas<extra></extra>",
                )
            )
            donut_adj.add_annotation(
                text=f"<b>{len(adjustment)}</b><br><span style='font-size:12px'>líneas</span>",
                x=.5,y=.5,showarrow=False,
                font={"family":"Bebas Neue, Arial Narrow, sans-serif","size":25,"color":"#171717"},
            )
            donut_adj.update_layout(
                title="Tipo de ajuste",height=420,showlegend=False,
                margin={"l":45,"r":45,"t":60,"b":35},paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(donut_adj,use_container_width=True)

        with chart_right:
            if supplier_filtered.empty:
                st.info("No hay resumen por proveedor.")
            else:
                totals = (
                    supplier_filtered.groupby("proveedor")[["formatos_actuales","formatos_recomendados"]]
                    .sum()
                    .reset_index()
                )
                long = totals.melt(
                    id_vars="proveedor",
                    value_vars=["formatos_actuales","formatos_recomendados"],
                    var_name="serie",value_name="formatos",
                )
                long["serie"] = long["serie"].map({"formatos_actuales":"Actual","formatos_recomendados":"Recomendado"})
                fig = px.bar(
                    long,x="formatos",y="proveedor",color="serie",orientation="h",barmode="group",
                    text_auto=".0f",color_discrete_map={"Actual":"#AAA39B","Recomendado":"#E2372E"},
                )
                fig.update_layout(
                    title="Actual vs recomendado por proveedor",height=420,
                    xaxis_title="Formatos",yaxis_title="",legend_title="",
                    margin={"l":20,"r":30,"t":60,"b":35},paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,.9)",bargap=.28,bargroupgap=.08,
                )
                fig.update_xaxes(gridcolor="rgba(23,23,23,.08)")
                fig.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig,use_container_width=True)

        st.subheader("Detalle del pedido recomendado")
        display = corrected_filtered.rename(columns={
            "sucursal":"Sucursal","proveedor":"Proveedor","nombre":"Ingrediente","formato_compra":"Formato",
            "formatos_solicitados":"Pedido","formatos_recomendados":"Recomendado","ajuste_formatos":"Ajuste",
            "estado":"Estado","accion_recomendada":"Acción",
        })
        st.dataframe(
            display[["Sucursal","Proveedor","Ingrediente","Formato","Pedido","Recomendado","Ajuste","Estado","Acción"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pedido":st.column_config.NumberColumn(format="%.0f"),
                "Recomendado":st.column_config.NumberColumn(format="%.0f"),
                "Ajuste":st.column_config.NumberColumn(format="%+.0f"),
            },
        )

        with st.expander("Resumen por proveedor y sucursal"):
            if supplier_filtered.empty:
                st.info("No hay resumen por proveedor.")
            else:
                st.dataframe(supplier_filtered, use_container_width=True, hide_index=True)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Descargar pedido",
                csv_bytes(corrected_filtered),
                "barrio_pedido_recomendado.csv",
                "text/csv",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Descargar por proveedor",
                csv_bytes(supplier_filtered),
                "barrio_resumen_proveedores.csv",
                "text/csv",
                use_container_width=True,
            )

# -----------------------------------------------------------------------------
# PRONÓSTICO — se conserva el diseño aprobado; filtros propios de la vista.
# -----------------------------------------------------------------------------
elif current_page == "Pronóstico":
    st.markdown(f'<div id="{PAGE_ANCHORS["Pronóstico"]}" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
    render_page_head(
        "ANTES DE QUE FALTE",
        "Consulta el consumo esperado por sucursal e ingrediente antes de aprobar la recomendación de compra.",
        "forecast",
        "Planeación de demanda",
    )
    if scroll_target == PAGE_ANCHORS["Pronóstico"]:
        emit_scroll_to(PAGE_ANCHORS["Pronóstico"])
        st.session_state["_pending_scroll_target"] = None
    if forecast is None:
        st.error("El pronóstico no está disponible.")
    else:
        projections = forecast.projections.copy()
        if projections.empty:
            st.info("No hay pronósticos disponibles.")
        else:
            display = projections.rename(columns={
                "sucursal":"Sucursal","nombre":"Ingrediente","proveedor":"Proveedor","unidad_base":"Unidad",
                "semanas_disponibles":"Semanas","consumo_minimo":"Mínimo","consumo_maximo":"Máximo",
                "consumo_promedio":"Promedio","consumo_proyectado":"Pronóstico","historico_completo":"Completo",
            })
            st.dataframe(
                display[["Sucursal","Ingrediente","Proveedor","Unidad","Semanas","Mínimo","Máximo","Promedio","Pronóstico","Completo"]],
                use_container_width=True,
                hide_index=True,
            )
            c1, c2 = st.columns(2)
            branches = sorted(projections["sucursal"].dropna().unique())
            with c1:
                branch = st.selectbox("Sucursal", branches, key="forecast_branch")
            options = projections.loc[
                projections["sucursal"].eq(branch), ["ingrediente_id","nombre"]
            ].drop_duplicates()
            labels = dict(zip(options["ingrediente_id"], options["nombre"]))
            with c2:
                ingredient = st.selectbox(
                    "Ingrediente",
                    list(labels),
                    format_func=lambda value: labels.get(value, value),
                    key="forecast_ingredient",
                )
            chart_data = get_history_with_projection(report.cleaned_data, forecast, branch, ingredient)
            selected = projections.loc[
                projections["sucursal"].eq(branch)
                & projections["ingrediente_id"].eq(ingredient)
            ].iloc[0]
            hist = chart_data.loc[chart_data["tipo"].eq("Histórico")]
            proj = chart_data.loc[chart_data["tipo"].eq("Proyección")]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=hist["semana"],y=hist["consumo_unidad_base"],mode="lines+markers",
                    name="Consumo real",line={"color":"#171717","width":3},marker={"size":8},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=proj["semana"],y=proj["consumo_unidad_base"],mode="markers",
                    name="Próxima semana",marker={"size":15,"symbol":"diamond","color":"#E2372E"},
                )
            )
            fig.add_hrect(
                y0=float(selected["consumo_minimo"]),
                y1=float(selected["consumo_maximo"]),
                fillcolor="rgba(226,55,46,.08)",
                line_width=0,
            )
            fig.update_layout(
                height=410,
                xaxis_title="Semana",
                yaxis_title=f"Consumo ({selected['unidad_base']})",
                hovermode="x unified",
                margin={"l":20,"r":20,"t":25,"b":30},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,.9)",
            )
            forecast_cols = st.columns([1.45, .95], gap="large")
            with forecast_cols[0]:
                st.plotly_chart(fig,use_container_width=True)
            with forecast_cols[1]:
                st.markdown(
                    f"""
                    <div class="highlight-card">
                        <div class="eyebrow">Pronóstico operativo</div>
                        <div class="highlight-value">{selected['consumo_proyectado']:.2f} {selected['unidad_base']}</div>
                        <div class="highlight-title">{html.escape(labels[ingredient])}</div>
                        <div class="highlight-text">Consumo proyectado para <strong>{html.escape(branch)}</strong> en la próxima semana.</div>
                        <div class="highlight-list">
                            <div><strong>Promedio:</strong> {selected['consumo_promedio']:.2f} {selected['unidad_base']}</div>
                            <div><strong>Rango histórico:</strong> {selected['consumo_minimo']:.2f} – {selected['consumo_maximo']:.2f} {selected['unidad_base']}</div>
                            <div><strong>Semanas disponibles:</strong> {int(selected['semanas_disponibles'])}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# -----------------------------------------------------------------------------
# DATOS
# -----------------------------------------------------------------------------
elif current_page == "Datos":
    st.markdown(f'<div id="{PAGE_ANCHORS["Datos"]}" style="scroll-margin-top:1rem;"></div>', unsafe_allow_html=True)
    render_page_head(
        "DATOS EN ORDEN",
        "Consulta hallazgos y verifica las fuentes después de la limpieza inicial.",
        "quality",
        "Trazabilidad",
    )
    if scroll_target == PAGE_ANCHORS["Datos"]:
        emit_scroll_to(PAGE_ANCHORS["Datos"])
        st.session_state["_pending_scroll_target"] = None

    st.radio(
        "Sección de Datos",
        DATA_SUB_OPTIONS,
        horizontal=True,
        key="data_view",
        label_visibility="collapsed",
    )
    data_view = st.session_state["data_view"]

    if data_view == "Hallazgos":
        issues = build_hallazgos_display()
        if issues.empty:
            st.success("No se encontraron problemas de calidad.")
        else:
            levels = st.multiselect(
                "Nivel",
                ["Error", "Advertencia"],
                default=["Error", "Advertencia"],
                key="quality_levels",
            )
            filtered = issues.loc[issues["Nivel"].isin(levels)]
            if filtered.empty:
                st.info("No hay hallazgos para el nivel seleccionado.")
            else:
                level_counts = filtered.groupby("Nivel").size().reset_index(name="Hallazgos")
                level_colors = {"Error": "#171717", "Advertencia": "#E2372E"}
                center_col = st.columns([.18, .64, .18])[1]
                with center_col:
                    fig = make_donut(
                        level_counts["Nivel"],
                        level_counts["Hallazgos"],
                        [level_colors.get(level, "#AAA39B") for level in level_counts["Nivel"]],
                        title="Estado de calidad de datos",
                        center_label="hallazgos",
                        height=450,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.subheader("Detalle de hallazgos")
                st.dataframe(
                    filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Filas afectadas": st.column_config.NumberColumn(format="%d"),
                        "Mensaje": st.column_config.TextColumn(width="large"),
                    },
                )

    else:
        dataset = st.selectbox(
            "Archivo",
            list(report.cleaned_data.as_dict()),
            format_func=lambda value: value.replace("_", " ").title(),
            key="source_dataset",
        )
        raw_frame = report.cleaned_data.as_dict()[dataset].copy()
        ingredient_catalog = report.cleaned_data.ingredientes[["ingrediente_id", "nombre"]].drop_duplicates()
        ingredient_lookup = dict(zip(ingredient_catalog["ingrediente_id"], ingredient_catalog["nombre"]))

        def ingredient_label(value: str) -> str:
            name = ingredient_lookup.get(value)
            if name is None or pd.isna(name):
                return value
            return f"{name} · {value}"

        filtered_frame = raw_frame.copy()

        if dataset == "ingredientes":
            providers = sorted(filtered_frame["proveedor"].dropna().unique().tolist())
            selected_provider = st.selectbox(
                "Proveedor",
                ["Todos los proveedores", *providers],
                key="src_ingredients_provider",
            )
            if selected_provider != "Todos los proveedores":
                filtered_frame = filtered_frame.loc[filtered_frame["proveedor"].eq(selected_provider)]
            frame_to_show = filtered_frame
            visual = filtered_frame.groupby("proveedor", dropna=False).size().reset_index(name="registros")
            x_col, title = "proveedor", "Ingredientes registrados por proveedor"

        elif dataset == "consumo_historico":
            display_frame = filtered_frame.merge(ingredient_catalog, on="ingrediente_id", how="left")
            cols = st.columns(3)
            with cols[0]:
                selected_branch = st.selectbox(
                    "Sucursal",
                    ["Todas las sucursales", *sorted(display_frame["sucursal"].dropna().unique().tolist())],
                    key="src_hist_branch",
                )
            with cols[1]:
                selected_week = st.selectbox(
                    "Semana",
                    ["Todas las semanas", *sorted(display_frame["semana"].dropna().unique().tolist())],
                    key="src_hist_week",
                )
            ingredient_ids = sorted(display_frame["ingrediente_id"].dropna().unique().tolist(), key=ingredient_label)
            with cols[2]:
                selected_ingredient = st.selectbox(
                    "Ingrediente",
                    ["Todos los ingredientes", *ingredient_ids],
                    format_func=lambda value: value if value == "Todos los ingredientes" else ingredient_label(value),
                    key="src_hist_ingredient",
                )
            if selected_branch != "Todas las sucursales":
                display_frame = display_frame.loc[display_frame["sucursal"].eq(selected_branch)]
            if selected_week != "Todas las semanas":
                display_frame = display_frame.loc[display_frame["semana"].eq(selected_week)]
            if selected_ingredient != "Todos los ingredientes":
                display_frame = display_frame.loc[display_frame["ingrediente_id"].eq(selected_ingredient)]
            frame_to_show = display_frame.rename(columns={"nombre": "ingrediente"})
            visual = frame_to_show.groupby("sucursal", dropna=False).size().reset_index(name="registros")
            x_col, title = "sucursal", "Registros históricos por sucursal"

        elif dataset in {"inventario_actual", "orden_compra"}:
            display_frame = filtered_frame.merge(ingredient_catalog, on="ingrediente_id", how="left")
            cols = st.columns(2)
            with cols[0]:
                selected_branch = st.selectbox(
                    "Sucursal",
                    ["Todas las sucursales", *sorted(display_frame["sucursal"].dropna().unique().tolist())],
                    key=f"src_branch_{dataset}",
                )
            ingredient_ids = sorted(display_frame["ingrediente_id"].dropna().unique().tolist(), key=ingredient_label)
            with cols[1]:
                selected_ingredient = st.selectbox(
                    "Ingrediente",
                    ["Todos los ingredientes", *ingredient_ids],
                    format_func=lambda value: value if value == "Todos los ingredientes" else ingredient_label(value),
                    key=f"src_ingredient_{dataset}",
                )
            if selected_branch != "Todas las sucursales":
                display_frame = display_frame.loc[display_frame["sucursal"].eq(selected_branch)]
            if selected_ingredient != "Todos los ingredientes":
                display_frame = display_frame.loc[display_frame["ingrediente_id"].eq(selected_ingredient)]
            frame_to_show = display_frame.rename(columns={"nombre": "ingrediente"})
            visual = frame_to_show.groupby("sucursal", dropna=False).size().reset_index(name="registros")
            x_col = "sucursal"
            title = (
                "Líneas de inventario por sucursal"
                if dataset == "inventario_actual"
                else "Líneas de la orden de compra por sucursal"
            )

        else:
            frame_to_show = filtered_frame
            visual = pd.DataFrame()
            x_col, title = "", ""

        st.caption(f"{len(frame_to_show)} registros · {len(frame_to_show.columns)} columnas")

        if not visual.empty:
            source_fig = px.bar(
                visual,
                x=x_col,
                y="registros",
                text_auto=True,
                color_discrete_sequence=["#E2372E"],
            )
            source_fig.update_layout(
                title=title,
                height=390,
                xaxis_title="",
                yaxis_title="Registros",
                showlegend=False,
                margin={"l":25,"r":25,"t":60,"b":65},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,.9)",
                bargap=.32,
            )
            source_fig.update_yaxes(gridcolor="rgba(23,23,23,.08)")
            source_fig.update_xaxes(tickangle=-12)
            st.plotly_chart(source_fig, use_container_width=True)

        st.subheader("Vista de registros")
        st.dataframe(frame_to_show, use_container_width=True, hide_index=True)


"""
Founder Readiness Program (FRP) — Full Stack App
=================================================
Stack: Streamlit + Supabase
Users: 55 founders + 1 admin
Flow:  PSF → PMF → GTM → Revenue Model Validation → Funding/Debt Readiness → Analytics
"""

import streamlit as st
import json
import os
import io
import math
import time
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Dev Mode ──────────────────────────────────────────────────────────────────
# Set DEV_MODE = True to bypass Supabase and use dummy credentials
DEV_MODE = False

DEV_ACCOUNTS = {
    "admin@frp.dev":    {"password": "admin123", "role": "admin", "id": "dev-admin-001"},
    "user@frp.dev":     {"password": "user123",  "role": "user",  "id": "dev-user-001"},
    "founder2@frp.dev": {"password": "user123",  "role": "user",  "id": "dev-user-002"},
}

class _DevUser:
    """Mock user object that mimics Supabase user for dev mode."""
    def __init__(self, uid, email):
        self.id = uid
        self.email = email

# ── Supabase Setup ──
from supabase import create_client, Client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
ADMIN_EMAIL  = os.environ.get("ADMIN_EMAIL", "admin@frp.dev")

def get_supabase() -> Client:
    """Get or create a per-session Supabase client."""
    if "supabase_client" not in st.session_state:
        if SUPABASE_URL and SUPABASE_KEY:
            st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            st.session_state.supabase_client = None
    
    # Ensure auth session is synced from session state if it exists
    client = st.session_state.supabase_client
    if client and st.session_state.get("sb_access_token") and st.session_state.get("sb_refresh_token"):
        try:
            # Check if current client auth matches our session state
            # If not, sync it.
            curr_session = client.auth.get_session()
            if not curr_session or curr_session.access_token != st.session_state["sb_access_token"]:
                client.auth.set_session(st.session_state["sb_access_token"], st.session_state["sb_refresh_token"])
        except:
            pass
    return client

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FRP Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# SCORING CONFIG  (from Excel)
# ─────────────────────────────────────────────────────────────────────────────
PHASES = {
    "PSF": {
        "label": "Product-Solution Fit",
        "icon": "🔬",
        "color": "#6366f1",
        "pillars": {
            "Customer Discovery": {
                "max": 20,
                "options": [
                    ("0 interviews", 0),
                    ("1–5 interviews", 5),
                    ("6–10 interviews", 10),
                    ("11–20 interviews", 15),
                    ("20+ interviews", 20),
                ],
                "kpi": "No. of qualified customer interviews completed",
            },
            "Solution Validation": {
                "max": 25,
                "options": [
                    ("0 interested users", 0),
                    ("1–3 positive responses", 10),
                    ("4–7 positive responses", 15),
                    ("8–10 pilot intent / LOIs", 20),
                    ("10+ willing to pay / committed", 25),
                ],
                "kpi": "No. of customers who validated interest / demo / pilot intent",
            },
            "Early Traction": {
                "max": 30,
                "options": [
                    ("0 traction", 0),
                    ("1–5 leads", 10),
                    ("1–2 pilots running", 15),
                    ("1 paying customer", 20),
                    ("2–5 paying customers", 25),
                    ("5+ paying / repeat customers", 30),
                ],
                "kpi": "No. of pilots / LOIs / paying customers / repeat users",
            },
            "Product Iteration": {
                "max": 15,
                "options": [
                    ("0 releases", 0),
                    ("1 update", 5),
                    ("2–3 updates", 10),
                    ("4+ updates / monthly releases", 15),
                ],
                "kpi": "No. of improvements released based on feedback",
            },
            "Compliance & Docs": {
                "max": 10,
                "options": [
                    ("0 completed", 0),
                    ("1 item completed", 3),
                    ("2–3 items completed", 5),
                    ("4–5 items completed", 8),
                    ("All required completed", 10),
                ],
                "kpi": "No. of required registrations / docs completed",
            },
        },
        "status_bands": [(80, "Strong PSF – Ready for PMF Push"), (60, "Good Progress"), (40, "Early Validation"), (0, "Idea Stage")],
    },
    "PMF": {
        "label": "Product-Market Fit",
        "icon": "🎯",
        "color": "#10b981",
        "pillars": {
            "ICP Sharpening": {
                "max": 20,
                "options": [
                    ("No ICP defined", 0),
                    ("Broad segment only", 5),
                    ("ICP documented", 10),
                    ("ICP tested with outreach", 15),
                    ("ICP converts consistently", 20),
                ],
                "kpi": "No. of clearly defined ICP customers / conversion from ICP segment",
            },
            "Channel Validation": {
                "max": 25,
                "options": [
                    ("No channel tested", 0),
                    ("1 channel tested", 10),
                    ("CAC known", 15),
                    ("Best channel identified", 20),
                    ("Repeatable profitable channel", 25),
                ],
                "kpi": "No. of tested channels with CAC + conversion data",
            },
            "Revenue Growth": {
                "max": 25,
                "options": [
                    ("No growth", 0),
                    ("Some new leads", 10),
                    ("1–3 new customers", 15),
                    ("20%+ growth", 20),
                    ("30–50%+ growth", 25),
                ],
                "kpi": "New customers added / revenue growth achieved",
            },
            "Retention & Expansion": {
                "max": 15,
                "options": [
                    ("No repeat customers", 0),
                    ("Some repeat usage", 5),
                    ("Retention tracked", 10),
                    ("Upsell / strong retention", 15),
                ],
                "kpi": "Repeat customers / upsells / retention rate",
            },
            "Operational Readiness": {
                "max": 15,
                "options": [
                    ("No systems", 0),
                    ("Bottlenecks identified", 5),
                    ("Processes improved", 10),
                    ("SOPs ready for scale", 15),
                ],
                "kpi": "No. of bottlenecks fixed / SOPs ready for scale",
            },
        },
        "status_bands": [(80, "Strong PMF – Ready for GTM Push"), (60, "Good Progress"), (40, "Early PMF"), (0, "PMF Stage")],
    },
    "GTM": {
        "label": "Go-To-Market",
        "icon": "📡",
        "color": "#f59e0b",
        "pillars": {
            "ICP & Customer Segments": {
                "max": 20,
                "options": [
                    ("No clear ICP", 0),
                    ("Broad segment only", 5),
                    ("ICP defined", 10),
                    ("Best segment identified", 15),
                    ("ICP converts consistently", 20),
                ],
                "kpi": "No. of validated ICP customers / best-performing segment clarity",
            },
            "Channel Performance": {
                "max": 25,
                "options": [
                    ("No working channel", 0),
                    ("1 active channel", 10),
                    ("CAC tracked", 15),
                    ("CAC + LTV known", 20),
                    ("Profitable repeatable channel", 25),
                ],
                "kpi": "No. of tested channels with CAC + conversion data",
            },
            "Pipeline & Conversion": {
                "max": 25,
                "options": [
                    ("No pipeline", 0),
                    ("Leads in discussion", 10),
                    ("Proposal stage deals", 15),
                    ("Closed deals happening", 20),
                    ("Predictable monthly pipeline conversion", 25),
                ],
                "kpi": "No. of leads and conversion performance in sales funnel",
            },
            "Pricing & Revenue Growth": {
                "max": 20,
                "options": [
                    ("No revenue growth", 0),
                    ("Revenue stable", 5),
                    ("New customers added", 10),
                    ("Price tested / upsell working", 15),
                    ("Revenue growing consistently", 20),
                ],
                "kpi": "Price increase success, revenue growth, ARPU expansion",
            },
            "Operations & Fulfilment": {
                "max": 10,
                "options": [
                    ("Delivery bottlenecks severe", 0),
                    ("Capacity known", 5),
                    ("Bottlenecks fixed", 8),
                    ("Ready for 3x scale demand", 10),
                ],
                "kpi": "Capacity readiness, bottlenecks removed, delivery reliability",
            },
        },
        "status_bands": [(80, "Strong GTM – Revenue Ready"), (60, "GTM Working"), (40, "Early GTM Validation"), (0, "Pre-GTM")],
    },
    "Revenue": {
        "label": "Revenue Model Validation",
        "icon": "💰",
        "color": "#ec4899",
        "pillars": {
            "Pricing Clarity": {
                "max": 25,
                "options": [
                    ("No pricing defined", 0),
                    ("Price exists but not tested", 8),
                    ("Price tested with 1–2 customers", 15),
                    ("Price validated, consistent payment", 20),
                    ("Pricing model scalable with data", 25),
                ],
                "kpi": "Pricing model clarity and validation level",
            },
            "Revenue Streams": {
                "max": 25,
                "options": [
                    ("Single untested stream", 0),
                    ("1 stream, some revenue", 10),
                    ("1 stream, consistent revenue", 15),
                    ("2 streams validated", 20),
                    ("Multiple streams, growing MRR", 25),
                ],
                "kpi": "No. of validated revenue streams",
            },
            "Unit Economics": {
                "max": 25,
                "options": [
                    ("No metrics tracked", 0),
                    ("CAC known only", 8),
                    ("CAC + LTV known", 15),
                    ("LTV:CAC > 2, margins tracked", 20),
                    ("LTV:CAC > 3, path to profitability clear", 25),
                ],
                "kpi": "CAC, LTV, gross margin, contribution margin",
            },
            "Recurring Revenue": {
                "max": 15,
                "options": [
                    ("No recurring revenue", 0),
                    ("Some repeat customers", 5),
                    ("10–30% recurring", 10),
                    ("30%+ recurring revenue", 15),
                ],
                "kpi": "% of recurring vs one-time revenue",
            },
            "Financial Forecasting": {
                "max": 10,
                "options": [
                    ("No forecasts exist", 0),
                    ("Revenue estimate only", 4),
                    ("P&L forecast prepared", 7),
                    ("Full cash flow + scenario model", 10),
                ],
                "kpi": "Quality and detail of financial forecasting",
            },
        },
        "status_bands": [(80, "Revenue Model Validated"), (60, "Revenue Emerging"), (40, "Early Revenue Stage"), (0, "Pre-Revenue")],
    },
    "Funding": {
        "label": "Funding / Debt Readiness",
        "icon": "🏦",
        "color": "#8b5cf6",
        "pillars": {
            "Revenue Performance": {
                "max": 25,
                "options": [
                    ("No revenue / declining", 0),
                    ("Irregular revenue", 10),
                    ("Stable monthly revenue", 15),
                    ("Growing revenue (3 months)", 20),
                    ("Consistent MoM growth + recurring base", 25),
                ],
                "kpi": "Revenue growth, recurring revenue, churn control",
            },
            "Unit Economics": {
                "max": 25,
                "options": [
                    ("No metrics known", 0),
                    ("CAC known only", 10),
                    ("CAC + LTV known", 15),
                    ("Positive margin + payback known", 20),
                    ("Healthy LTV:CAC + scalable economics", 25),
                ],
                "kpi": "CAC, LTV, gross margin, payback period validation",
            },
            "Financial Hygiene": {
                "max": 20,
                "options": [
                    ("No organised records", 0),
                    ("Basic P&L available", 8),
                    ("Statements updated", 12),
                    ("Auditeds + projections ready", 16),
                    ("Full investor-grade finance pack", 20),
                ],
                "kpi": "Quality of financial records and reporting readiness",
            },
            "Fundraising Readiness": {
                "max": 20,
                "options": [
                    ("No deck / no outreach", 0),
                    ("Deck ready", 8),
                    ("Data room started", 12),
                    ("Investor meetings happening", 16),
                    ("Strong pipeline + refined narrative", 20),
                ],
                "kpi": "Investor material readiness and outreach momentum",
            },
            "Capital Readiness": {
                "max": 10,
                "options": [
                    ("No ask clarity", 0),
                    ("Rough requirement known", 4),
                    ("Use of funds clear", 7),
                    ("Right instrument + deployment plan clear", 10),
                ],
                "kpi": "Clarity on capital needs and deployment plan",
            },
        },
        "status_bands": [(80, "Fund Ready"), (60, "Fundraising Emerging"), (40, "Early Readiness"), (0, "Not Ready Yet")],
    },
}

PHASE_ORDER = ["PSF", "PMF", "GTM", "Revenue", "Funding"]

# ─────────────────────────────────────────────────────────────────────────────
# THEME SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
def build_css(theme="dark"):
    L = theme == "light"
    # ── Token palette ──
    bg_app       = "#f8fafc"    if L else "#050a14"
    bg_side      = "#ffffff"    if L else "#0b1424"
    bg_card      = "rgba(255,255,255,0.9)" if L else "rgba(15, 23, 42, 0.7)"
    bg_ter       = "#f1f5f9"    if L else "#1e293b"
    tx1          = "#0f172a"    if L else "#f8fafc"
    tx2          = "#475569"    if L else "#94a3b8"
    tx3          = "#94a3b8"    if L else "#64748b"
    brd          = "rgba(0,0,0,0.06)"   if L else "rgba(255,255,255,0.08)"
    brd_h        = "rgba(99,102,241,0.4)" if L else "rgba(99,102,241,0.5)"
    gt           = "#e2e8f0"    if L else "#1e293b"
    hero_bg      = "linear-gradient(135deg,#6366f1 0%,#a855f7 100%)"
    inp_bg       = "#ffffff"    if L else "#0f172a"
    inp_brd      = "rgba(0,0,0,0.1)"    if L else "rgba(255,255,255,0.1)"
    sh_card      = "0 4px 20px rgba(0,0,0,0.05)" if L else "0 4px 20px rgba(0,0,0,0.2)"
    sh_hover     = "0 12px 40px rgba(99,102,241,0.15)" if L else "0 12px 40px rgba(99,102,241,0.25)"
    div_c        = "rgba(0,0,0,0.06)"   if L else "rgba(255,255,255,0.05)"
    pill_bg      = "#e53935"
    accent       = "#6366f1"
    glass        = "backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"

    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── BASE ── */
html,body,[class*="css"]{{font-family:'Inter',sans-serif; transition: all 0.3s ease;}}
.stApp.stApp{{background:{bg_app} !important; transition: background 0.4s ease;}}
[data-testid="stAppViewContainer"][data-testid="stAppViewContainer"]{{background:{bg_app} !important;}}
.main .block-container{{padding-top:1.5rem;max-width:1180px;}}
section[data-testid="stSidebar"]{{background:{bg_side};border-right:1px solid {brd};transition: background 0.4s ease;}}

/* ── ANIMATIONS ── */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes scaleIn{{from{{opacity:0;transform:scale(.95)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes shimmer{{0%{{background-position:-200% 0}}100%{{background-position:200% 0}}}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}

/* ── HERO ── */
.hero{{background:{hero_bg}; border-radius:24px; padding:2.5rem 3rem; margin-bottom:2rem;
  border:1px solid rgba(255,255,255,0.1); animation:fadeInUp .6s cubic-bezier(0.16, 1, 0.3, 1);
  position:relative; overflow:hidden; box-shadow: 0 20px 50px rgba(99, 102, 241, 0.2);}}
.hero h1{{color:#ffffff; font-size:2.5rem; font-weight:900; margin:0; letter-spacing:-0.5px;}}
.hero p{{color:rgba(255,255,255,0.8); font-size:1.1rem; margin:.6rem 0 0;}}
.pill{{display:inline-block;background:{pill_bg};color:#fff;font-size:.75rem;
  font-weight:800;padding:4px 16px;border-radius:20px;text-transform:uppercase;
  letter-spacing:1px;margin-bottom:1rem; box-shadow: 0 4px 10px rgba(229, 57, 53, 0.3);}}

/* ── CARDS ── */
.card{{background:{bg_card}; {glass} border:1px solid {brd}; border-radius:20px;
  padding:1.6rem; margin-bottom:1.5rem; box-shadow:{sh_card};
  transition:all .4s cubic-bezier(0.16, 1, 0.3, 1); animation:fadeInUp .5s ease-out;}}
.card:hover{{border-color:{brd_h}; transform:translateY(-4px); box-shadow:{sh_hover};}}

/* ── STAT BOX ── */
.stat{{background:{bg_card}; {glass} border:1px solid {brd}; border-radius:18px;
  padding:1.2rem; text-align:center; box-shadow:{sh_card};
  transition:all .4s ease; animation:scaleIn .6s cubic-bezier(0.16, 1, 0.3, 1);}}
.stat:hover{{transform:translateY(-4px); box-shadow:{sh_hover}; border-color:{brd_h};}}
.stat-val{{font-size:2.2rem; font-weight:900; color:{accent}; margin-bottom: 4px;}}
.stat-lbl{{font-size:.75rem; color:{tx3}; text-transform:uppercase; letter-spacing:1.5px; font-weight:700;}}

/* ── STREAMLIT WIDGET OVERRIDES ── */
div.stButton>button{{border-radius:12px; font-weight:700; background:{bg_card};
  color:{tx1}; border:1px solid {inp_brd}; transition:all .3s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 0.6rem 1.2rem; {glass}}}
div.stButton>button:hover{{border-color:{accent}; color:{accent};
  transform:translateY(-2px); box-shadow:0 8px 25px rgba(99,102,241,.2);}}

div.stSelectbox>div,div.stTextInput>div>div, div.stTextArea>div>div{{
  background:{inp_bg} !important; border-radius:12px !important;
  border-color:{inp_brd} !important; color:{tx1} !important; transition: all 0.3s ease;}}
div.stSelectbox>div:focus-within, div.stTextInput>div>div:focus-within{{
  border-color:{accent} !important; box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;}}

.stTabs [data-baseweb="tab-list"]{{gap: 8px; background: transparent;}}
.stTabs [data-baseweb="tab"]{{
  background: {bg_ter}; border-radius: 10px 10px 0 0; border: 1px solid {brd};
  padding: 10px 20px; color: {tx2}; font-weight: 600; transition: all 0.3s ease;}}
.stTabs [aria-selected="true"]{{
  background: {bg_card} !important; color: {accent} !important; border-color: {brd_h} !important;
  border-bottom: 2px solid {accent} !important;}}

/* ── RADIO BUTTONS & OPTIONS ── */
.stRadio div[role="radiogroup"]{{gap: 1.5rem !important;}}
.stRadio label, .stRadio label p, .stRadio label span, .stRadio [data-testid="stWidgetLabel"] p{{
  color: {tx1} !important; font-size: 1rem !important; font-weight: 600 !important;
  opacity: 1 !important; visibility: visible !important;}}
.stRadio label:hover{{transform: translateY(-1px); color: {accent} !important;}}
/* Ensure the radio circle labels themselves are high contrast */
[data-testid="stMarkdownContainer"] p {{color: {tx1} !important;}}

/* ── FULL APP OVERRIDES ── */
.stMarkdown, .stMarkdown p, .stMarkdown span{{color:{tx1} !important; font-size: 0.95rem;}}
.stMarkdown h1,.stMarkdown h2,.stMarkdown h3,.stMarkdown h4,.stMarkdown h5,.stMarkdown h6{{color:{tx1} !important; font-weight:800;}}
label[data-testid="stWidgetLabel"]{{color:{tx1} !important; font-weight:700; font-size: 1.05rem !important;}}
.stDivider{{border-color:{brd} !important; margin: 2rem 0 !important;}}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label{{color:{tx1} !important;}}

/* ── CUSTOM TEXT CLASSES ── */
.tp{{color:{tx1};}}
.ts{{color:{tx2};}}
.tm{{color:{tx3};}}
.bg-ter{{background:{bg_ter};}}

/* ── GAUGE SVG ── */
.gauge-track{{stroke:{gt};}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{{width:8px;}}
::-webkit-scrollbar-track{{background:{bg_app};}}
::-webkit-scrollbar-thumb{{background:{tx3}; border-radius:10px; border: 2px solid {bg_app};}}
::-webkit-scrollbar-thumb:hover{{background:{tx2};}}

/* ── PLACEHOLDERS ── */
::placeholder {{ color: {tx3} !important; opacity: 0.8 !important; }}
input::placeholder {{ color: {tx3} !important; opacity: 0.8 !important; }}

/* ── PRINT (PDF EXPORT) CSS ── */
@media print {{
  section[data-testid="stSidebar"] {{ display: none !important; }}
  header[data-testid="stHeader"] {{ display: none !important; }}
  .stTabs [data-baseweb="tab-list"] {{ display: none !important; }}
  .stButton {{ display: none !important; }}
  body {{ background: white !important; color: black !important; }}
  * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
}}
</style>"""



# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_status(phase_key, score):
    for threshold, label in PHASES[phase_key]["status_bands"]:
        if score >= threshold:
            return label
    return PHASES[phase_key]["status_bands"][-1][1]

def phase_score(phase_key, answers):
    """answers = {pillar: score_value}. Returns (total, max)."""
    total = sum(answers.get(p, 0) for p in PHASES[phase_key]["pillars"])
    max_s = sum(v["max"] for v in PHASES[phase_key]["pillars"].values())
    return total, max_s

def score_color(pct):
    if pct >= 80: return "#10b981"
    if pct >= 60: return "#f59e0b"
    if pct >= 40: return "#f97316"
    return "#ef4444"

def gauge_svg(pct, color, size=120):
    r = 46; cx = cy = size // 2
    circ = 2 * math.pi * r
    arc = circ * 0.75
    offset = arc * (1 - pct / 100)
    rot = 135
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle class="gauge-track" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke-width="10"
        stroke-dasharray="{arc:.1f} {circ:.1f}" stroke-linecap="round"
        transform="rotate({rot},{cx},{cy})"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="10"
        stroke-dasharray="{arc-offset:.1f} {circ:.1f}" stroke-linecap="round"
        transform="rotate({rot},{cx},{cy})" style="transition:stroke-dasharray .8s ease-out;"/>
      <text x="{cx}" y="{cy+5}" text-anchor="middle" fill="{color}"
        font-size="18" font-weight="900" font-family="Inter">{pct:.0f}</text>
    </svg>"""

# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE DB CALLS
# ─────────────────────────────────────────────────────────────────────────────
import json
import os

DEV_DB_FILE = ".dev_db.json"

def _load_dev_db():
    if os.path.exists(DEV_DB_FILE):
        try:
            with open(DEV_DB_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def _save_dev_db(db):
    try:
        with open(DEV_DB_FILE, "w") as f:
            json.dump(db, f)
    except: pass

# ─────────────────────────────────────────────
# 🏢 COMPANIES
# ─────────────────────────────────────────────

def db_get_or_create_company(user_id, company_name, founder_name):
    if DEV_MODE:
        return {"id": "dev-co-001", "company_name": company_name, "founder_name": founder_name}
    
    client = get_supabase()
    if not client: return None
    
    try:
        # Check if company exists
        res = client.table("companies").select("*").eq("user_id", user_id).execute()
        if res.data:
            co = res.data[0]
            # Update names if they changed
            if co["company_name"] != company_name or co["founder_name"] != founder_name:
                client.table("companies").update({
                    "company_name": company_name, 
                    "founder_name": founder_name
                }).eq("id", co["id"]).execute()
            return co
            
        # Create new
        ins = client.table("companies").insert({
            "user_id": user_id,
            "company_name": company_name,
            "founder_name": founder_name
        }).execute()
        return ins.data[0] if ins.data else None
    except Exception as e:
        st.error(f"Company Sync Error: {e}")
        return None

# ─────────────────────────────────────────────
# 📅 SUBMISSIONS (Atomic)
# ─────────────────────────────────────────────

def db_save_full_submission(user_id, company_name, founder_name, week_start, answers_dict):
    """
    Saves a complete weekly snapshot. Atomic operation:
    1. Upsert Company
    2. Upsert Weekly Submission (Summary)
    3. Replace Answers (Granular)
    """
    if DEV_MODE:
        st.success("Dev Mode: Saved Snapshot")
        return True

    client = get_supabase()
    if not client: return False
    
    try:
        # 1. Company
        company = db_get_or_create_company(user_id, company_name, founder_name)
        if not company: return False
        cid = company["id"]
        
        # 2. Compute Phase Totals
        phase_scores = {}
        for ph in PHASE_ORDER:
            total, _ = phase_score(ph, answers_dict.get(ph, {}))
            phase_scores[ph] = total
            
        # 3. Upsert Submission Summary
        sub_payload = {
            "company_id": cid,
            "week_start": str(week_start),
            "psf_score": phase_scores.get("PSF", 0),
            "pmf_score": phase_scores.get("PMF", 0),
            "gtm_score": phase_scores.get("GTM", 0),
            "revenue_score": phase_scores.get("Revenue", 0),
            "funding_score": phase_scores.get("Funding", 0),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        sub_res = client.table("weekly_submissions").upsert(sub_payload, on_conflict="company_id,week_start").execute()
        if not sub_res.data: return False
        sid = sub_res.data[0]["id"]
        
        # 4. Replace Answers (Granular)
        # Delete old answers for this submission to keep it clean
        client.table("answers").delete().eq("submission_id", sid).execute()
        
        answer_rows = []
        for phase, pillars in answers_dict.items():
            for pillar, score in pillars.items():
                answer_rows.append({
                    "submission_id": sid,
                    "phase": phase,
                    "pillar": pillar,
                    "score": score
                })
        
        if answer_rows:
            client.table("answers").insert(answer_rows).execute()
            
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

def db_load_user_history(user_id):
    """Loads all historical submissions for a user."""
    if DEV_MODE: return []
    client = get_supabase()
    if not client: return []
    
    try:
        # Complex join via RPC or explicit join
        # For simplicity in this step, we fetch submissions for the user's company
        res = client.table("weekly_submissions")\
            .select("*, companies!inner(user_id)")\
            .eq("companies.user_id", user_id)\
            .order("week_start", desc=True)\
            .execute()
        return res.data or []
    except:
        return []

def db_load_full_answers(submission_id):
    """Loads granular answers for a specific submission."""
    if DEV_MODE: return []
    client = get_supabase()
    if not client: return []
    try:
        res = client.table("answers").select("*").eq("submission_id", submission_id).execute()
        return res.data or []
    except: return []

# ─────────────────────────────────────────────
# 🧑💼 ADMIN DATA
# ─────────────────────────────────────────────

def db_load_admin_cohort_data():
    """Loads latest submission for every company."""
    if DEV_MODE: return []
    client = get_supabase()
    if not client: return []
    try:
        # Get all companies and their latest submission
        # Use a join to get company names
        res = client.table("weekly_submissions")\
            .select("*, companies(company_name, founder_name, user_id)")\
            .order("week_start", desc=True)\
            .execute()
        return res.data or []
    except:
        return []

def db_delete_company(company_id):
    """Soft delete or Hard delete based on preference. Here: Hard Delete."""
    if DEV_MODE: return True, 1
    client = get_supabase()
    if not client: return False, 0
    try:
        res = client.table("companies").delete().eq("id", company_id).execute()
        return True, len(res.data)
    except Exception as e:
        st.error(f"Delete Error: {e}")
        return False, 0
    if DEV_MODE:
        return sorted(set(r["entry_date"] for r in _load_dev_db() if r["user_id"] == user_id))
    client = get_supabase()
    if not client: return []
    try:
        res = client.table("frp_entries").select("entry_date").eq("user_id", user_id).execute()
        return sorted(set(r["entry_date"] for r in (res.data or [])))
    except:
        return []

def restore_user_session(user_id):
    """Fetch the most recent entry from DB and restore session state."""
    entries = db_load_entries(user_id)
    if not entries:
        return
    
    # Sort by date descending
    df = pd.DataFrame(entries)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    latest_date = df["entry_date"].max()
    latest_rows = df[df["entry_date"] == latest_date]
    
    # Restore basic info
    first_row = latest_rows.iloc[0]
    st.session_state.company = first_row.get("company_name", "")
    st.session_state.founder = first_row.get("founder_name", "")
    st.session_state.selected_week = latest_date.strftime("%Y-%m-%d")
    
    # Restore answers for all weeks (to populate analytics)
    # Answers structure: {phase: {pillar: score}}
    new_answers = {}
    # We actually only want to pre-fill the form with the LATEST week's answers
    for _, row in latest_rows.iterrows():
        new_answers.setdefault(row["phase"], {})[row["pillar"]] = row["score_value"]
    
    st.session_state.answers = new_answers

def login_user(email, password):
    # ── Dev mode: check dummy credentials ──
    if DEV_MODE:
        account = DEV_ACCOUNTS.get(email.lower())
        if account and account["password"] == password:
            return _DevUser(account["id"], email.lower()), None, None
        return None, None, "Invalid dev credentials. Use admin@frp.dev/admin123 or user@frp.dev/user123"

    client = get_supabase()
    if not client: return None, None, "Supabase not configured"
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res.user, res.session, None
    except Exception as e:
        return None, None, str(e)

def signup_user(email, password):
    if DEV_MODE:
        return None, None, "Sign-up disabled in DEV_MODE. Use the pre-set dev accounts."

    client = get_supabase()
    if not client: return None, None, "Supabase not configured"
    try:
        res = client.auth.sign_up({"email": email, "password": password})
        return res.user, res.session, None
    except Exception as e:
        return None, None, str(e)

def logout_user():
    client = get_supabase()
    if client:
        try: client.auth.sign_out()
        except: pass
    for k in ["user", "is_admin", "company", "founder", "answers", "selected_week", "sb_access_token", "sb_refresh_token", "admin_target"]:
        st.session_state.pop(k, None)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION INIT
# ─────────────────────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "user": None,
        "is_admin": False,
        "company": "",
        "founder": "",
        "answers": {},        # {phase: {pillar: score}}
        "active_phase": "PSF",
        "selected_week": str(date.today()),
        "admin_target": None,
        "theme": "light",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Supabase client is now lazy-loaded via get_supabase()
    # No need to explicitly set session here as get_supabase() handles it
    pass

# ── DIALOGS ──
@st.dialog("Verify Your Email")
def signup_success_dialog():
    st.markdown("""
    <div style="text-align:center;">
        <h2 style="font-size:3rem; margin-bottom:1rem;">📧</h2>
        <p style="font-size:1.1rem; font-weight:500;">Go to your email and click the link to verify your account.</p>
        <p class="tm" style="font-size:0.9rem; margin-top:1rem; padding:12px; background:rgba(0,0,0,0.03); border-radius:8px;">
            Don't worry if the link opens a blank page—just come back here to log in once you've clicked it.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Close & Go to Login", use_container_width=True, type="primary"):
        st.session_state.user = None
        st.rerun()

@st.dialog("Welcome to FRP!")
def signup_welcome_dialog():
    st.markdown("""
    <div style="text-align:center;">
        <h2 style="font-size:3rem; margin-bottom:1rem;">🚀</h2>
        <p style="font-size:1.2rem; font-weight:600; color:#10b981;">Welcome to FRP Tracker!</p>
        <p style="font-size:1rem; margin-top:0.5rem;">Your account has been created successfully. Since email verification is disabled, you can jump right in!</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start Tracking Now →", use_container_width=True, type="primary"):
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_auth():
    st.markdown("""
    <div class="hero" style="text-align:center;max-width:480px;margin:4rem auto 2rem;">
        <div class="pill">Founder Readiness Program</div>
        <h1 style="font-size:1.8rem;">🚀 FRP Tracker</h1>
    </div>
    """, unsafe_allow_html=True)
    
    col = st.columns([1, 2, 1])[1]
    with col:
        _sidebar_theme_toggle()
        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

        with tab_login:
            email = st.text_input("Email", key="li_email", placeholder="you@startup.in")
            pwd   = st.text_input("Password", type="password", key="li_pwd")
            if st.button("Login", use_container_width=True, key="btn_login"):
                if email and pwd:
                    user, session, err = login_user(email, pwd)
                    if user:
                        st.session_state.user = user
                        if session:
                            st.session_state.sb_access_token = session.access_token
                            st.session_state.sb_refresh_token = session.refresh_token
                        
                        # Automatically restore data from DB
                        restore_user_session(user.id)
                        
                        # Support multiple admins separated by commas
                        admin_list = [a.strip().lower() for a in ADMIN_EMAIL.split(',')]
                        st.session_state.is_admin = (email.lower() in admin_list)
                        
                        st.rerun()
                    else:
                        st.error(f"Login failed: {err}")
                else:
                    st.warning("Enter email and password.")
            
            st.markdown('<p style="text-align:center;font-size:0.8rem;margin-top:1rem;color:#64748b;">Forgot Password? Please contact your program administrator.</p>', unsafe_allow_html=True)

        with tab_signup:
            s_email = st.text_input("Email", key="su_email", placeholder="founder@startup.in")
            s_pwd   = st.text_input("Password (min 6 chars)", type="password", key="su_pwd")
            s_pwd2  = st.text_input("Confirm Password", type="password", key="su_pwd2")
            if st.button("Create Account", use_container_width=True, key="btn_signup"):
                if not s_email or not s_pwd:
                    st.warning("Fill all fields.")
                elif s_pwd != s_pwd2:
                    st.error("Passwords don't match.")
                elif len(s_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    user, session, err = signup_user(s_email, s_pwd)
                    if user:
                        st.session_state.user = user
                        if session:
                            st.session_state.sb_access_token = session.access_token
                            st.session_state.sb_refresh_token = session.refresh_token
                        
                        # Restore (likely empty for new signup but good for consistency)
                        restore_user_session(user.id)
                        
                        # Immediately check if this new user should be an admin
                        admin_list = [a.strip().lower() for a in ADMIN_EMAIL.split(',')]
                        is_admin = (s_email.lower() in admin_list)
                        
                        if is_admin:
                            st.success("Admin account created! 📧 Please check your email (if enabled) and then Login.")
                        else:
                            if session:
                                # Email verification is OFF, user is logged in
                                signup_welcome_dialog()
                            else:
                                # Email verification is ON, user needs to verify
                                signup_success_dialog()
                    else:
                        st.error(f"Signup failed: {err}")

    if DEV_MODE:
        st.markdown("""
        <div class="card" style="text-align:center;max-width:400px;margin:2rem auto;padding:1.2rem;">
          <p style="color:#f59e0b;font-weight:700;font-size:0.9rem;margin-bottom:0.5rem;">🔧 DEV MODE — Dummy Accounts</p>
          <p class="ts" style="font-size:0.82rem;margin:4px 0;">👑 Admin: <code style="color:#6366f1;background:rgba(99,102,241,0.1);padding:2px 6px;border-radius:4px;">admin@frp.dev</code> / <code style="color:#6366f1;">admin123</code></p>
          <p class="ts" style="font-size:0.82rem;margin:4px 0;">👤 User 1: <code style="color:#6366f1;background:rgba(99,102,241,0.1);padding:2px 6px;border-radius:4px;">user@frp.dev</code> / <code style="color:#6366f1;">user123</code></p>
          <p class="ts" style="font-size:0.82rem;margin:4px 0;">👤 User 2: <code style="color:#6366f1;background:rgba(99,102,241,0.1);padding:2px 6px;border-radius:4px;">founder2@frp.dev</code> / <code style="color:#6366f1;">user123</code></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<p class="tm" style="text-align:center;font-size:0.8rem;margin-top:3rem;">Admin login: use the admin email set by your program coordinator.</p>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR (user)
# ─────────────────────────────────────────────────────────────────────────────
def _sidebar_theme_toggle():
    """Render theme toggle; returns current theme string."""
    is_light = st.toggle(
        "☀️ Light Mode",
        value=st.session_state.theme == "light",
        key="theme_toggle_widget",
    )
    new_theme = "light" if is_light else "dark"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

def show_sidebar_user():
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;color:#e53935;'>🚀 FRP Tracker</h2>", unsafe_allow_html=True)
        user_email = st.session_state.user.email if st.session_state.user else ""
        st.markdown(f'<p class="tm" style="text-align:center;font-size:0.8rem;">{user_email}</p>', unsafe_allow_html=True)
        _sidebar_theme_toggle()
        st.divider()

        st.markdown("### 🏢 Your Details")
        st.session_state.company = st.text_input("Company Name", value=st.session_state.company, placeholder="e.g. Aztra technologies")
        st.session_state.founder = st.text_input("Founder Name", value=st.session_state.founder, placeholder="e.g. MathitYahu")

        st.divider()
        st.markdown("### 📅 Entry Week")
        st.session_state.selected_week = st.date_input("Select Friday date", value=date.today()).isoformat()

        st.divider()
        # Upload JSON to resume
        st.markdown("### 📂 Upload Previous Data")
        uploaded = st.file_uploader("Upload JSON (v1/v2...)", type="json", key="upload_json")
        if uploaded:
            try:
                data = json.load(uploaded)
                st.session_state.answers  = data.get("answers", {})
                st.session_state.company  = data.get("company", st.session_state.company)
                st.session_state.founder  = data.get("founder", st.session_state.founder)
                st.success("Data loaded! You can now edit and re-save.")
            except:
                st.error("Invalid JSON file.")

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Fill each phase weekly. Your score improves automatically.")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR (admin)
# ─────────────────────────────────────────────────────────────────────────────
def show_sidebar_admin():
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;color:#e53935;'>🚀 FRP Admin</h2>", unsafe_allow_html=True)
        st.markdown('<p class="tm" style="text-align:center;font-size:0.75rem;">Admin Panel</p>', unsafe_allow_html=True)
        _sidebar_theme_toggle()
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PHASE INPUT TAB
# ─────────────────────────────────────────────────────────────────────────────
def show_phase_input(phase_key):
    phase = PHASES[phase_key]
    uid   = st.session_state.user.id if st.session_state.user else "demo"
    ph_answers = st.session_state.answers.get(phase_key, {})

    st.markdown(f"""
    <div class="card" style="border-left:4px solid {phase['color']};">
        <h3 style="margin:0;">{phase['icon']} {phase['label']}</h3>
        <p class="tm" style="margin:0.2rem 0 0;font-size:0.9rem;">
        Rate each pillar based on your current evidence this week.</p>
    </div>
    """, unsafe_allow_html=True)

    changed = False
    for idx, (pillar, pdata) in enumerate(phase["pillars"].items(), 1):
        st.markdown(f"**{idx}. {pillar}** <span title='{pdata['kpi']}' style='cursor:help; opacity:0.7;'>❔</span> — *{pdata['kpi']}*", unsafe_allow_html=True)
        opts = [o[0] for o in pdata["options"]]
        vals = {o[0]: o[1] for o in pdata["options"]}
        cur_val = ph_answers.get(pillar, 0)
        cur_opt = next((o[0] for o in pdata["options"] if o[1] == cur_val), opts[0])

        chosen = st.radio(
            f"Select option for {pillar}",
            opts,
            index=opts.index(cur_opt),
            key=f"radio_{phase_key}_{pillar}",
            horizontal=True,
            label_visibility="collapsed",
        )
        new_val = vals[chosen]
        if new_val != cur_val:
            ph_answers[pillar] = new_val
            changed = True
        elif pillar not in ph_answers:
            ph_answers[pillar] = new_val

        score_pct = int(new_val / pdata["max"] * 100) if pdata["max"] else 0
        col_g, col_s = st.columns([1, 5])
        col_g.markdown(gauge_svg(score_pct, phase["color"], 70), unsafe_allow_html=True)
        col_s.markdown(f'<p class="tm" style="font-size:0.8rem;">Score: <b style="color:{score_color(score_pct)};">{new_val}/{pdata["max"]}</b></p>', unsafe_allow_html=True)
        st.divider()

    if changed:
        st.session_state.answers[phase_key] = ph_answers

    total, max_s = phase_score(phase_key, ph_answers)
    pct = int(total / max_s * 100) if max_s else 0
    status = get_status(phase_key, pct)

    st.markdown(f"""
    <div class="card" style="text-align:center;">
        <div class="tm" style="font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">
        {phase_key} Score</div>
        <div style="font-size:2.5rem;font-weight:900;color:{score_color(pct)};">{total}/{max_s}</div>
        <div style="font-size:1rem;color:{score_color(pct)};font-weight:700;">{status}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    # Protection: Only show View-Only if Admin is viewing a target
    if st.session_state.is_admin and st.session_state.get("admin_target"):
        st.info("💡 You are in View-Only mode for this company.")
    else:
        if st.button(f"💾 Save {phase_key} Entry", width="stretch", key=f"save_{phase_key}"):
            if not st.session_state.company or not st.session_state.founder:
                st.error("Set Company & Founder name in sidebar first.")
            else:
                # Use the new atomic submission service
                ok = db_save_full_submission(
                    user_id=uid,
                    company_name=st.session_state.company,
                    founder_name=st.session_state.founder,
                    week_start=st.session_state.selected_week,
                    answers_dict=st.session_state.answers
                )
                
                if ok:
                    st.success(f"✅ Full assessment saved for {st.session_state.selected_week}.")
                    st.balloons()
                    time.sleep(2.5)
                    st.rerun()
                else:
                    st.error("Failed to save to cloud. Please check your connection.")

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS TAB
# ─────────────────────────────────────────────────────────────────────────────
def show_analytics(uid=None, company_override=None):
    target_uid = uid or (st.session_state.user.id if st.session_state.user else None)
    company    = company_override or st.session_state.company
    founder    = st.session_state.founder

    # Load historical submissions
    history = db_load_user_history(target_uid) if target_uid else []
    
    # Get the latest submission for initial display if session is empty
    latest_sub = history[0] if history else None
    
    # If session state is empty, pre-fill from latest DB submission
    if not any(st.session_state.answers.values()) and latest_sub:
        granular = db_load_full_answers(latest_sub["id"])
        for ans in granular:
            st.session_state.answers.setdefault(ans["phase"], {})[ans["pillar"]] = ans["score"]

    session_answers = st.session_state.answers

    st.markdown(f"""
    <div class="hero">
        <div class="pill">Analytics Dashboard</div>
        <h1 style="font-size:1.6rem;">📊 {company or 'Your Company'}</h1>
        <p>Founder: {founder or '—'} &nbsp;|&nbsp; 90-Day FRP Progress</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Overall Score Cards ──
    st.markdown("### 🏆 Phase Scores (Latest / Session)")
    cols = st.columns(len(PHASE_ORDER))
    for i, ph in enumerate(PHASE_ORDER):
        phase = PHASES[ph]
        ph_ans = session_answers.get(ph, {})

        # Fill from DB if session is empty
        if not ph_ans and ph in answers:
            for pil, dates in answers[ph].items():
                latest_dt = max(dates.keys())
                ph_ans[pil] = dates[latest_dt]

        total, max_s = phase_score(ph, ph_ans)
        pct = int(total / max_s * 100) if max_s else 0
        color = phase["color"]
        status = get_status(ph, pct)
        cols[i].markdown(f"""
        <div class="stat">
            {gauge_svg(pct, color, 90)}
            <div style="font-size:0.75rem;font-weight:700;color:{color};margin-top:4px;">{phase['icon']} {ph}</div>
            <div class="tm" style="font-size:0.65rem;">{status}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 90-Day Journey Analytics ──
    st.markdown("### 🗺️ The 90-Day Journey")
    
    col_print, col_dl = st.columns([4, 2])
    with col_print:
        # Integrated PDF Download Button via iframe hack
        import streamlit.components.v1 as components
        components.html(
            """
            <div style="display: flex; align-items: center; height: 100%; font-family: sans-serif;">
                <button onclick="window.parent.print()" style="background:#4f46e5;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:600;font-size:14px;box-shadow:0 1px 3px rgba(0,0,0,0.1);transition:background 0.2s;">
                    🖨️ Download PDF Report
                </button>
                <span style="color:#64748b;font-size:12px;margin-left:12px;">Generates a clean PDF of this dashboard.</span>
            </div>
            """,
            height=50
        )
    
    with col_dl:
        if all_entries:
            df_dl = pd.DataFrame(all_entries)
            csv = df_dl.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV Report",
                data=csv,
                file_name=f"FRP_Report_{company or 'Founder'}.csv",
                mime='text/csv',
                use_container_width=True
            )
        
    if all_entries:
        df = pd.DataFrame(all_entries)
        df["entry_date"] = pd.to_datetime(df["entry_date"])
        pivot_raw = df.groupby(["entry_date", "phase"])["score_value"].sum().reset_index()
        pivot = pivot_raw.pivot(index="entry_date", columns="phase", values="score_value").fillna(0)
        
        # Convert raw scores to percentages for accurate comparison
        for ph in PHASE_ORDER:
            if ph in pivot.columns:
                max_s = sum(v["max"] for v in PHASES[ph]["pillars"].values())
                if max_s > 0:
                    pivot[ph] = (pivot[ph] / max_s * 100).astype(int)
        
        pivot = pivot.reindex(columns=[p for p in PHASE_ORDER if p in pivot.columns])
        
        c_trend, c_radar = st.columns([3, 2])
        
        with c_trend:
            st.markdown("#### 📈 Week-over-Week Trajectory")
            plot_df = pivot.copy()
            plot_df.index = plot_df.index.strftime("%d %b")
            fig_line = px.line(plot_df, x=plot_df.index, y=plot_df.columns, markers=True,
                               color_discrete_sequence=[PHASES[p]["color"] for p in plot_df.columns])
            fig_line.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8", margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
            )
            fig_line.update_yaxes(title="Phase Score", range=[0, 105], gridcolor="rgba(148,163,184,0.1)")
            fig_line.update_xaxes(title="")
            st.plotly_chart(fig_line, use_container_width=True)
            
        with c_radar:
            st.markdown("#### 🎯 Execution Footprint")
            fig_radar = go.Figure()
            categories = plot_df.columns.tolist()
            
            # Plot Previous Week (if available)
            if len(plot_df) > 1:
                prev_vals = plot_df.iloc[-2].tolist()
                fig_radar.add_trace(go.Scatterpolar(
                    r=prev_vals + [prev_vals[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    name='Previous Week',
                    fillcolor='rgba(148, 163, 184, 0.2)',
                    line=dict(color='rgba(148, 163, 184, 0.5)', width=2)
                ))
                
            # Plot Current Week
            if len(plot_df) > 0:
                curr_vals = plot_df.iloc[-1].tolist()
                fig_radar.add_trace(go.Scatterpolar(
                    r=curr_vals + [curr_vals[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    name='Current Week',
                    fillcolor='rgba(99, 102, 241, 0.3)',
                    line=dict(color='#6366f1', width=3)
                ))
                
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(148,163,184,0.2)", tickfont=dict(color="rgba(148,163,184,0.5)")),
                    angularaxis=dict(gridcolor="rgba(148,163,184,0.2)"),
                    bgcolor="rgba(0,0,0,0)"
                ),
                paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
                margin=dict(l=40, r=40, t=20, b=20),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
    else:
        st.warning("⚠️ **No saved entries found for this week.** \n\nTo generate your 90-Day Journey charts, you must scroll to the bottom of each Phase tab (e.g., PSF, PMF) and click the **💾 Save Entry** button after making your selections.")

    # ── Per Phase Breakdown ──
    st.markdown("### 🔍 Phase Breakdown (Current Session)")
    for ph in PHASE_ORDER:
        phase    = PHASES[ph]
        ph_ans   = session_answers.get(ph, {})
        total, max_s = phase_score(ph, ph_ans)
        pct = int(total / max_s * 100) if max_s else 0

        with st.expander(f"{phase['icon']} {phase['label']}  —  {total}/{max_s}"):
            for idx, (pillar, pdata) in enumerate(phase["pillars"].items(), 1):
                val = ph_ans.get(pillar, 0)
                p_pct = int(val / pdata["max"] * 100) if pdata["max"] else 0
                bar_w = max(4, p_pct)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <div class="ts" style="width:160px;font-size:0.82rem;">{idx}. {pillar}</div>
                    <div class="bg-ter" style="flex:1;border-radius:6px;height:10px;">
                        <div style="width:{bar_w}%;background:{phase['color']};height:10px;border-radius:6px;"></div>
                    </div>
                    <div style="width:60px;text-align:right;font-size:0.82rem;color:{score_color(p_pct)};font-weight:700;">
                    {val}/{pdata['max']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Download Section ──
    st.markdown("### 📥 Download Your Data")
    export = {
        "company": company,
        "founder": founder,
        "export_date": datetime.now().isoformat(),
        "answers": session_answers,
        "phase_scores": {
            ph: {"total": phase_score(ph, session_answers.get(ph, {}))[0],
                 "max":   phase_score(ph, session_answers.get(ph, {}))[1],
                 "status": get_status(ph, int(phase_score(ph, session_answers.get(ph,{}))[0] /
                            max(phase_score(ph, session_answers.get(ph,{}))[1], 1) * 100))}
            for ph in PHASE_ORDER
        }
    }
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇ Download as JSON",
            data=json.dumps(export, indent=2),
            file_name=f"{(company or 'FRP').replace(' ','_')}_v{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        # CSV flat export
        rows = []
        for ph, ph_data in session_answers.items():
            for pillar, val in ph_data.items():
                rows.append({"Phase": ph, "Pillar": pillar, "Score": val,
                             "Max": PHASES[ph]["pillars"][pillar]["max"]})
        csv_df = pd.DataFrame(rows)
        st.download_button(
            "⬇ Download as CSV",
            data=csv_df.to_csv(index=False),
            file_name=f"{(company or 'FRP').replace(' ','_')}_v{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# USER MAIN
# ─────────────────────────────────────────────────────────────────────────────
def show_user_app():
    show_sidebar_user()
    company = st.session_state.company
    founder = st.session_state.founder

    st.markdown(f"""
    <div class="hero">
        <div class="pill">Bootcamp 2026</div>
        <h1>Founder Readiness Program</h1>
        <p>{company or 'Set your company name →'} &nbsp;|&nbsp; {founder or 'Set founder name'}</p>
    </div>
    """, unsafe_allow_html=True)

    # Phase tabs
    tab_labels = [f"{PHASES[p]['icon']} {p}" for p in PHASE_ORDER] + ["📊 Analytics"]
    tabs = st.tabs(tab_labels)

    for i, ph in enumerate(PHASE_ORDER):
        with tabs[i]:
            show_phase_input(ph)

    with tabs[-1]:
        show_analytics()

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN MAIN
# ─────────────────────────────────────────────────────────────────────────────
def show_admin_app():
    show_sidebar_admin()
    
    # ── Breadcrumb Navigation Logic ──
    target = st.session_state.get("admin_target")
    
    if target:
        # Deep Dive View
        st.markdown(f"""
        <div class="no-print" style="display:flex; align-items:center; gap:10px; margin-bottom:20px;">
            <div style="background:#4f46e5; color:white; padding:4px 12px; border-radius:20px; font-size:0.8rem; font-weight:600;">Admin Panel</div>
            <div style="color:#64748b; font-size:1.2rem;">/</div>
            <div style="font-weight:600; font-size:1rem; color:#1e293b;">Viewing: {target['company_name']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("← Back to Cohort Dashboard", use_container_width=True, key="back_to_cohort"):
            st.session_state.admin_target = None
            st.rerun()
            
        show_admin_deep_dive(target)
    else:
        # Main Cohort View
        show_admin_cohort_view()

def show_admin_cohort_view():
    st.markdown("""
    <div class="hero">
        <div class="pill">Admin Panel</div>
        <h1>🛡 FRP Admin Dashboard</h1>
        <p>Monitor all founder companies in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── RELATIONAL DATA FETCH ──
    all_submissions = db_load_admin_cohort_data()
    if not all_submissions:
        st.info("No submissions found yet.")
        return

    # Process data for visualization
    seen_companies = set()
    latest_cohort = []
    for sub in all_submissions:
        cid = sub["company_id"]
        if cid not in seen_companies:
            co_info = sub["companies"]
            latest_cohort.append({
                "company_id": cid,
                "user_id": co_info["user_id"],
                "company_name": co_info["company_name"],
                "founder_name": co_info["founder_name"],
                "week_start": sub["week_start"],
                "total_score": sub["total_score"],
                "PSF": sub["psf_score"],
                "PMF": sub["pmf_score"],
                "GTM": sub["gtm_score"],
                "Revenue": sub["revenue_score"],
                "Funding": sub["funding_score"],
            })
            seen_companies.add(cid)

    df_cohort = pd.DataFrame(latest_cohort)
    
    # ── COHORT WEAKNESS HEATMAP ──
    st.markdown("### 🌡️ Cohort Weakness Heatmap")
    st.markdown('<p style="font-size:0.8rem; color:#64748b;">Instantly see which phases founders are struggling with across the whole cohort.</p>', unsafe_allow_html=True)
    
    heatmap_df = df_cohort.set_index("company_name")[PHASE_ORDER]
    fig_heat = px.imshow(
        heatmap_df,
        labels=dict(x="Phase", y="Company", color="Score"),
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )
    fig_heat.update_layout(height=max(300, len(latest_cohort)*30), margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})

    # ── STATS CARDS ──
    avg_score = df_cohort["total_score"].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Companies", len(latest_cohort))
    c2.metric("Avg Cohort Score", f"{avg_score:.1f}")
    c3.metric("Latest Submission", max(sub["week_start"] for sub in all_submissions))

    # ── SEARCH & FILTERS ──
    search = st.text_input("🔍 Search Founder or Company", placeholder="Filter list...")
    
    filtered = df_cohort
    if search:
        filtered = df_cohort[
            df_cohort["company_name"].str.contains(search, case=False) | 
            df_cohort["founder_name"].str.contains(search, case=False)
        ]


    # Company list
    st.markdown(f"### 🏢 Companies ({len(final_list)})")
    for co in filtered.to_dict("records"):
        cid    = co["company_id"]
        score  = co["total_score"]
        # Max theoretical score
        max_t = sum(sum(pd["max"] for pd in PHASES[ph]["pillars"].values()) for ph in PHASE_ORDER)
        pct    = int(score/max_t*100) if max_t else 0
        color  = score_color(pct)

        col_a, col_spark, col_b, col_c, col_d = st.columns([3, 2, 1, 1, 0.6])
        
        # Column A: Info
        col_a.markdown(f"""
        <div>
            <div class="tp" style="font-weight:700;font-size:1.1rem;color:#1e293b;">{co['company_name']}</div>
            <div class="tm" style="font-size:0.8rem;color:#64748b;">👤 {co['founder_name']}</div>
            <div style="font-size:0.7rem; color:#94a3b8;">Latest: {co['week_start']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Column Spark: Trajectory
        with col_spark:
            # Load historical trend for this company
            co_history = [s for s in all_submissions if s["company_id"] == cid]
            if co_history:
                df_h = pd.DataFrame(co_history).sort_values("week_start")
                fig_spark = px.line(df_h, x="week_start", y="total_score")
                fig_spark.update_layout(
                    height=40, width=120, margin=dict(l=5, r=5, t=5, b=5),
                    xaxis_visible=False, yaxis_visible=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_spark.update_traces(line_color=color, line_width=2.5)
                st.plotly_chart(fig_spark, use_container_width=False, config={'displayModeBar': False})
        
        # Column B: Score
        col_b.markdown(f"""
        <div style="text-align:center;">
            <div style="color:{color};font-weight:800;font-size:1.4rem;">{pct}%</div>
            <div style="font-size:0.6rem;text-decoration:uppercase;color:#94a3b8;">Readiness</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Column C: Action
        if col_c.button("View →", key=f"view_{cid}", use_container_width=True):
            st.session_state.admin_target = co
            st.rerun()

        # Column D: Delete
        if col_d.button("🗑️", key=f"del_{cid}", help=f"Delete ALL data for {co['company_name']}"):
            st.session_state[f"confirm_delete_{cid}"] = True

        # Inline confirmation
        if st.session_state.get(f"confirm_delete_{cid}"):
            st.error(f"Permanently delete ALL data for **{co['company_name']}**?")
            c_del1, c_del2 = st.columns(2)
            if c_del1.button("Confirm Delete", key=f"y_del_{cid}", type="primary", use_container_width=True):
                success, count = db_delete_company(cid)
                if success:
                    st.success(f"Successfully deleted {co['company_name']}.")
                    del st.session_state[f"confirm_delete_{cid}"]
                    time.sleep(1.5)
                    st.rerun()
            if c_del2.button("Cancel", key=f"n_del_{cid}", use_container_width=True):
                del st.session_state[f"confirm_delete_{cid}"]
                st.rerun()

        st.divider()

    # Company list section continues...


def show_admin_deep_dive(target):
    uid = target["user_id"]
    st.markdown(f"""
    <div class="card no-print" style="border-top: 4px solid #4f46e5;">
        <h2 style="margin:0;">📈 Deep Dive: {target['company_name']}</h2>
        <p style="color:#64748b; margin:4px 0 0;">Founder: {target['founder_name']} | Accessing live trajectory data.</p>
    </div>
    """, unsafe_allow_html=True)

    # Load all weekly entries for this user
    entries = db_load_entries(uid)
    if not entries:
        st.info("No entries for this company yet.")
    else:
        df_e = pd.DataFrame(entries)
        weeks = sorted(df_e["entry_date"].unique(), reverse=True)
        sel_week = st.selectbox("Select week to review", weeks, key="admin_week_select")

        week_entries = df_e[df_e["entry_date"] == sel_week]
        week_answers = {}
        for _, row in week_entries.iterrows():
            week_answers.setdefault(row["phase"], {})[row["pillar"]] = row["score_value"]

        # Temporarily override session for analytics display
        orig_answers = st.session_state.answers
        orig_week = st.session_state.selected_week
        
        st.session_state.answers = week_answers
        st.session_state.selected_week = sel_week
        
        # Reuse existing analytics component
        show_analytics(uid=uid, company_override=target["company_name"])
        
        # Restore session state
        st.session_state.answers = orig_answers
        st.session_state.selected_week = orig_week

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    init_session()
    
    # Warm up Supabase client
    get_supabase()

    # ── Single CSS injection for current theme ──
    st.markdown(build_css(st.session_state.theme), unsafe_allow_html=True)

    if not st.session_state.user:
        show_auth()
        return

    if st.session_state.is_admin:
        show_admin_app()
    else:
        show_user_app()

if __name__ == "__main__":
    main()

import streamlit as st

def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --pr-gold: #E6B85C;
            --pr-ink: #0B0D10;
            --pr-panel: #151920;
            --pr-soft: #202631;
            --pr-muted: #9DA6B2;
            --pr-line: rgba(255,255,255,.08);
            --pr-red: #E76F51;
            --pr-green: #7FB685;
        }
        .block-container {max-width: 1480px; padding-top: 1.35rem; padding-bottom: 4rem;}
        [data-testid="stSidebar"] {border-right: 1px solid var(--pr-line);}
        h1,h2,h3 {letter-spacing: -0.03em;}
        .pr-brand {
            display:flex; align-items:center; gap:.9rem; margin-bottom: .25rem;
        }
        .pr-mark {
            width:42px; height:42px; border:1px solid rgba(230,184,92,.55);
            display:flex; align-items:center; justify-content:center;
            border-radius:12px; color:var(--pr-gold); font-weight:800; font-size:1.1rem;
            box-shadow: inset 0 0 20px rgba(230,184,92,.06);
        }
        .pr-kicker {
            font-size:.76rem; text-transform:uppercase; letter-spacing:.18em;
            color:var(--pr-gold); font-weight:700;
        }
        .pr-title {font-size:2.1rem; font-weight:800; line-height:1; margin:.15rem 0 .25rem;}
        .pr-sub {color:var(--pr-muted); font-size:.98rem;}
        .pr-card {
            background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.018));
            border:1px solid var(--pr-line); border-radius:16px; padding:1rem 1.05rem;
            min-height:100%;
        }
        .pr-card-title {font-size:.75rem; text-transform:uppercase; letter-spacing:.12em; color:var(--pr-muted); font-weight:700;}
        .pr-card-value {font-size:1.55rem; font-weight:800; margin-top:.25rem;}
        .pr-quote {
            border-left:3px solid var(--pr-gold); padding:.7rem 1rem; color:#E9E5DA;
            background:rgba(230,184,92,.055); border-radius:0 12px 12px 0;
        }
        .pr-pill {
            display:inline-block; border:1px solid var(--pr-line); padding:.25rem .5rem;
            border-radius:999px; margin:.1rem .2rem .1rem 0; color:#D8DDE4; font-size:.8rem;
        }
        .pr-danger {color:#F0A08A;}
        .pr-good {color:#A5D6AA;}
        .pr-muted {color:var(--pr-muted);}
        .pr-divider {height:1px;background:var(--pr-line);margin:1rem 0;}
        .stButton > button {border-radius:10px; font-weight:700;}
        .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {border-radius:10px;}
        [data-testid="stMetricValue"] {font-weight:800;}
        </style>
        """,
        unsafe_allow_html=True,
    )

def brand():
    st.markdown(
        """
        <div class="pr-brand">
          <div class="pr-mark">PR</div>
          <div>
            <div class="pr-kicker">Writers, under pressure.</div>
            <div class="pr-title">Pressure Room</div>
            <div class="pr-sub">A causal story-development workspace.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def page_header(kicker: str, title: str, sub: str = ""):
    st.markdown(
        f"""
        <div style="margin-bottom:1.1rem">
          <div class="pr-kicker">{kicker}</div>
          <h1 style="margin:.15rem 0 .2rem">{title}</h1>
          <div class="pr-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def card(label: str, value: str, note: str = ""):
    return f"""
    <div class="pr-card">
      <div class="pr-card-title">{label}</div>
      <div class="pr-card-value">{value}</div>
      <div class="pr-sub">{note}</div>
    </div>
    """

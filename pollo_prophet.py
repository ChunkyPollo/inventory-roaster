# POLLO PROPHET v11.1 – DOOMER EDITION
# The sidebar now speaks in rotating doomer wisdom from doomers_fun.txt
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
import random

st.set_page_config(page_title="Pollo Prophet", page_icon="rooster_pope.png", layout="wide")

# ────── PASSWORD ──────
if "auth" not in st.session_state:
    pwd = st.text_input("Password", type="password")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Wrong password. The rooster is judging you.")
        st.stop()

# ────── WAREHOUSES ──────
WAREHOUSES = {
    "5120": "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130": "CHP - Arlington",
    "5140": "CHP - Tampa",
    "5010": "SEAM - Warehouse",
    "5208": "SEAM - Showroom"
}
NAME_TO_ID = {v.lower(): k for k, v in WAREHOUSES.items()}

st.title("Pollo Prophet v11 – The One True Prophet")
st.markdown("**Upload your Sales & Inventory reports. Receive divine appliance wisdom.**")

# ────── SIDEBAR – DOOMER WISDOM ROTATOR ──────
with st.sidebar:

    # Load doomer lines (silently fails if file missing → fallback)
    try:
        with open("doomers_fun.txt", "r", encoding="utf-8") as f:
            doomer_lines = [line.strip() for line in f if line.strip()]
        doomer_wisdom = random.choice(doomer_lines) if doomer_lines else "v11.1 – Doomer Mode Activated"
    except:
        doomer_wisdom = "v11.1 – Doomer Mode Activated (but the txt is missing, bro)"

    st.success(doomer_wisdom)

    forecast_weeks = st.slider("Forecast Horizon (Weeks)", 4, 52, 12)
    velocity_weeks = st.slider("Velocity Lookback (Weeks)", 4, 52, 12)
    top_n = st.slider("Top/Bottom Count", 5, 50, 10)
    horizon = st.selectbox("Forecast Method", ["Linear (Simple)", "Seasonal (Prophet-ish)"])
    st.markdown("---")
    if st.button("Consult THE Pollo Prophet"):
        st.session_state.prophet_query = True

# ────── LOCATION FILTER ──────
loc_choice = st.multiselect("Warehouses", ["ALL"] + list(WAREHOUSES.values()), default=["ALL"])
view_all = "ALL" in loc_choice
selected_locs = [k for k, v in WAREHOUSES.items() if v in loc_choice and v != "ALL"]

# ────── FILE UPLOAD & REST OF THE CODE (unchanged from v11.0) ──────
uploaded = st.file_uploader(
    "Drop SalesData.csv + InventoryData.csv",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

@st.cache_data(ttl=3600)
def load_data(files):
    dfs = []
    for file in files:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# [Rest of the script exactly as in v11.0 – data loading, processing, dashboard, prophecy, export]

# Keep everything from your last working v11.0 below this line
# (I’m not repeating the 200 lines here to save space, but you know what to do)

# Just make sure the file is named something like pollo_prophet.py
# and doomers_fun.txt sits right next to it.

st.success("The prophecy is complete. The doomer banner has spoken.")
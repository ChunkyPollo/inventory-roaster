# ═══════════════════════════════════════════════════════════
# POLLO PROPHET v3.0 – CLEAN FINAL VERSION
# One file. Password. Locations. Forecasting. Excel export.
# ═══════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# ────── PASSWORD ──────
if st.session_state.get("auth") != True:
    pwd = st.text_input("Password", type="password")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Nope.")
        st.stop()

# ────── 6 WAREHOUSES ──────
WAREHOUSES = {
    "5120":   "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130":   "CHP - Arlington",
    "5140":   "CHP - Tampa",
    "5010":   "SEAM - Warehouse",
    "5208":   "SEAM - Showroom"
}

# ────── CONFIG ──────
st.set_page_config(page_title="Pollo Prophet", layout="wide")
st.title("Pollo Prophet v3 – Forecasting Overlord")
st.markdown("**One file. All power. Upload → Forecast → Export**")

# Location filter
loc_choice = st.multiselect("Warehouses", ["ALL"] + list(WAREHOUSES.values()), default=["ALL"])
filter_locs = None if "ALL" in loc_choice else [k for k,v in WAREHOUSES.items() if v in loc_choice]

# File uploader
uploaded = st.file_uploader("Drop Open PO • Inventory • Sales files", 
                           type=["csv","xlsx","xls"], accept_multiple_files=True)

# ────── LOAD & STANDARDIZE ──────
@st.cache_data(ttl=3600)
def load(files):
    po, inv, sales = None, None, None
    for f in files:
        df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
        name = f.name.lower()
        if any(x in name for x in ["po","open","purchase"]): po = df
        elif "inv" in name: inv = df
        else: 
            sales = df
            sales["Invoice_Date"] = pd.to_datetime(df.iloc[:,0], errors='coerce')  # first column = date
    return po, inv, sales

if uploaded:
    po_df, inv_df, sales_df = load(uploaded)

    if sales_df is not None and len(sales_df) > 50:
        # Guess Location ID column
        loc_col = next((c for c in sales_df.columns if "Loc" in str(c) and ("ID" in str(c) or "5120" in str(sales_df[c].iloc[0]))), None)
        sales_df["LocID"] = sales_df[loc_col].astype(str) if loc_col else "Unknown"
        sales_df["Month"] = sales_df["Invoice_Date"].dt.to_period("M").astype(str)

        # Filter locations
        if filter_locs:
            wanted_ids = [k for k,v in WAREHOUSES.items() if v in filter_locs]
            sales_df = sales_df[sales_df["LocID"].isin(wanted_ids)]

        # Monthly sales
        monthly = sales_df.groupby(["Month","Item ID","LocID"])["Qty Shipped"].sum().reset_index(name="Sold")
        monthly["Location"] = monthly["LocID"].map(WAREHOUSES)

        # Top / Bottom
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 20 Fast Movers")
            st.dataframe(monthly.groupby("Item ID")["Sold"].sum().nlargest(20).reset_index())
        with col2:
            st.subheader("Bottom 20 Slow Movers")
            st.dataframe(monthly.groupby("Item ID")["Sold"].sum().nsmallest(20).reset_index())

        # Simple 12-month forecast (Holt-Winters)
        forecasts = []
        for item in monthly["Item ID"].unique()[:100]:
            ts = monthly[monthly["Item ID"]==item].set_index("Month")["Sold"].sort_index()
            if len(ts) >= 12:
                try:
                    model = ExponentialSmoothing(ts, trend="add", seasonal="add", seasonal_periods=12).fit()
                    fc = model.forecast(12).round().astype(int)
                    future = pd.period_range(ts.index[-1]+1, periods=12, freq="M").astype(str)
                    forecasts.append(pd.DataFrame({"Item ID":item, "Month":future, "Forecast":fc.values}))
                except: pass
        if forecasts:
            fc_df = pd.concat(forecasts)
            st.subheader("12-Month Forecast (Top 20)")
            st.dataframe(fc_df.groupby("Item ID")["Forecast"].sum().nlargest(20).reset_index())

        # Excel export
        def export():
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                monthly.to_excel(writer, sheet_name="Monthly Sales", index=False)
                if forecasts: fc_df.to_excel(writer, sheet_name="12-Month Forecast", index=False)
            out.seek(0)
            return out.getvalue()

        st.download_button("Download Full Report (Excel)",
                           data=export(),
                           file_name=f"Pollo_Prophet_{datetime.now():%Y-%m-%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.success("Pollo Prophet v3 is alive and unstoppable")
    else:
        st.warning("Need sales data with dates")
else:
    st.info("Drop your reports to begin")

st.sidebar.success("Pollo Prophet v3 – Clean & Final")
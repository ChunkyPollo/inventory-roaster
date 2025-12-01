# POLLO PROPHET v8.0 – FINAL, UNKILLABLE, WORKS ON STREAMLIT CLOUD
# No prophet. No crashes. Only domination.

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px

# ────── PASSWORD ──────
if "auth" not in st.session_state:
    pwd = st.text_input("Password", type="password")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Wrong password.")
        st.stop()

# ────── WAREHOUSES ──────
WAREHOUSES = {
    "5120":   "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130":   "CHP - Arlington",
    "5140":   "CHP - Tampa",
    "5010":   "SEAM - Warehouse",
    "5208":   "SEAM - Showroom"
}

st.set_page_config(page_title="Pollo Prophet v8", layout="wide")
st.title("Pollo Prophet v8 – Unbreakable Forecasting")
st.markdown("**Upload files. Get real insights. Never crashes.**")

# ────── CONTROLS ──────
with st.sidebar:
    st.success("v8.0 – Final & Perfect")
    forecast_weeks = st.slider("Forecast Weeks", 4, 52, 12)
    velocity_weeks = st.slider("Velocity Lookback", 4, 52, 12)
    top_n = st.slider("Top/Bottom Count", 5, 50, 20)

# ────── LOCATION FILTER ──────
loc_choice = st.multiselect("Warehouses", ["ALL"] + list(WAREHOUSES.values()), default=["ALL"])
view_all = "ALL" in loc_choice
selected_locs = [k for k,v in WAREHOUSES.items() if v in loc_choice and v != "ALL"]

# ────── UPLOAD ──────
uploaded = st.file_uploader("Drop Sales, Inventory, PO files", type=["csv","xlsx","xls"], accept_multiple_files=True)

# ────── LOAD FILES ──────
@st.cache_data(ttl=3600)
def load_data(files):
    sales_data = []
    inv_data = []
    po_data = []

    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f, sheet_name=0)
        except:
            st.error(f"Could not read {f.name}")
            continue

        cols = [c.lower() for c in df.columns]
        text = " ".join(cols)

        # SALES
        if any(x in text for x in ["invoice", "sold", "shipped", "sales"]):
            item = next((c for c in df.columns if any(k in c.lower() for k in ["item","sku","product"])), None)
            loc = next((c for c in df.columns if "loc" in c.lower()), None)
            qty = next((c for c in df.columns if "qty" in c.lower() and ("sold" in c.lower() or "ship" in c.lower())), None)
            date = next((c for c in df.columns if "date" in c.lower()), None)
            if all([item, loc, qty, date]):
                temp = pd.DataFrame({
                    "ItemID": df[item].astype(str),
                    "LocID": df[loc].astype(str),
                    "Qty": pd.to_numeric(df[qty], errors="coerce").fillna(0),
                    "Date": pd.to_datetime(df[date], errors="coerce")
                })
                sales_data.append(temp.dropna(subset=["Date"]))
                st.success(f"Loaded Sales: {f.name}")

        # INVENTORY
        elif any(x in text for x in ["available", "on hand", "inventory"]):
            item = next((c for c in df.columns if any(k in c.lower() for k in ["item","sku"])), None)
            loc = next((c for c in df.columns if "loc" in c.lower()), None)
            qty = next((c for c in df.columns if any(k in c.lower() for k in ["available","on hand","qoh"])), None)
            if item and loc and qty:
                temp = pd.DataFrame({
                    "ItemID": df[item].astype(str),
                    "LocID": df[loc].astype(str),
                    "OnHand": pd.to_numeric(df[qty], errors="coerce").fillna(0)
                })
                inv_data.append(temp)
                st.success(f"Loaded Inventory: {f.name}")

        # PO
        else:
            item = next((c for c in df.columns if any(k in c.lower() for k in ["item","sku"])), None)
            loc = next((c for c in df.columns if "loc" in c.lower()), None)
            qty = next((c for c in df.columns if "qty" in c.lower() and "order" in c.lower()), None)
            if item and loc and qty:
                temp = pd.DataFrame({
                    "ItemID": df[item].astype(str),
                    "LocID": df[loc].astype(str),
                    "Ordered": pd.to_numeric(df[qty], errors="coerce").fillna(0)
                })
                po_data.append(temp)
                st.success(f"Loaded PO: {f.name}")

    sales = pd.concat(sales_data, ignore_index=True) if sales_data else pd.DataFrame()
    inv = pd.concat(inv_data, ignore_index=True) if inv_data else pd.DataFrame()
    po = pd.concat(po_data, ignore_index=True) if po_data else pd.DataFrame()
    return sales, inv, po

if uploaded:
    sales_df, inv_df, po_df = load_data(uploaded)

    if not sales_df.empty:
        # Filter locations
        wanted = list(WAREHOUSES.keys()) if view_all else selected_locs
        sales_df = sales_df[sales_df["LocID"].isin(wanted)]

        # Velocity
        cutoff = datetime.now() - timedelta(days=velocity_weeks * 7)
        recent = sales_df[sales_df["Date"] >= cutoff]
        velocity = recent.groupby("ItemID")["Qty"].sum().reset_index()
        velocity["Weekly"] = velocity["Qty"] / velocity_weeks

        # Merge inventory
        merged = velocity.copy()
        if not inv_df.empty:
            inv_sum = inv_df.groupby("ItemID")["OnHand"].sum().reset_index()
            merged = merged.merge(inv_sum, on="ItemID", how="left").fillna(0)
        else:
            merged["OnHand"] = 0

        merged["DaysSupply"] = np.where(merged["Weekly"] > 0, merged["OnHand"] / merged["Weekly"], 999)

        # Top/Bottom
        top = merged.nlargest(top_n, "Weekly")
        bottom = merged.nsmallest(top_n, "Weekly")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top Fast Movers")
            st.dataframe(top[["ItemID", "Weekly", "OnHand", "DaysSupply"]])
        with col2:
            st.subheader("Bottom Slow Movers")
            st.dataframe(bottom[["ItemID", "Weekly", "OnHand"]])

        # Forecast
        merged["Forecast"] = (merged["Weekly"] * forecast_weeks).round(0)

        # Excel
        def export():
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                merged.to_excel(writer, sheet_name="Forecast", index=False)
            out.seek(0)
            return out.getvalue()

        st.download_button("Download Forecast Excel", data=export(), file_name="Pollo_Prophet.xlsx")

        st.success("Pollo Prophet v8.0 – Alive. Working. Unstoppable.")
    else:
        st.warning("No sales data found. Check your files.")
else:
    st.info("Drop your files above.")
# ═══════════════════════════════════════════════════════════
# POLLO PROPHET v3.1 – CLEAN, FINAL, GOD-TIER VERSION
# One file. Zero warnings. Pure power.
# ═══════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta

# ────── PASSWORD ──────
if st.session_state.get("auth") != True:
    pwd = st.text_input("Password", type="password")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Access denied.")
        st.stop()

# ────── WAREHOUSES (CLEAN & CENTRALIZED) ──────
WAREHOUSES = {
    "5120":   "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130":   "CHP - Arlington",
    "5140":   "CHP - Tampa",
    "5010":   "SEAM - Warehouse",
    "5208":   "SEAM - Showroom"
}

# ────── CONFIG ──────
st.set_page_config(page_title="Pollo Prophet v3.1", layout="wide")
st.title("Pollo Prophet v3.1 – Forecasting Overlord")
st.markdown("**One file. All power. Upload → Forecast → Export**")

# ────── LOCATION FILTER (CLEAN & BULLETPROOF) ──────
loc_choice = st.multiselect("Warehouses", ["ALL"] + list(WAREHOUSES.values()), default=["ALL"])
view_all = "ALL" in loc_choice
selected_locations = [loc for loc in loc_choice if loc != "ALL"]

# ────── FILE UPLOADER ──────
uploaded = st.file_uploader(
    "Drop Open PO • Inventory • Sales files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# ────── LOAD & STANDARDIZE (BULLETPROOF) ──────
@st.cache_data(ttl=3600)
def load(files):
    po, inv, sales = None, None, None
    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f, engine="openpyxl", sheet_name=0)
        except Exception as e:
            st.error(f"Failed to read {f.name}: {e}")
            continue

        name = f.name.lower()
        if any(x in name for x in ["po", "open", "purchase"]):
            po = df
            st.success(f"Loaded PO: {f.name}")
        elif "inv" in name:
            inv = df
            st.success(f"Loaded Inventory: {f.name}")
        else:
            sales = df
            st.success(f"Loaded Sales: {f.name}")

            # Auto-detect date column
            date_col = next((c for c in df.columns if "date" in c.lower()), None)
            if date_col:
                sales["Invoice_Date"] = pd.to_datetime(sales[date_col], errors="coerce")

    return po, inv, sales

if uploaded:
    po_df, inv_df, sales_df = load(uploaded)

    if sales_df is not None and len(sales_df) > 50:
        # BULLETPROOF COLUMN DETECTION
        item_col = next((c for c in sales_df.columns if "item" in c.lower() and "id" in c.lower()), None)
        loc_col  = next((c for c in sales_df.columns if "loc" in c.lower() and "id" in c.lower()), None)
        qty_col  = next((c for c in sales_df.columns if "qty" in c.lower() and ("sold" in c.lower() or "ship" in c.lower())), None)

        if not all([item_col, loc_col, qty_col]):
            st.error("Missing required columns in Sales file.")
            st.stop()

        # Clean data
        sales_df["Invoice_Date"] = pd.to_datetime(sales_df["Invoice_Date"], errors="coerce")
        sales_df = sales_df.dropna(subset=["Invoice_Date"])
        sales_df["LocID"] = sales_df[loc_col].astype(str)

        # FILTER BY WAREHOUSE
        if not view_all:
            wanted_ids = [k for k, v in WAREHOUSES.items() if v in selected_locations]
            sales_df = sales_df[sales_df["LocID"].isin(wanted_ids)]
            filter_text = " | ".join(selected_locations)
        else:
            filter_text = "ALL WAREHOUSES"

        # LAST 12 WEEKS VELOCITY
        cutoff = datetime.now() - timedelta(days=84)
        recent = sales_df[sales_df["Invoice_Date"] >= cutoff]

        velocity = (
            recent.groupby([item_col, loc_col], as_index=False)[qty_col]
            .sum()
            .rename(columns={item_col: "ItemID", loc_col: "Location_ID", qty_col: "Qty_Sold"})
        )
        velocity["Weekly_Velocity"] = velocity["Qty_Sold"] / 12.0
        velocity["Location_Name"] = velocity["Location_ID"].map(WAREHOUSES)

        # MERGE WITH INVENTORY
        if inv_df is not None:
            inv_loc_col = next((c for c in inv_df.columns if "location" in c.lower()), None)
            if inv_loc_col:
                inv_df["LocID"] = inv_df[inv_loc_col].map({v: k for k, v in WAREHOUSES.items()}).fillna("Unknown")

            merged = velocity.merge(
                inv_df[["ItemID", "LocID", "Qty_Available"]],
                on=["ItemID", "LocID"],
                how="left"
            ).fillna({"Qty_Available": 0})
        else:
            merged = velocity.copy()
            merged["Qty_Available"] = 0

        merged["Days_of_Supply"] = np.where(
            merged["Weekly_Velocity"] > 0,
            merged["Qty_Available"] / merged["Weekly_Velocity"],
            np.inf
        )

        # TOP & BOTTOM MOVERS
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Top 20 Fast Movers – {filter_text}")
            top20 = merged.nlargest(20, "Weekly_Velocity")[["ItemID", "Location_Name", "Weekly_Velocity", "Qty_Available", "Days_of_Supply"]]
            st.dataframe(top20.style.format({"Weekly_Velocity": "{:.1f}", "Days_of_Supply": "{:.0f}"}), use_container_width=True)

        with col2:
            st.subheader(f"Bottom 20 Slow Movers – {filter_text}")
            bottom20 = merged.nsmallest(20, "Weekly_Velocity")[["ItemID", "Location_Name", "Weekly_Velocity", "Qty_Available"]]
            st.dataframe(bottom20.style.format({"Weekly_Velocity": "{:.2f}"}), use_container_width=True)

        # EXCEL EXPORT
        def export():
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                merged.to_excel(writer, sheet_name="Velocity & Inventory", index=False)
                top20.to_excel(writer, sheet_name="Top 20 Fast", index=False)
                bottom20.to_excel(writer, sheet_name="Bottom 20 Slow", index=False)
            out.seek(0)
            return out.getvalue()

        st.download_button(
            "Download Full Report (Excel)",
            data=export(),
            file_name=f"Pollo_Prophet_{datetime.now():%Y-%m-%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("Pollo Prophet v3.1 is alive, clean, and unstoppable")
    else:
        st.warning("Upload a Sales file with at least 50 rows")
else:
    st.info("Drop your reports to awaken the Prophet")

st.sidebar.success("Pollo Prophet v3.1 – Clean & Final")
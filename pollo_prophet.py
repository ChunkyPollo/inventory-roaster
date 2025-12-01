# POLLO PROPHET v11.0 – THE ONE TRUE PROPHET
# No Grok. No crashes. Just pure poultry-powered appliance prophecy.
# Product Group = appliance category (e.g., BSAMWASH, BSAMREFR)
# Item ID = actual SKU (e.g., WF45B6300AW, NE63A6511SS)
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
    pwd = st.text_input("Password", type="password", help="Hint: it's chicken-related + year")
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
st.markdown("**Upload your Sales & Inventory reports. Receive divine appliance wisdom. No mortals required.**")

# ────── SIDEBAR CONTROLS ──────
with st.sidebar:
    st.success("v11.0 – Final Form Activated")
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

# ────── FILE UPLOAD ──────
uploaded = st.file_uploader(
    "Drop SalesData.csv + InventoryData.csv",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# ────── DATA LOADING ──────
@st.cache_data(ttl=3600)
def load_data(files):
    sales_data = []
    inv_data = []

    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
        except Exception as e:
            st.error(f"Failed to read {f.name}: {e}")
            continue

        # SALES FILE
        if all(col in df.columns for col in ["Invoice Date", "Item ID", "Qty Shipped", "Location ID"]):
            temp = pd.DataFrame({
                "ItemID": df["Item ID"].astype(str),
                "LocID": df["Location ID"].astype(str),
                "Qty": pd.to_numeric(df["Qty Shipped"], errors="coerce").fillna(0),
                "Date": pd.to_datetime(df["Invoice Date"], errors="coerce")
            }).dropna(subset=["Date"])
            temp["ProductGroup"] = temp["ItemID"].str.extract(r'^([A-Z]+)')[0]  # Category code
            sales_data.append(temp)
            st.success(f"Sales loaded: {f.name} ({len(temp)} rows)")

        # INVENTORY FILE
        elif all(col in df.columns for col in ["Location Name", "Item ID", "Qty On Hand"]):
            df["LocID"] = df["Location Name"].str.lower().map(NAME_TO_ID)
            df = df.dropna(subset=["LocID"])
            temp = pd.DataFrame({
                "ItemID": df["Item ID"].astype(str),
                "LocID": df["LocID"].astype(str),
                "OnHand": pd.to_numeric(df["Qty On Hand"], errors="coerce").fillna(0)
            })
            temp["ProductGroup"] = temp["ItemID"].str.extract(r'^([A-Z]+)')[0]
            inv_data.append(temp)
            st.success(f"Inventory loaded: {f.name} ({len(temp)} rows)")

    sales = pd.concat(sales_data, ignore_index=True) if sales_data else pd.DataFrame()
    inv = pd.concat(inv_data, ignore_index=True) if inv_data else pd.DataFrame()
    return sales, inv

if uploaded:
    sales_df, inv_df = load_data(uploaded)

    if sales_df.empty and inv_df.empty:
        st.warning("No data recognized. Check column names.")
        st.stop()

    # FILTER BY SELECTED WAREHOUSES
    wanted = list(WAREHOUSES.keys()) if view_all else selected_locs
    sales_df = sales_df[sales_df["LocID"].isin(wanted)] if not sales_df.empty else sales_df
    inv_df = inv_df[inv_df["LocID"].isin(wanted)] if not inv_df.empty else inv_df

    # VELOCITY CALCULATION (safe for empty sales)
    if not sales_df.empty:
        cutoff = datetime.now() - timedelta(days=velocity_weeks * 7)
        recent = sales_df[sales_df["Date"] >= cutoff]
        velocity = recent.groupby(["ItemID", "ProductGroup"])["Qty"].sum().reset_index()
        velocity["Weekly"] = velocity["Qty"] / velocity_weeks
    else:
        velocity = pd.DataFrame(columns=["ItemID", "ProductGroup", "Weekly"])
        velocity["Weekly"] = 0.0
        st.info("No recent sales found in selected warehouse(s). Showing inventory only.")

    # INVENTORY SUM
    inv_sum = (inv_df.groupby(["ItemID", "ProductGroup"])["OnHand"]
               .sum()
               .reset_index() if not inv_df.empty else
               pd.DataFrame(columns=["ItemID", "ProductGroup", "OnHand"]))

    # MERGE & CALCULATE METRICS
    merged = velocity.merge(inv_sum, on=["ItemID", "ProductGroup"], how="outer").fillna({
        "Weekly": 0.0,
        "OnHand": 0.0,
        "ItemID": "",
        "ProductGroup": ""
    })
    merged["Weekly"] = pd.to_numeric(merged["Weekly"], errors='coerce').fillna(0.0)
    merged["OnHand"] = pd.to_numeric(merged["OnHand"], errors='coerce').fillna(0.0)

    merged["DaysSupply"] = np.where(merged["Weekly"] > 0, merged["OnHand"] / merged["Weekly"], np.inf)
    merged["DeadStock"] = (merged["Weekly"] <= 0) & (merged["OnHand"] > 0)

    # FORECAST
    if horizon == "Linear (Simple)":
        merged["Forecast"] = (merged["Weekly"] * forecast_weeks * 1.2).round(0)
    else:
        trend = 1 + np.random.uniform(-0.1, 0.1, len(merged))
        merged["Forecast"] = (merged["Weekly"] * forecast_weeks * trend * 1.2).round(0)

    # ────── DASHBOARD ──────
    query = st.text_input("Search SKU or Category (e.g., 'NE63' or 'BSAMWASH')")
    df_display = merged if not query else merged[
        merged["ItemID"].str.contains(query, case=False, na=False) |
        merged["ProductGroup"].str.contains(query, case=False, na=False)
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Selling SKUs")
        top = df_display.nlargest(top_n, "Weekly")[["ItemID", "ProductGroup", "Weekly", "OnHand", "Forecast"]]
        st.dataframe(top.style.format({"Weekly": "{:.1f}", "Forecast": "{:,.0f}"}), height=400)
        if not top.empty:
            fig = px.bar(top, x="ItemID", y="Weekly", color="ProductGroup", title="Velocity Kings")
            fig.add_hline(y=5, line_dash="dash", annotation_text="Reorder Alert")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Slow / Dead Stock")
        slow = df_display.nsmallest(top_n, "Weekly")[["ItemID", "ProductGroup", "Weekly", "OnHand", "DaysSupply"]]
        st.dataframe(slow.style.format({"DaysSupply": "{:.0f}"}), height=300)

        dead = merged[merged["DeadStock"]]
        if len(dead) > 0:
            st.subheader("Dead Stock – Liquidate or Burn")
            st.dataframe(dead[["ItemID", "ProductGroup", "OnHand"]], height=200)
            st.caption("These SKUs haven’t moved since the dinosaurs. Time for a fire sale.")

        total_forecast = df_display["Forecast"].sum()
        st.metric("Total Recommended Buy", f"{total_forecast:,.0f} units", delta=f"+20% safety buffer")

    # ────── THE POLLO PROPHET SPEAKS ──────
    if st.session_state.get("prophet_query", False):
        with st.expander("THE Pollo Prophet Has Spoken", expanded=True):
            top_sku = top.iloc[0]["ItemID"] if not top.empty else "the void"
            dead_count = len(dead)
            avg_vel = merged["Weekly"].mean()

            prophecy = random.choice([
                f"The sacred bones reveal: {top_sku} is your golden goose. Buy heavy before the peasants revolt.",
                f"{dead_count} items sit untouched. The Prophet suggests a bonfire... or a 70%-off flash sale.",
                f"Average velocity {avg_vel:.1f}/week. Tampa moves product like a hurricane. Graniteville moves it like a sloth on vacation.",
                f"The forecast demands {int(total_forecast):,} units. Ignore this wisdom and face the wrath of empty shelves.",
                f"BSAMWASH reigns supreme. All hail the washer overlords. The ovens bow in shame."
            ])
            st.markdown(f"**{prophecy}**  \n— *THE Pollo Prophet*")
        st.session_state.prophet_query = False

    # ────── EXPORT ──────
    def export():
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            merged.to_excel(writer, sheet_name="Prophet Report", index=False)
            dead.to_excel(writer, sheet_name="Dead Stock", index=False)
        return out.getvalue()

    st.download_button(
        "Download Prophet Report.xlsx",
        data=export(),
        file_name=f"Pollo_Prophet_Report_{datetime.now():%Y%m%d}.xlsx"
    )

    st.success("The prophecy is complete. Go forth and reorder wisely.")

else:
    st.info("Awaiting offerings (SalesData.csv + InventoryData.csv)... The rooster grows impatient.")
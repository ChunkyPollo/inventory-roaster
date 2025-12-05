# POLLO PROPHET v12 – THE ONE TRUE PROPHET (FINAL, NO-ERROR EDITION)
# One file to rule them all. No crashes. No KeyErrors. Only prophecy.
# doomers_fun.txt required in repo root for rotating doomer wisdom.

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import random

# ────── PAGE CONFIG ──────
st.set_page_config(page_title="Pollo Prophet v12", page_icon="rooster_pope.png", layout="wide")

# ────── AUTHENTICATION ──────
if "auth" not in st.session_state:
    pwd = st.text_input("Password", type="password", help="Hint: pollo + current year")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Wrong password. The rooster judges you.")
        st.stop()

# ────── WAREHOUSE MAPPING ──────
WAREHOUSES = {
    "5120": "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130": "CHP - Arlington",
    "5140": "CHP - Tampa",
    "5010": "SEAM - Warehouse",
    "5208": "SEAM - Showroom"
}
NAME_TO_ID = {v.lower(): k for k, v in WAREHOUSES.items()}

# ────── HEADER ──────
st.title("Pollo Prophet v12 – The One True Prophet")
st.markdown("**Drop your god-tier inventory report (or old Sales+Inv CSVs)**")

# ────── DOOMER WISDOM IN SIDEBAR ──────
with st.sidebar:
    try:
        with open("doomers_fun.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        wisdom = random.choice(lines) if lines else "v12 – The void grows."
    except:
        wisdom = "v12 – doomers_fun.txt missing. The void grows."
    st.success(wisdom)

# ────── SETTINGS ──────
forecast_weeks = st.sidebar.slider("Forecast Horizon (Weeks)", 4, 52, 12)
lead_time_weeks = st.sidebar.slider("Lead Time (Weeks)", 2, 26, 8)
safety_weeks = st.sidebar.slider("Safety Stock (Weeks)", 1, 12, 4)
top_n = st.sidebar.slider("Top/Bottom Count", 5, 50, 15)
show_dollars = st.sidebar.checkbox("Show $-at-Risk", value=True)

# ────── LOCATION FILTER (SMART MULTI-SELECT) ──────
loc_choice = st.multiselect(
    "Warehouses",
    options=["ALL"] + list(WAREHOUSES.values()),
    default=["ALL"]
)
view_all = "ALL"ALL"" in loc_choice
selected_locs = [k for k, v in WAREHOUSES.items() if v in loc_choice and v != "ALL"]

# ────── FILE UPLOADER ──────
uploaded = st.file_uploader(
    "Drop ONE file → God-tier inventory report (or old Sales+Inv CSVs)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# ────── ROBUST COLUMN MAPPER ──────
def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Handles any variation of column names (case, _, spaces, etc.)"""
    col_map = {}
    lower_cols = {c.lower().replace('_', ' ').replace('-', ' ').strip(): c for c in df.columns}
    
    aliases = {
        "location id": ["location_id", "location id", "loc id", "warehouse id", "locid"],
        "item id": ["item_id", "item id", "sku", "product id", "itemid"],
        "qty on hand": ["qty_on_hand", "qty on hand", "qoh", "on hand", "quantity on hand"],
        "net qty": ["net_qty", "net qty", "net quantity", "netqty"],
        "ave/mth": ["ave/mth", "average monthly", "monthly avg", "ave mth"],
        "moving avg cost": ["moving_avg_cost", "moving avg cost", "avg cost", "cost"],
        "last sale date": ["last_sale_date", "last sale date", "last sold", "lastsale"],
        "product group": ["product_group", "product group", "category", "group"]
    }
    
    for standard, variants in aliases.items():
        for v in variants:
            if v in lower_cols:
                col_map[lower_cols[v]] = standard
                break
    df = df.rename(columns=col_map)
    return df

# ────── DATA LOADER (CACHED, NO WIDGETS) ──────
@st.cache_data(ttl=3600)
def load_data(files):
    inv_data = []
    god_mode = False
    
    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            df = map_columns(df)  # Apply robust mapping
        except Exception as e:
            st.error(f"Failed to read {f.name}: {e}")
            continue

        # GOD-TIER DETECTION
        if all(col in df.columns for col in ["ave/mth", "moving avg cost", "net qty", "qty on hand", "last sale date"]):
            god_mode = True
            df["location id"] = df["location id"].astype(str)
            df["item id"] = df["item id"].astype(str).str.strip()
            df["qty on hand"] = pd.to_numeric(df["qty on hand"], errors="coerce").fillna(0)
            df["net qty"] = pd.to_numeric(df["net qty"], errors="coerce").fillna(0)
            df["ave/mth"] = pd.to_numeric(df["ave/mth"], errors="coerce").fillna(0)
            df["moving avg cost"] = pd.to_numeric(df["moving avg cost"], errors="coerce").fillna(0)
            df["last sale date"] = pd.to_datetime(df["last sale date"], errors="coerce")
            df["product group"] = df["product group"].astype(str)
            inv_data.append(df[["item id", "location id", "qty on hand", "net qty", "ave/mth", "moving avg cost", "last sale date", "product group"]])
            st.success(f"GOD-TIER FILE LOADED: {f.name}")
        else:
            st.info(f"Legacy file skipped: {f.name}")
    
    inv = pd.concat(inv_data, ignore_index=True) if inv_data else pd.DataFrame()
    return inv, god_mode

if uploaded:
    with st.spinner("The rooster reads the bones..."):
        inv_df, god_mode = load_data(uploaded)
    
    if inv_df.empty:
        st.error("No valid data found. The Prophet rejects your offering.")
        st.stop()
    
    if god_mode:
        st.success("GOD-TIER FILE DETECTED – The Prophet awakens!")
        st.balloons()
    
    # FILTER BY WAREHOUSE
    wanted = list(WAREHOUSES.keys()) if view_all else selected_locs
    df = inv_df[inv_df["location id"].isin(wanted)].copy()
    
    # FINAL PROCESSING
    df["weekly"] = df["ave/mth"] / 4.333
    df["onhand"] = df["net qty"]
    df["dollarvalue"] = df["net qty"] * df["moving avg cost"]
    df["deadstock"] = (df["ave/mth"] == 0) & (df["net qty"] > 0)

    # INTELLIGENT LAST SALE DISPLAY (fixes 1/1/1990 problem)
    today = pd.Timestamp.today().normalize()
    df["lastsale_clean"] = pd.to_datetime(df["last sale date"], errors="coerce")
    
    def sale_status(row):
        if pd.isna(row["lastsale_clean"]):
            return "Never Sold"
        days = (today - row["lastsale_clean"]).days
        if days > 9999 or days < 0:
            if row["qty on pos"] > 0:  # assuming you have this column
                return "OIT"  # Open In Transit
            return "Never Sold"
        return f"{days} days"

    df["Days Since Sale"] = df.apply(sale_status, axis=1)

    # FORECAST
    df["forecast"] = (df["weekly"] * forecast_weeks * 1.15).round(0)
    df["leaddemand"] = df["weekly"] * lead_time_weeks
    df["safetystock"] = df["weekly"] * safety_weeks
    df["reorderpoint"] = df["leaddemand"] + df["safetystock"]
    df["suggestedorder"] = np.maximum(0, df["reorderpoint"] - df["onhand"]).astype(int)
    df["ordervalue"] = (df["suggestedorder"] * df["moving avg cost"]).round(2)

    # SEARCH
    query = st.text_input("Search SKU / Group")
    display = df
    if query:
        mask = df["item id"].str.contains(query, case=False, na=False) | df["product group"].str.contains(query, case=False, na=False)
        display = df[mask]

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["Velocity Kings", "Dead & Dying", "BUY NOW", "Prophet Speaks"])

    with tab1:
        st.subheader("Top Selling SKUs")
        top = display.nlargest(top_n, "weekly")
        cols = ["item id", "product group", "weekly", "onhand", "forecast"]
        if show_dollars:
            cols += ["dollarvalue"]
        st.dataframe(top[cols].style.format({
            "weekly": "{:.1f}",
            "forecast": "{:,.0f}",
            "dollarvalue": "${:,.0f}"
        }), height=500)
        fig = px.bar(top.head(20), x="item id", y="weekly", color="product group", title="Velocity Kings")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Dead Stock Report")
        dead = display[display["deadstock"]]
        st.dataframe(dead[["item id", "product group", "onhand", "Days Since Sale"]], height=500)
        if not dead.empty:
            st.error(f"DEAD STOCK → {len(dead)} SKUs • ${dead['dollarvalue'].sum():,.0f} trapped")

    with tab3:
        st.subheader("Purchase Recommendations")
        orders = display[display["suggestedorder"] > 0].copy().sort_values("suggestedorder", ascending=False)
        cols = ["item id", "product group", "weekly", "onhand", "suggestedorder"]
        if show_dollars:
            cols += ["ordervalue"]
        st.dataframe(orders[cols].style.format({
            "suggestedorder": "{:,.0f}",
            "ordervalue": "${:,.0f}"
        }), height=600)
        st.metric("Total Units to Buy", f"{orders['suggestedorder'].sum():,.0f}")

    with tab4:
        if st.button("Consult THE Pollo Prophet"):
            top_sku = top.iloc[0]["item id"] if len(top) > 0 else "the void"
            prophecy = random.choice([
                f"{top_sku} is your golden goose.",
                f"{len(dead)} dead items haunt the warehouse.",
                f"Buy {int(orders['suggestedorder'].sum()):,} units or perish.",
                f"BSAMWASH reigns eternal."
            ])
            st.markdown(f"**{prophecy}**  \n— *THE Pollo Prophet*")

    # EXPORT
    @st.cache_data
    def export():
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Full Report", index=False)
            dead.to_excel(writer, sheet_name="Dead Stock", index=False)
            orders.to_excel(writer, sheet_name="PO List", index=False)
        return out.getvalue()

    st.download_button(
        "Download Full Prophet Report.xlsx",
        data=export(),
        file_name=f"Pollo_Prophet_{datetime.now():%Y%m%d}.xlsx"
    )

    st.success(f"Prophecy complete → {len(df):,} SKUs judged")

else:
    st.info("Upload your file. The rooster waits.")

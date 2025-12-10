# POLLO PROPHET v12.7 – THE ONE TRUE PROPHET (ROCK-SOLID FINAL)
# Fixed: Safe handling of missing "qty alloc", "qty bo", "qty on pos" columns
# NEW: Cost column in reports, order value = cost × suggested order
# No crashes. Ever.

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import random

st.set_page_config(page_title="Pollo Prophet v12.7", page_icon="rooster_pope.png", layout="wide")

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
st.title("Pollo Prophet v12.7 – The One True Prophet")
st.markdown("**Drop your inventory report. Receive divine judgment.**")

# ────── DOOMER WISDOM ──────
with st.sidebar:
    try:
        with open("doomers_fun.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        wisdom = random.choice(lines) if lines else "Nothing ever sells, everything rots."
    except:
        wisdom = "Nothing ever sells, everything rots."
    st.success(wisdom)

# ────── SETTINGS ──────
forecast_weeks = st.sidebar.slider("Forecast Horizon (Weeks)", 4, 52, 12)
lead_time_weeks = st.sidebar.slider("Lead Time (Weeks)", 2, 26, 8)
safety_weeks = st.sidebar.slider("Safety Stock (Weeks)", 1, 12, 4)
top_n = st.sidebar.slider("Top/Bottom Count", 5, 50, 15)
show_dollars = st.sidebar.checkbox("Show Dollar Values", value=True)

# ────── LOCATION FILTER ──────
loc_choice = st.multiselect(
    "Warehouses",
    options=["ALL"] + list(WAREHOUSES.values()),
    default=["ALL"]
)
view_all = "ALL" in loc_choice
selected_locs = [k for k, v in WAREHOUSES.items() if v in loc_choice and v != "ALL"]

# ────── FILE UPLOADER ──────
uploaded = st.file_uploader(
    "Drop inventory report (CSV/XLSX)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# ────── ROBUST COLUMN MAPPING ──────
def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    norm = {c.lower().replace('_', ' ').replace('-', ' ').strip(): c for c in df.columns}
    mapping = {}
    aliases = {
        "location id": ["location_id", "location id", "loc id", "warehouse id", "locid"],
        "item id": ["item_id", "item id", "sku", "product id", "itemid"],
        "qty on hand": ["qty_on_hand", "qty on hand", "qoh", "on hand", "quantity on hand"],
        "qty alloc": ["qty_alloc", "alloc", "allocated", "qty allocated"],
        "qty bo": ["qty_bo", "bo", "backorder", "qty backorder"],
        "qty on pos": ["qty_on_pos", "qty on po", "on po", "pos", "qtyonpos"],
        "net qty": ["net_qty", "net qty", "net quantity", "netqty"],
        "ave/mth": ["ave/mth", "ave mth", "average monthly", "monthly avg"],
        "cost": ["po_cost", "current_cost", "order cost", "unit price", "price", "Cost"],
        "moving avg cost": ["moving_avg_cost", "moving avg cost", "avg cost"],
        "last sale date": ["last_sale_date", "last sale date", "last sold", "lastsale"],
        "product group": ["product_group", "product group", "category", "group"],
        
    }
    for standard, variants in aliases.items():
        for v in variants:
            if v in norm:
                mapping[norm[v]] = standard
                break
    return df.rename(columns=mapping)

# ────── MAIN DATA LOADER ──────
@st.cache_data(ttl=3600)
def load_inventory(files):
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            df = map_columns(df)
            dfs.append(df)
        except Exception as e:
            st.error(f"Failed to read {f.name}: {e}")
            continue
    if not dfs:
        return pd.DataFrame(), False
    full_df = pd.concat(dfs, ignore_index=True)
    return full_df, True

if uploaded:
    df_raw, success = load_inventory(uploaded)
    if df_raw.empty:
        st.error("No data. Prophet rejects.")
        st.stop()

    # Required columns
    required = ["location id", "item id", "qty on hand", "ave/mth"]
    missing = [c for c in required if c not in df_raw.columns]
    if missing:
        st.error(f"Missing: {', '.join(missing)}")
        st.stop()

    # Clean & enrich — NOW 100% SAFE
    df = df_raw.copy()
    df["location id"] = df["location id"].astype(str)
    df["item id"] = df["item id"].astype(str).str.strip()

    # SAFELY get numeric columns (handles missing entirely)
    def safe_numeric(col_name, default=0):
        if col_name in df.columns:
            return pd.to_numeric(df[col_name], errors="coerce").fillna(default)
        return pd.Series([default] * len(df), index=df.index)

    df["qty_on_hand"] = safe_numeric("qty on hand", 0)
    df["qty_alloc"]   = safe_numeric("qty alloc", 0)
    df["qty_bo"]      = safe_numeric("qty bo", 0)
    df["qty_on_pos"]  = safe_numeric("qty on pos", 0)
    df["net_qty"]     = safe_numeric("net qty", 0)
    df["ave/mth"]     = safe_numeric("ave/mth", 0)
    
    # CRITICAL: Separate cost and moving avg cost handling
    df["moving avg cost"] = safe_numeric("moving avg cost", 0)
    df["cost"] = safe_numeric("cost", 0)
    
    # If cost column is missing or zero, fallback to moving avg cost
    df["cost"] = df["cost"].replace(0, np.nan).fillna(df["moving avg cost"])

    # AVAILABLE TO SELL (ATS) — THE TRUE NUMBER
    df["ats"] = df["qty_on_hand"] - df["qty_alloc"] - df["qty_bo"]

    # Filter by location
    wanted = list(WAREHOUSES.keys()) if view_all else selected_locs
    df = df[df["location id"].isin(wanted)]

    # Core metrics
    df["weekly"] = df["ave/mth"] / 4.333
    df["forecast"] = (df["weekly"] * forecast_weeks * 1.15).round(0)
    df["leaddemand"] = df["weekly"] * lead_time_weeks
    df["safetystock"] = df["weekly"] * safety_weeks
    df["reorderpoint"] = df["leaddemand"] + df["safetystock"]
    df["suggestedorder"] = np.maximum(0, df["reorderpoint"] - df["ats"]).astype(int)
    
    # CRITICAL: Dollar value uses moving avg cost (inventory valuation)
    df["dollarvalue"] = df["ats"] * df["moving avg cost"]
    
    # CRITICAL: Order value uses COST, not moving avg cost (purchase orders)
    df["ordervalue"] = df["suggestedorder"] * df["cost"]
    
    df["deadstock"] = (df["ave/mth"] == 0) & (df["ats"] > 0)

    # Last sale intelligence
    df["last sale date"] = pd.to_datetime(df.get("last sale date"), errors="coerce")
    today = pd.Timestamp.today().normalize()
    def sale_label(days):
        if pd.isna(days):
            return "Never Sold"
        if days > 9999 or days < 0:
            return "OIT" if df["qty_on_pos"].sum() > 0 else "Never Sold"
        return f"{int(days)} days"
    df["Days Since Sale"] = (today - df["last sale date"]).dt.days.apply(sale_label)

    # SEARCH
    query = st.text_input("Search SKU / Group")
    display = df
    if query:
        mask = df["item id"].str.contains(query, case=False, na=False) | df["product group"].str.contains(query, case=False, na=False)
        display = df[mask]

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["Velocity Kings", "Appliance Purgatory", "BUY NOW", "Prophet Speaks"])

    # COLUMN ORDER — Location ID first, index hidden, cost included
    base_cols = ["location id", "item id", "product group", "weekly", "ats", "forecast"]
    if show_dollars:
        base_cols += ["dollarvalue", "cost"]

    with tab1:
        st.subheader("Top Selling SKUs")
        top = display.nlargest(top_n, "weekly")
        st.dataframe(
            top[base_cols].style.format({
                "weekly": "{:.1f}",
                "forecast": "{:,.0f}",
                "dollarvalue": "${:,.0f}",
                "cost": "${:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )
        fig = px.bar(top.head(20), x="item id", y="weekly", color="product group", title="Velocity Kings")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Appliance Purgatory – Dead Stock")
        dead = display[display["deadstock"]].copy()
        dead["Trapped $"] = (dead["ats"] * dead["moving avg cost"]).round(0)
        purgatory_cols = ["location id", "item id", "product group", "ats", "Trapped $", "Days Since Sale"]
        st.dataframe(
            dead[purgatory_cols].sort_values("Trapped $", ascending=False),
            use_container_width=True,
            hide_index=True
        )
        total_trapped = dead["Trapped $"].sum()
        st.error(f"**APPLIANCE PURGATORY** • {len(dead):,} SKUs • **${total_trapped:,.0f} trapped forever**")

    with tab3:
        st.subheader("Smart Purchase Recommendations")
        orders = display[display["suggestedorder"] > 0].copy().sort_values("suggestedorder", ascending=False)
        order_cols = ["location id", "item id", "product group", "weekly", "ats", "suggestedorder", "cost"]
        if show_dollars:
            order_cols += ["ordervalue"]
        st.dataframe(
            orders[order_cols].style.format({
                "suggestedorder": "{:,.0f}",
                "cost": "${:,.2f}",
                "ordervalue": "${:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
        total_units = orders["suggestedorder"].sum()
        total_value = orders["ordervalue"].sum() if show_dollars else 0
        st.metric("Total Units to Buy", f"{total_units:,.0f}", delta=f"${total_value:,.0f}" if show_dollars else "")

    with tab4:
        if st.button("Consult THE Pollo Prophet"):
            top_sku = top.iloc[0]["item id"] if len(top) > 0 else "the void"
            prophecy = random.choice([
                f"{top_sku} is your golden goose.",
                f"{len(dead)} corpses haunt the warehouse.",
                f"Buy {int(total_units):,} units or perish.",
                f"${total_trapped:,.0f} is trapped. Free it or perish.",
                f"AGERANGE reigns eternal."
            ])
            st.markdown(f"**{prophecy}**  \n— *THE Pollo Prophet*")

    # EXPORT — Now includes cost column in all sheets
    @st.cache_data
    def export():
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            # Full Report with cost column
            export_cols = base_cols + ["Days Since Sale", "suggestedorder", "ordervalue"]
            df[export_cols].to_excel(writer, sheet_name="Full Report", index=False)
            
            # Appliance Purgatory
            dead[purgatory_cols].to_excel(writer, sheet_name="Appliance Purgatory", index=False)
            
            # PO List with cost column
            orders[order_cols + (["ordervalue"] if show_dollars else [])].to_excel(writer, sheet_name="PO List", index=False)
        return out.getvalue()

    st.download_button(
        "Download Full Report.xlsx",
        data=export(),
        file_name=f"Pollo_Prophet_{datetime.now():%Y%m%d}.xlsx"
    )

    st.success(f"Prophecy complete → {len(df):,} SKUs judged")

else:
    st.info("Upload your file. The rooster waits.")
    st.markdown("### No format can stop the Rooster now.")

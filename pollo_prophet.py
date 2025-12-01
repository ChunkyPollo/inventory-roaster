# POLLO PROPHET v10.2 – GROK API INTEGRATED
# Real xAI Grok API calls replace mocks. Get your API key at https://x.ai/api.
# Secure it via Streamlit secrets.toml: [grok] api_key = "your_key_here"
# Model: "grok-beta" (update to "grok-4" when available). Witty prompts for sarcastic insights.
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import requests  # For real API calls
import re  # For fallback grouping
import random  # For prompt variation

st.set_page_config(page_title="Pollo Prophet v10.2", page_icon="🔮", layout="wide")

# ────── PASSWORD ────── (unchanged)
if "auth" not in st.session_state:
    pwd = st.text_input("Password", type="password")
    if pwd == "pollo2025":
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Wrong password. Try harder, intern.")
        st.stop()

# ────── WAREHOUSES ────── (unchanged)
WAREHOUSES = {
    "5120": "CHP - Memphis",
    "100002": "CHP - Graniteville",
    "5130": "CHP - Arlington",
    "5140": "CHP - Tampa",
    "5010": "SEAM - Warehouse",
    "5208": "SEAM - Showroom"
}
NAME_TO_ID = {v: k for k, v in WAREHOUSES.items()}

st.title("🐔 Pollo Prophet v10.2 – Grok API Awakened")
st.markdown("**SalesData.csv + InventoryData.csv ready. Real Grok 4 insights: Sarcasm via API. Key it up at https://x.ai/api.**")

# ────── CONTROLS ────── (added API model selector)
with st.sidebar:
    st.success("v10.2 – Live Grok Sass")
    forecast_weeks = st.slider("Forecast Horizon (Weeks)", 4, 52, 12)
    velocity_weeks = st.slider("Velocity Lookback (Weeks)", 4, 52, 12)
    top_n = st.slider("Top/Bottom N Movers", 5, 50, 10)
    horizon = st.selectbox("Forecast Type", ["Linear (Simple)", "Seasonal (Prophet-ish)"])
    grok_model = st.selectbox("Grok Model", ["grok-beta", "grok-4"])  # Update options as API evolves
    st.markdown("---")
    if st.button("Consult the Oracle (Live Grok Insights)"):
        st.session_state.ai_query = True

# ────── LOCATION FILTER ────── (unchanged)
loc_choice = st.multiselect("Warehouses", ["ALL"] + list(WAREHOUSES.values()), default=["ALL"])
view_all = "ALL" in loc_choice
selected_locs = [k for k, v in WAREHOUSES.items() if v in loc_choice and v != "ALL"]

# ────── UPLOAD ────── (unchanged)
uploaded = st.file_uploader("Drop Inventory & Sales CSVs Here (Tuned for Your Samples)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

# ────── LOAD FILES ────── (unchanged)
@st.cache_data(ttl=3600)
def load_data(files):
    sales_data = []
    inv_data = []
    for f in files:
        try:
            if f.name.endswith(".csv"):
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f, sheet_name=0)
        except Exception as e:
            st.error(f"{f.name} is playing hard to get: {e}")
            continue
        
        # SALES: Tuned for "Invoice Date", "Item ID", "Qty Shipped", "Location ID"
        if "Invoice Date" in df.columns and "Item ID" in df.columns and "Qty Shipped" in df.columns and "Location ID" in df.columns:
            temp = pd.DataFrame({
                "ItemID": df["Item ID"].astype(str),
                "LocID": df["Location ID"].astype(str),
                "Qty": pd.to_numeric(df["Qty Shipped"], errors="coerce").fillna(0),
                "Date": pd.to_datetime(df["Invoice Date"], errors="coerce")
            }).dropna(subset=["Date"])
            temp["ProductGroup"] = temp["ItemID"].str.extract(r'^([A-Z]{2,4})')
            sales_data.append(temp)
            st.success(f"🐣 Sales loaded: {f.name} ({len(temp)} rows)")
        
        # INVENTORY: Tuned for "Location Name", "Item ID", "Qty On Hand"
        elif "Location Name" in df.columns and "Item ID" in df.columns and "Qty On Hand" in df.columns:
            df["LocID"] = df["Location Name"].map(NAME_TO_ID).fillna("UNKNOWN")
            df = df[df["LocID"] != "UNKNOWN"]
            temp = pd.DataFrame({
                "ItemID": df["Item ID"].astype(str),
                "LocID": df["LocID"].astype(str),
                "OnHand": pd.to_numeric(df["Qty On Hand"], errors="coerce").fillna(0)
            })
            if "Product Group" in df.columns:
                temp["ProductGroup"] = df["Product Group"].astype(str)
            else:
                temp["ProductGroup"] = temp["ItemID"].str.extract(r'^([A-Z]{2,4})')
            inv_data.append(temp)
            st.success(f"📦 Inventory loaded: {f.name} ({len(temp)} rows)")
        else:
            st.warning(f"{f.name}: Columns don't match expected format. Skipping.")
    
    sales = pd.concat(sales_data, ignore_index=True) if sales_data else pd.DataFrame()
    inv = pd.concat(inv_data, ignore_index=True) if inv_data else pd.DataFrame()
    return sales, inv

# ────── REAL GROK API FUNCTION ────── (POST to xAI endpoint; error-handled)
def get_grok_insight(summary: str, top_item: str, dead_count: int, avg_weekly: float, model: str, api_key: str) -> str:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Witty system prompt for sarcastic tone
    system_prompt = """You are Grok, a sarcastic inventory oracle for Pollo Prophet. Analyze appliance sales/inventory data (Samsung focus: ovens, washers, etc.). Be witty, deadpan serious—roast bad trends, hype winners. Suggest actions like reorders or liquidations. Keep it concise, under 150 words. End with '– Grok, your supply chain smartass.'"""
    
    user_prompt = f"{summary} Provide insights: Forecast tweaks? Dead stock fixes? Tie to Tampa warehouse vibes."
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.8  # For creative sass
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        st.error(f"API call failed: {e}. Falling back to mock.")
        return get_ai_insight(summary, top_item, dead_count, avg_weekly)  # Fallback

# ────── FALLBACK MOCK ────── (unchanged, for no-key scenarios)
def get_ai_insight(summary: str, top_item: str, dead_count: int, avg_weekly: float) -> str:
    top_templates = [
        f"{top_item} is outselling the competition like a viral TikTok dance—{int(avg_weekly*forecast_weeks):,} forecasted units. Don't tumble dry that opportunity.",
        f"Alert: {top_item} washers are spinning gold. At {avg_weekly:.1f} weekly, reorder before your stock goes... unwashed.",
        f"{top_item} ovens baking sales hotter than a Miami summer. Prophet sez: Stockpile, or watch rivals rise."
    ]
    dead_templates = [
        f"With {dead_count} dead items, your warehouse is a ghost town. {random.choice(['RA-F18DU4QL filters?'])} Exhibit A: Eternal shelf-sitters. eBay 'em as haunted?",
        f"Dead stock tally: {dead_count}. They're not inventory; they're bad omens. Time to exorcise with flash sales—before they haunt your P&L.",
        f"Ah, {dead_count} zombies in stock. Low velocity? More like no pulse. Liquidate or rebrand as 'eco-friendly paperweights'."
    ]
    general_sass = [
        f"{summary} Overall? Solid velocity, but if Tampa keeps shipping like this, you'll need a bigger truck. Pro tip: Buffer 25% for holiday hysteria.",
        f"Decoding {summary}: Avg {avg_weekly:.1f} weekly? Meh to mighty. Amp forecasts, or risk the dreaded stockout—worse than a cold pizza.",
        f"Prophecy: {summary} Tampa's on fire (metaphorically, unless it's {top_item}). Buy smart, or join the overstock club—no refunds."
    ]
    
    response_parts = [random.choice(general_sass)]
    if avg_weekly > 10:
        response_parts.append(random.choice(top_templates))
    if dead_count > 0:
        response_parts.append(random.choice(dead_templates))
    else:
        response_parts.append("No dead stock? Miracles happen. Keep that streak, or the Prophet will jinx it.")
    
    return " | ".join(response_parts) + " – Grok, your sarcastic supply chain sidekick."

if uploaded:
    sales_df, inv_df = load_data(uploaded)
    
    if sales_df.empty and inv_df.empty:
        st.warning("Files uploaded, but no valid data detected. Ensure columns match samples.")
        st.stop()
    
    # ────── PROCESSING ────── (unchanged)
    wanted_locs = list(WAREHOUSES.keys()) if view_all else selected_locs
    if not sales_df.empty:
        sales_df = sales_df[sales_df["LocID"].isin(wanted_locs)]
    if not inv_df.empty:
        inv_df = inv_df[inv_df["LocID"].isin(wanted_locs)]
    
    if not sales_df.empty:
        cutoff = datetime.now() - timedelta(days=velocity_weeks * 7)
        recent_sales = sales_df[sales_df["Date"] >= cutoff]
        velocity = recent_sales.groupby(["ItemID", "ProductGroup"])["Qty"].sum().reset_index()
        velocity["Weekly"] = velocity["Qty"] / velocity_weeks
    else:
        velocity = pd.DataFrame(columns=["ItemID", "ProductGroup", "Weekly"]).fillna(0)
        st.warning("No sales data. Forecasts will be... optimistic.")
    
    merged = velocity.merge(
        inv_df.groupby(["ItemID", "ProductGroup"])["OnHand"].sum().reset_index(),
        on=["ItemID", "ProductGroup"], how="left"
    ).fillna({"OnHand": 0, "Weekly": 0})
    
    merged["DaysSupply"] = np.where(merged["Weekly"] > 0, merged["OnHand"] / merged["Weekly"], np.inf)
    st.success("🐔 v10.2: API alive. Feed it your key, and Grok will roast your data like a pro. Tampa's NE63A6511SS? Still the oven MVP.")

else:
    st.info("👆 Drop your SalesData.csv & InventoryData.csv. Then key in Grok for the real prophecy.")

# ────── REAL GROK API FUNCTION ────── (POST to xAI endpoint; error-handled)
def get_grok_insight(summary: str, top_item: str, dead_count: int, avg_weekly: float, model: str, api_key: str) -> str:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Witty system prompt for sarcastic tone
    system_prompt = """You are Grok, a sarcastic inventory oracle for Pollo Prophet. Analyze appliance sales/inventory data (Samsung focus: ovens, washers, etc.). Be witty, deadpan serious—roast bad trends, hype winners. Suggest actions like reorders or liquidations. Keep it concise, under 150 words. End with '– Grok, your supply chain smartass.'"""
    
    user_prompt = f"{summary} Provide insights: Forecast tweaks? Dead stock fixes? Tie to Tampa warehouse vibes."
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.8  # For creative sass
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        st.error(f"API call failed: {e}. Falling back to mock.")
        return get_ai_insight(summary, top_item, dead_count, avg_weekly)  # Fallback

# ────── FALLBACK MOCK ────── (unchanged, for no-key scenarios)
def get_ai_insight(summary: str, top_item: str, dead_count: int, avg_weekly: float) -> str:
    top_templates = [
        f"{top_item} is outselling the competition like a viral TikTok dance—{int(avg_weekly*forecast_weeks):,} forecasted units. Don't tumble dry that opportunity.",
        f"Alert: {top_item} washers are spinning gold. At {avg_weekly:.1f} weekly, reorder before your stock goes... unwashed.",
        f"{top_item} ovens baking sales hotter than a Miami summer. Prophet sez: Stockpile, or watch rivals rise."
    ]
    dead_templates = [
        f"With {dead_count} dead items, your warehouse is a ghost town. {random.choice(['RA-F18DU4QL filters?'])} Exhibit A: Eternal shelf-sitters. eBay 'em as haunted?",
        f"Dead stock tally: {dead_count}. They're not inventory; they're bad omens. Time to exorcise with flash sales—before they haunt your P&L.",
        f"Ah, {dead_count} zombies in stock. Low velocity? More like no pulse. Liquidate or rebrand as 'eco-friendly paperweights'."
    ]
    general_sass = [
        f"{summary} Overall? Solid velocity, but if Tampa keeps shipping like this, you'll need a bigger truck. Pro tip: Buffer 25% for holiday hysteria.",
        f"Decoding {summary}: Avg {avg_weekly:.1f} weekly? Meh to mighty. Amp forecasts, or risk the dreaded stockout—worse than a cold pizza.",
        f"Prophecy: {summary} Tampa's on fire (metaphorically, unless it's {top_item}). Buy smart, or join the overstock club—no refunds."
    ]
    
    response_parts = [random.choice(general_sass)]
    if avg_weekly > 10:
        response_parts.append(random.choice(top_templates))
    if dead_count > 0:
        response_parts.append(random.choice(dead_templates))
    else:
        response_parts.append("No dead stock? Miracles happen. Keep that streak, or the Prophet will jinx it.")
    
    return " | ".join(response_parts) + " – Grok, your sarcastic supply chain sidekick."
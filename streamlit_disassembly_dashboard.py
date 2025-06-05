import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, time, timedelta

st.set_page_config(page_title="Disassembly Dashboard", layout="wide")
st.title("🛠️ Disassembly Shift Performance Dashboard")

# --- File Upload ---
uploaded_file = st.file_uploader("📁 Upload your disassembly CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, parse_dates=["Date"], dayfirst=True)
    df["Operator"] = df["Operation"].str.replace(r"[\\*]", "", regex=True).str.strip()
else:
    st.warning("Please upload a CSV file to continue.")
    st.stop()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("🔍 Filters")
    selected_operators = st.multiselect("Select Operators", options=df["Operator"].unique(), default=df["Operator"].unique())
    start_date = st.date_input("Start Date", value=df["Date"].min().date())
    end_date = st.date_input("End Date", value=df["Date"].max().date())
    start_time = st.time_input("Start Time", value=time(6, 0))
    end_time = st.time_input("End Time", value=time(22, 0))

# --- Filter DataFrame ---
filtered_df = df[
    (df["Operator"].isin(selected_operators)) &
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date) &
    (df["Date"].dt.time >= start_time) &
    (df["Date"].dt.time <= end_time)
].copy()

# --- Assign Shift and Shift Day (AM/PM/Night) ---
def assign_shift_and_shift_day(dt):
    t = dt.time()
    if time(6, 0) <= t < time(14, 0):
        return "AM", dt.date()
    elif time(14, 0) <= t < time(22, 0):
        return "PM", dt.date()
    else:
        shift_day = dt.date()
        if t < time(6, 0):
            shift_day -= timedelta(days=1)
        return "Night", shift_day

filtered_df[["Shift", "Shift Day"]] = filtered_df["Date"].apply(
    lambda x: pd.Series(assign_shift_and_shift_day(x))
)

# --- Shift Summary ---
shift_summary = (
    filtered_df.groupby(["Shift Day", "Shift", "Operator"])["Drawers Processed"]
    .sum()
    .reset_index()
    .rename(columns={"Drawers Processed": "Total Drawers"})
)

# --- Plot Chart ---
st.subheader("📊 Drawers Processed per Shift by Operator")

if not shift_summary.empty:
    fig = px.bar(
        shift_summary,
        x="Operator",
        y="Total Drawers",
        color="Shift",
        barmode="group",
        title="Drawers Processed by Shift (AM / PM / Night)",
        text_auto=True,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data matches the selected filters.")

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
    start_time = st.time_input("Start Time", value=time(6, 0), step=3600)
    end_time = st.time_input("End Time", value=time(22, 0), step=3600)

# --- Filter DataFrame ---
filtered_df = df[
    (df["Operator"].isin(selected_operators)) &
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date) &
    (df["Date"].dt.time >= start_time) &
    (df["Date"].dt.time <= end_time)
].copy()

# --- Assign Shift and Shift Day ---
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

# --- Format date display
filtered_df["Date"] = pd.to_datetime(filtered_df["Date"]).dt.strftime("%d/%m/%y %H:%M")

# --- Calculate Drawers Per Hour ---
# Group by operator, shift, day and count shift entries
grouped = (
    filtered_df.groupby(["Shift Day", "Shift", "Operator"])
    .agg(
        Total_Drawers=("Drawers Processed", "sum"),
        Sessions=("Date", "count")
    )
    .reset_index()
)

# Assume each session (row) = 1 hour worked
grouped["Drawers per Hour"] = (grouped["Total_Drawers"] / grouped["Sessions"]).round(1)
grouped["Shift Day"] = pd.to_datetime(grouped["Shift Day"]).dt.strftime("%d/%m/%y")

# --- KPI Setup ---
KPI_PER_HOUR = 130

# --- Plot Chart ---
st.subheader("📊 Drawers per Hour by Operator and Shift")

if not grouped.empty:
    fig = px.bar(
        grouped,
        x="Operator",
        y="Drawers per Hour",
        color="Shift",
        barmode="group",
        title="Operator Productivity by Shift (Drawers per Hour)",
        text_auto=True,
    )
    fig.add_hline(
        y=KPI_PER_HOUR,
        line_dash="dash",
        line_color="red",
        annotation_text=f"KPI Target ({KPI_PER_HOUR}/hr)",
        annotation_position="top right"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data matches the selected filters.")

# --- Grand Total Drawers Table by Shift ---
st.subheader("📋 Total Drawers by Shift")

totals_by_shift = (
    filtered_df.groupby("Shift")["Drawers Processed"]
    .sum()
    .reset_index()
    .rename(columns={"Drawers Processed": "Total Drawers"})
)

totals_by_shift["KPI Target"] = KPI_PER_HOUR * 1  # hourly KPI shown for clarity
totals_by_shift["Note"] = "Total not normalized by shift length"

st.dataframe(totals_by_shift, use_container_width=True, hide_index=True)

# --- Downloadable Summary ---
csv_bytes = grouped.to_csv(index=False).encode("utf-8")

st.download_button(
    label="📤 Download Drawers per Hour Summary (CSV)",
    data=csv_bytes,
    file_name="drawers_per_hour_summary.csv",
    mime="text/csv"
)

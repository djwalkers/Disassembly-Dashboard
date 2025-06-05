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

# Format Date column for display
filtered_df["Date"] = pd.to_datetime(filtered_df["Date"]).dt.strftime("%d/%m/%y %H:%M")

# --- Shift Summary Table ---
shift_summary = (
    filtered_df.groupby(["Shift Day", "Shift", "Operator"])["Drawers Processed"]
    .sum()
    .reset_index()
    .rename(columns={"Drawers Processed": "Total Drawers"})
)

shift_summary["Shift Day"] = pd.to_datetime(shift_summary["Shift Day"]).dt.strftime("%d/%m/%y")

# --- Chart: Drawers per Operator by Shift ---
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

# --- Grand Total Summary by Shift ---
st.subheader("📋 Total Drawers by Shift")

totals_by_shift = (
    filtered_df.groupby("Shift")["Drawers Processed"]
    .sum()
    .reset_index()
    .rename(columns={"Drawers Processed": "Total Drawers"})
)

st.dataframe(totals_by_shift, use_container_width=True, hide_index=True)

# --- 🏆 Top Operator Per Day (All Shifts Combined) ---
st.subheader("🏆 Top Operator Per Day (Average Drawers per Session)")

filtered_df["Shift Day"] = pd.to_datetime(filtered_df["Shift Day"])

top_per_day = (
    filtered_df.groupby(["Shift Day", "Operator"])
    .agg(
        Total_Drawers=("Drawers Processed", "sum"),
        Sessions=("Date", "count")
    )
    .reset_index()
)

top_per_day["Avg Drawers per Session"] = (top_per_day["Total_Drawers"] / top_per_day["Sessions"]).round(2)

# Correct top operator logic (no shift separation)
idx = top_per_day.groupby("Shift Day")["Avg Drawers per Session"].idxmax()
top_users = top_per_day.loc[idx].reset_index(drop=True)

# Format for display
top_users["Shift Day"] = top_users["Shift Day"].dt.strftime("%d/%m/%y")
top_users = top_users.rename(columns={
    "Shift Day": "Date",
    "Operator": "Top Operator"
})

st.dataframe(top_users[["Date", "Top Operator", "Avg Drawers per Session"]],
             use_container_width=True, hide_index=True)

# --- 🐛 DEBUG CHECK: YI LAM WONG ---
st.subheader("🐛 Debug Check: YI LAM WONG Sessions")

debug_operator = "YI LAM WONG"
debug_data = filtered_df[filtered_df["Operator"] == debug_operator].copy()

session_count = len(debug_data)
drawer_total = debug_data["Drawers Processed"].sum()
average = round(drawer_total / session_count, 2) if session_count > 0 else 0

st.write(f"**Total Sessions:** {session_count}")
st.write(f"**Total Drawers Processed:** {drawer_total}")
st.write(f"**Calculated Average:** {average}")

st.dataframe(debug_data[["Date", "Shift", "Shift Day", "Drawers Processed"]], use_container_width=True)

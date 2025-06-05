import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, time, timedelta
import io

st.set_page_config(page_title="Disassembly Dashboard", layout="wide")
st.title("🛠️ Disassembly Shift Performance Dashboard")

KPI_TARGET = 130  # Drawers per hour per operator

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
    shift_options = ["AM", "PM", "Night"]
    selected_shifts = st.multiselect("Select Shifts", options=shift_options, default=shift_options)
    start_date = st.date_input("Start Date", value=df["Date"].min().date())
    end_date = st.date_input("End Date", value=df["Date"].max().date())
    start_time = st.time_input("Start Time", value=time(6, 0), step=3600)
    end_time = st.time_input("End Time", value=time(22, 0), step=3600)

# --- Filter DataFrame ---
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

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

df[["Shift", "Shift Day"]] = df["Date"].apply(lambda x: pd.Series(assign_shift_and_shift_day(x)))

filtered_df = df[
    (df["Operator"].isin(selected_operators)) &
    (df["Shift"].isin(selected_shifts)) &
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date) &
    (df["Date"].dt.time >= start_time) &
    (df["Date"].dt.time <= end_time)
].copy()

filtered_df["Date"] = pd.to_datetime(filtered_df["Date"]).dt.strftime("%d/%m/%y %H:%M")
filtered_df["Shift Day"] = pd.to_datetime(filtered_df["Shift Day"]).dt.strftime("%d/%m/%y")

# --- KPI % Analysis ---
filtered_df["KPI %"] = ((filtered_df["Drawers Processed"] / 1) / KPI_TARGET * 100).round(1)  # assuming 1 hour sessions

# --- Drawers by Shift & Operator ---
st.subheader("📊 Drawers Processed per Shift by Operator")
shift_summary = filtered_df.groupby(["Shift Day", "Shift", "Operator"]).agg(
    Total_Drawers=("Drawers Processed", "sum"),
    Sessions=("Date", "count"),
).reset_index()

if not shift_summary.empty:
    fig = px.bar(
        shift_summary,
        x="Operator",
        y="Total_Drawers",
        color="Shift",
        barmode="group",
        title="Drawers Processed by Shift",
        text_auto=True,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data matches your filters.")

# --- Grand Total Summary by Shift ---
st.subheader("📋 Total Drawers by Shift")
totals_by_shift = filtered_df.groupby("Shift")["Drawers Processed"].sum().reset_index()
totals_by_shift = totals_by_shift.rename(columns={"Drawers Processed": "Total Drawers"})
st.dataframe(totals_by_shift, use_container_width=True, hide_index=True)

# --- 🏆 Top Operator Per Day (All Shifts) ---
st.subheader("🏆 Top Operator Per Day (Avg Drawers/Session)")
top_per_day = filtered_df.groupby(["Shift Day", "Operator"]).agg(
    Total_Drawers=("Drawers Processed", "sum"),
    Sessions=("Date", "count")
).reset_index()
top_per_day["Avg Drawers per Session"] = (top_per_day["Total_Drawers"] / top_per_day["Sessions"]).round(2)
idx = top_per_day.groupby("Shift Day")["Avg Drawers per Session"].idxmax()
top_users = top_per_day.loc[idx].reset_index(drop=True).rename(columns={"Shift Day": "Date", "Operator": "Top Operator"})
st.dataframe(top_users[["Date", "Top Operator", "Avg Drawers per Session"]], use_container_width=True, hide_index=True)

# --- 📈 Time Series Trends ---
st.subheader("📈 Drawers Processed Over Time")
daily_totals = filtered_df.copy()
daily_totals["Shift Day"] = pd.to_datetime(daily_totals["Shift Day"], dayfirst=True)
daily_chart = daily_totals.groupby("Shift Day")["Drawers Processed"].sum().reset_index()
daily_chart["Shift Day"] = pd.to_datetime(daily_chart["Shift Day"], dayfirst=True)
daily_chart["Shift Day"] = daily_chart["Shift Day"].dt.strftime("%d/%m/%y")
fig2 = px.line(daily_chart, x="Shift Day", y="Drawers Processed", markers=True, title="Daily Total Drawers")
fig2.update_layout(xaxis_tickformat="%d/%m/%y")
st.plotly_chart(fig2, use_container_width=True)

# --- 🧮 Operator Efficiency Ranking ---
st.subheader("📋 Operator Efficiency Ranking")
efficiency = filtered_df.groupby("Operator").agg(
    Total_Drawers=("Drawers Processed", "sum"),
    Sessions=("Date", "count")
).reset_index()
efficiency["Avg per Session"] = (efficiency["Total_Drawers"] / efficiency["Sessions"]).round(2)
st.dataframe(efficiency.sort_values("Avg per Session", ascending=False), use_container_width=True, hide_index=True)

# --- ⏱️ Utilization Check ---
st.subheader("🕒 Operator Utilization Summary")
util = filtered_df.groupby(["Shift Day", "Operator"]).agg(Sessions=("Date", "count")).reset_index()
low_util = util[util["Sessions"] <= 1]
if not low_util.empty:
    st.warning("⚠️ Operators with low utilization (≤1 session per day):")
    st.dataframe(low_util, use_container_width=True, hide_index=True)
else:
    st.success("✅ No low-utilization operators found.")

# --- ⚠️ Fault and Rogue Drawer Analysis ---
st.subheader("❗ Faulty and Rogue Drawers Summary")
fault_summary = filtered_df.groupby("Operator")[["Faulty", "Rogue"]].sum().reset_index()
st.dataframe(fault_summary.sort_values("Faulty", ascending=False), use_container_width=True, hide_index=True)

# --- 📥 Export Options ---
st.subheader("📤 Export Data")
export_df = filtered_df.copy()
to_download = export_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Filtered Data as CSV", data=to_download, file_name="filtered_disassembly_data.csv")

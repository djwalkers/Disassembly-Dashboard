import pandas as pd
import plotly.express as px
from datetime import datetime, time, timedelta

# --- Load and clean data ---
df = pd.read_csv("Dissasembly Perfomance Report.csv", parse_dates=["Date"], dayfirst=True)
df["Operator"] = df["Operation"].str.replace(r"[\\*]", "", regex=True).str.strip()

# --- Parameters (used in Hex as @param inputs) ---
# @param
selected_operators = df["Operator"].unique().tolist()

# @param
start_date = df["Date"].min().date()

# @param
end_date = df["Date"].max().date()

# @param
start_time = "06:00"

# @param
end_time = "22:00"

# --- Convert time strings to time objects ---
start_time_obj = datetime.strptime(start_time, "%H:%M").time()
end_time_obj = datetime.strptime(end_time, "%H:%M").time()

# --- Filter based on date, time and operator ---
filtered_df = df[
    (df["Operator"].isin(selected_operators)) &
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date) &
    (df["Date"].dt.time >= start_time_obj) &
    (df["Date"].dt.time <= end_time_obj)
].copy()

# --- Assign Shift and Logical Shift Day ---
def assign_shift_and_shift_day(dt):
    t = dt.time()
    if time(6, 0) <= t < time(14, 0):
        return "Shift 1", dt.date()
    elif time(14, 0) <= t < time(22, 0):
        return "Shift 2", dt.date()
    else:
        shift_day = dt.date()
        if t < time(6, 0):
            shift_day -= timedelta(days=1)
        return "Shift 3", shift_day

filtered_df[["Shift", "Shift Day"]] = filtered_df["Date"].apply(
    lambda x: pd.Series(assign_shift_and_shift_day(x))
)

# --- Group for charting ---
shift_summary = (
    filtered_df.groupby(["Shift Day", "Shift", "Operator"])["Drawers Processed"]
    .sum()
    .reset_index()
    .rename(columns={"Drawers Processed": "Total Drawers"})
)

# --- Plot chart ---
fig = px.bar(
    shift_summary,
    x="Operator",
    y="Total Drawers",
    color="Shift",
    barmode="group",
    title="Drawers Processed per Shift by Operator"
)
fig.show()

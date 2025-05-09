
import streamlit as st
import pandas as pd
import plotly.express as px

# Load data
uploaded_file = st.file_uploader("Upload the disassembly performance CSV file", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, parse_dates=["Date"])
    df["Operator"] = df["Operation"].str.replace(r"[\*]", "", regex=True).str.strip()
    df["Date"] = df["Date"].dt.date

    # KPI target
    KPI_TARGET = 130

    # Sidebar filters
    st.sidebar.header("Filters")
    operator_options = df["Operator"].unique().tolist()
    selected_operators = st.sidebar.multiselect("Select operator(s)", operator_options, default=operator_options)
    min_date, max_date = df["Date"].min(), df["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select date range", [min_date, max_date], min_value=min_date, max_value=max_date)

    # Filter data
    filtered_df = df.copy()
    filtered_df = filtered_df[filtered_df["Operator"].isin(selected_operators)]
    filtered_df = filtered_df[(filtered_df["Date"] >= start_date) & (filtered_df["Date"] <= end_date)]

    st.title("Disassembly Performance Dashboard")

    if filtered_df.empty:
        st.warning("No data found for the selected filters.")
    else:
        # Summary calculations
        summary_df = (
            filtered_df.groupby("Operator")
            .agg(
                Total_Drawers=("Drawers Processed", "sum"),
                Hours_Worked=("Date", "count"),
                Faulty_Drawers=("Faulty", "sum"),
                Rogue_Drawers=("Rogue", "sum")
            )
            .reset_index()
        )
        summary_df["Avg_Drawers_Per_Hour"] = summary_df["Total_Drawers"] / summary_df["Hours_Worked"]
        summary_df["Diff_From_KPI"] = summary_df["Avg_Drawers_Per_Hour"] - KPI_TARGET
        summary_df["KPI_Status"] = summary_df["Avg_Drawers_Per_Hour"].apply(lambda x: "Meets/Exceeds" if x >= KPI_TARGET else "Below")

        # Charts
        bar_fig = px.bar(summary_df.sort_values("Avg_Drawers_Per_Hour", ascending=False),
                         x="Operator", y="Avg_Drawers_Per_Hour",
                         color="KPI_Status",
                         title="Average Drawers per Hour by Operator")
        st.plotly_chart(bar_fig)

        time_df = filtered_df.groupby(["Date", "Operator"])["Drawers Processed"].sum().reset_index()
        line_fig = px.line(time_df, x="Date", y="Drawers Processed", color="Operator", title="Drawers Processed Over Time")
        st.plotly_chart(line_fig)
else:
    st.info("Please upload a CSV file to start.")

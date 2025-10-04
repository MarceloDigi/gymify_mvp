"""
Analytics Overview Page

This script generates the "Analytics Overview" page for the Streamlit dashboard. It provides users with a detailed view of their training data, including KPIs, charts, and summary tables.

Features:
- **Data Loading**: Fetches user-specific training data from the database.
- **Date Filtering**: Allows users to select a date range and granularity for analysis.
- **KPI Calculation**: Computes key performance indicators (KPIs) for the selected period.
- **Charts and Tables**: Displays visualizations and summary tables for daily, routine, and muscle-level metrics.

Modules:
- `load_data`: Loads training data for the authenticated user.
- `filter_by_date`: Filters data based on the selected date range.
- `compute_kpis`: Calculates KPIs for the current and previous periods.
- `display_kpis`: Displays KPIs in the dashboard.
- `calculate_summary_table`: Aggregates data for summary tables.
- `plot_line_vs_bar`: Generates a combined line and bar chart for workload and series metrics.
- `display_summary_table`: Renders summary tables for daily, routine, and muscle-level metrics.

Dependencies:
- `streamlit`
- `pandas`
- `datetime`
- Utility modules: `data_loader`, `kpis`, `tables`, `charts`, `styling`, `general`

"""

import pandas as pd
import streamlit as st
import utils.kpis as kpis
import utils.tables as tables
import utils.charts as charts
import utils.filters_and_sort as fs
import utils.styling as styling

st.set_page_config(page_title="Dashboard Entrenamiento", layout="wide")

def main():
    """
    Main function to render the Analytics Overview page.

    This function handles the following tasks:
    - Retrieves user-specific training data from the database.
    - Applies date range and granularity filters to the data.
    - Computes KPIs for the selected and previous periods.
    - Generates and displays charts and summary tables for the data.

    Returns:
        None
    """

    # Cargar datos
    df_track_record = st.session_state.get("df_track_record")
    df_track_record_by_muscles = st.session_state.get("df_track_record_muscles")

    if df_track_record_by_muscles is None or df_track_record is None:
        st.warning("Datos no cargados. Vuelve a la página principal para inicializarlos.")
        st.stop()

    # Filtros de fechas
    start_date, end_date, prev_start, prev_end, period_length = fs.get_date_filters(df_track_record)

    granularity = st.sidebar.selectbox(
        "Selecciona la granularidad",
        options=["D", "W", "M"],
        index=1,
        format_func=lambda x: {"D": "Diaria", "W": "Semanal", "M": "Mensual"}[x]
    )
    # ////////////////// Resources ///////////////////////
    df_filtered = fs.filter_by_date(df_track_record, start_date, end_date)
    df_prev = fs.filter_by_date(df_track_record, prev_start, prev_end)
    df_muscles_filtered = fs.filter_by_date(df_track_record_by_muscles, start_date, end_date)
    df_muscles_prev = fs.filter_by_date(df_track_record_by_muscles, prev_start, prev_end)

    map_metrics = {"workload": "sum", "effective_set": "sum", "1rm": "max"}
    labels_kpis = [charts.labels[4]] + [charts.labels[2]] + [charts.labels[5]]

    metrics_1 = {
        "Series Totales": ("id_set", "nunique"),
        "Series Efectivas": ("effective_set", "sum"),
        "Workload": ("workload", "sum"),
        "Max. 1RM" : ("1rm", "max")
    }
    metrics_2 = {
        "Días Entrenados": ("fecha", "nunique"),
        "Series Totales": ("id_set", "nunique"),
        "Series Efectivas": ("effective_set", "sum"),
        "Workload": ("workload", "sum")
    }
    metrics_3 = {
        "Series Totales": ("sets_by_muscle", "sum"),
        "Series Directas": ("is_set_principal_for_muscle","sum"),
        "Series Efectivas": ("effective_sets_by_muscle", "sum"),
        "Workload": ("workload_by_muscle", "sum")
    }

    kpis_curr = kpis.compute_kpis(df_filtered, agg_map=map_metrics)
    kpis_prev = kpis.compute_kpis(df_prev, agg_map=map_metrics)

    daily_metrics = tables.calculate_summary_table(
                                        df_now=df_filtered,
                                        group_col="fecha",
                                        metrics=metrics_1,
                                        compare_prev=False
    )
    df_aggregated_processed = tables.calculate_summary_table(
                                        df_now=df_filtered,
                                        df_prev=df_prev,
                                        group_col="routine",
                                        metrics=metrics_2,
    )
    df_muscle_processed = tables.calculate_summary_table(
                                        df_now=df_muscles_filtered,
                                        df_prev=df_muscles_prev,
                                        group_col="muscle_name",
                                        metrics=metrics_3,
    )
    grouped = df_filtered\
        .groupby(pd.Grouper(key='fecha', freq=granularity))\
        .agg(
             Total_Series= ('id_set','nunique'),
             Series_Efectivas=('effective_set','sum'),
             Tonelaje= ('workload','sum')
        ).reset_index()
    grouped = grouped.rename(columns={
        'Total_Series': 'Total Series',
        'Series_Efectivas': 'Series Efectivas',
        'Tonelaje': 'Tonelaje'
    })
    grouped = kpis.compute_difference_between_kpis(grouped, 'Series Efectivas', 'Total Series', drop=True)
    grouped = fs.format_fecha_column(grouped, "fecha", granularity=granularity)
    col_metrics_2 = [col for col in df_aggregated_processed.columns if "prev" not in col]
    col_metrics_3 = [col for col in df_muscle_processed.columns if "prev" not in col]

    # ////////////////// Display ///////////////////////
    st.title("📊 Dashboard de Entrenamiento")
    # Period info display
    styling.texto_periodo_seleccionado(start_date, end_date, prev_start, prev_end, period_length)
    
    kpis.display_kpis(
        curr=kpis_curr,
        prev=kpis_prev,
        labels=labels_kpis
    )
    charts.plot_line_vs_bar(
        grouped,
        col_line="Tonelaje",
        col_bars=["Series Efectivas", "Series Efectivas_vs_Total Series"],
        data_labels=['Series'],
        color_line='#FF752F',
        colors_bars=["#fa9f3d", "#656566"],
        axis_color=True,
        showline=False,
        show_labels=["Series Efectivas"]
    )
    tables.display_summary_table(
        daily_metrics,
        group_col="fecha",
        title="📅 Resumen diario",
    )
    tables.display_summary_table(
        df_aggregated_processed[col_metrics_2],
        group_col="routine",
        title="📚 Detalle por rutina"
    )
    tables.display_summary_table(
        df_muscle_processed[col_metrics_3],
        group_col="muscle_name",
        title = "💪 Detalle por músculo"
    )

if __name__ == "__main__":
    main()

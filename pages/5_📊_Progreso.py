"""
Progress Analysis Page

This script generates the "Progress Analysis" page for the Streamlit dashboard. It provides users with detailed insights into their weekly compound and isolated exercise progress, including KPIs, charts, and summary tables.

Features:
- **Data Loading**: Fetches user-specific training data from the database.
- **Date Filtering**: Allows users to select a date range and granularity for analysis.
- **KPI Calculation**: Computes KPIs for compound and isolated exercises.
- **Charts and Tables**: Displays visualizations and summary tables for exercise-level metrics.
- **Detailed Analysis**: Provides breakdowns for individual exercises, including RIR ranges and weekly progress.

Modules:
- `load_data`: Loads training data for the authenticated user.
- `filter_by_date`: Filters data based on the selected date range.
- `compute_kpis`: Calculates KPIs for compound and isolated exercises.
- `display_kpis`: Displays KPIs in the dashboard.
- `calculate_summary_table`: Aggregates data for summary tables.
- `plot_line_vs_bar`: Generates combined line and bar charts for workload and other metrics.
- `display_summary_table`: Renders summary tables for exercise-level metrics.

Dependencies:
- `streamlit`
- `pandas`
- `datetime`
- Utility modules: `data_loader`, `kpis`, `tables`, `charts`, `general`

"""

import streamlit as st
import pandas as pd

import utils.kpis as kpis
import utils.tables as tables
import utils.charts as charts
import utils.filters_and_sort as fs
import utils.styling as styling

st.set_page_config(page_title="Análisis Compound Semanal", layout="wide")

def main():
    """
    Main function to render the Progress Analysis page.

    This function handles the following tasks:
    - Retrieves user-specific training data from the database.
    - Applies date range and granularity filters to the data.
    - Computes KPIs for compound and isolated exercises.
    - Generates and displays charts and summary tables for the data.
    - Provides detailed breakdowns for individual exercises.

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

    # Agregaciones para ejercicios
    groupers = [pd.Grouper(key='fecha', freq=granularity), 'exercise']
    metrics_compound = {'workload': 'sum', '1rm': 'max', 'effective_set': 'sum'}
    metrics_isolated = {'workload': 'sum', 'weight': 'max', 'effective_set': 'sum'}

    compound_agg = tables.double_grouping(
                                df_filtered,
                                groupers=groupers,
                                filter=df_filtered.progress_tracker == 'Compound',
                                metrics=metrics_compound
                                )
    compound_agg_prev = tables.double_grouping(
                                df_prev,
                                groupers=groupers,
                                filter=df_prev.progress_tracker == 'Compound',
                                metrics=metrics_compound
                                )
    isolate_agg = tables.double_grouping(
                                df_filtered,
                                groupers=groupers,
                                filter=df_filtered.progress_tracker == 'Isolate',
                                metrics=metrics_isolated
                                )
    isolate_agg_prev = tables.double_grouping(
                                df_prev,
                                groupers=groupers,
                                filter=df_prev.progress_tracker == 'Isolate',
                                metrics=metrics_isolated
                                )
    # KPIs
    agg_map_compound = {
        "workload": "sum",
        "effective_set": "sum",
        "1rm": "max",
    }
    agg_map_isolate = {
        "workload": "sum",
        "effective_set": "sum",
        "weight": "max",
    }

    kpi_now_compound = kpis.compute_kpis(compound_agg, agg_map=agg_map_compound)
    kpi_prev_compound = kpis.compute_kpis(compound_agg_prev, agg_map=agg_map_compound)

    kpi_now_isolate = kpis.compute_kpis(isolate_agg, agg_map=agg_map_isolate)
    kpi_prev_isolate = kpis.compute_kpis(isolate_agg_prev, agg_map=agg_map_isolate)

    compound_exercises = df_filtered[df_filtered["progress_tracker"] == "Compound"]["exercise"].unique()
    isolate_exercises = df_filtered[df_filtered["progress_tracker"] == "Isolate"]["exercise"].unique()

    compound_df_filtered = df_filtered[df_filtered["progress_tracker"] == "Compound"]
    compound_df_prev = df_prev[df_prev["progress_tracker"] == "Compound"]
    isolate_df_filtered = df_filtered[df_filtered["progress_tracker"] == "Isolate"]
    isolate_df_prev = df_prev[df_prev["progress_tracker"] == "Isolate"]

    labels_compound = [charts.labels[4]] + [charts.labels[2]] + [charts.labels[5]]
    labels_isolate = [charts.labels[4]] + [charts.labels[2]] + [charts.labels[6]]

    # Tabla 1
    table_1 = tables.calculate_summary_table(
        df_now=compound_df_filtered,
        df_prev=compound_df_prev,
        group_col="rir_range",
        metrics={"Series Totales": ("id_set", "nunique")},
    )
    table_1_cols = [col for col in table_1.columns if "prev" not in col]
    # Tabla 2
    metrics_2 = {
            "Workload": ("workload", "sum"),
            "Series Efectivas": ("effective_set", "sum"),
            "Max. 1RM": ("1rm", "max")
    }
    table_2 = tables.calculate_summary_table(
        df_now=compound_df_filtered,
        df_prev=compound_df_prev,
        group_col="exercise",
        metrics=metrics_2,
    )
    table_2_cols = [col for col in table_2.columns if "prev" not in col]
    # Tabla 3
    metrics_3 = {
            "Workload": ("workload", "sum"),
            "Series Efectivas": ("effective_set", "sum"),
            "Max. Peso": ("weight", "max")
    }
    table_3 = tables.calculate_summary_table(
        df_now=isolate_df_filtered,
        df_prev=isolate_df_prev,
        group_col="exercise",
        metrics=metrics_3
    )
    table_3_cols = [col for col in table_3.columns if "prev" not in col]
    # ////////////////// Display ///////////////////////
    st.title("📊 Análisis Compound Semanal")
    styling.texto_periodo_seleccionado(start_date, end_date, prev_start, prev_end, period_length)
    charts.display_exercise_tags(compound_exercises)
    kpis.display_kpis(
        kpi_now_compound,
        kpi_prev_compound,
        labels=labels_compound
    )
    compound_agg = fs.format_fecha_column(compound_agg, "fecha", granularity=granularity)
    charts.plot_line_vs_bar(
        compound_agg,
        col_line="workload",
        col_bars="1rm",
        show_labels='bars'
    )
    tables.display_summary_table(
        table_1[table_1_cols],
        group_col="rir_range",
        title="💪 Detalle por RIR range"
    )
    tables.display_summary_table(
        table_2[table_2_cols],
        group_col="exercise",
        title="💪 Detalle por ejercicio"
    )

    # Detalle semanal por ejercicio
    st.title("📊 Análisis Detallado - Compound")
    for exercise in compound_exercises:
        st.subheader(f"🔍 {exercise}")
        exercise_df = df_filtered[df_filtered["exercise"] == exercise]
        exercise_muscle_filtered = df_muscles_filtered[df_muscles_filtered["exercise"] == exercise]
        exercise_muscle_prev = df_muscles_prev[df_muscles_prev["exercise"] == exercise]

        freq_grouped = exercise_df\
            .groupby(pd.Grouper(key='fecha', freq=granularity)).agg({
            'workload': 'sum',
            '1rm': 'max',
            'effective_set': 'sum'
        }).reset_index()

        freq_grouped = fs.format_fecha_column(freq_grouped, "fecha", granularity=granularity)

        charts.plot_line_vs_bar(
            freq_grouped,
            col_line="workload",
            col_bars="1rm",
            show_labels='bars'
        )
        exercise_by_rir = tables.calculate_summary_table(
            df_now=exercise_muscle_filtered,
            df_prev=exercise_muscle_prev,
            group_col="rir_range",
            metrics={"Series Totales": ("sets_by_muscle", "sum")}
        )
        exercise_by_rir_cols = [
            col for col in exercise_by_rir.columns if "prev" not in col
        ]
        tables.display_summary_table(
            exercise_by_rir[exercise_by_rir_cols],
            group_col="rir_range",
            title="💪 Detalle por RIR range"
        )

    st.title("📊 Análisis Detallado - Isolate")
    charts.display_exercise_tags(isolate_exercises)
    kpis.display_kpis(
        kpi_now_isolate,
        kpi_prev_isolate,
        labels=labels_isolate
    )
    isolate_agg = fs.format_fecha_column(isolate_agg, "fecha", granularity=granularity)
    charts.plot_line_vs_bar(
        isolate_agg,
        col_line="workload",
        col_bars="weight",
        show_labels='bars'
    )
    tables.display_summary_table(
        table_3[table_3_cols],
        group_col="exercise",
        title="💪 Detalle por ejercicio"
    )

    for exercise in isolate_exercises:
        st.subheader(f"🔍 {exercise}")
        exercise_df = df_filtered[df_filtered["exercise"] == exercise]

        exercise_by_rir = tables.calculate_summary_table(
            df_now=exercise_muscle_filtered,
            df_prev=exercise_muscle_prev,
            group_col="rir_range",
            metrics={"Series Totales": ("sets_by_muscle", "sum")}
        )
        exercise_by_rir_cols = [
            col for col in exercise_by_rir.columns if "prev" not in col
        ]
        tables.display_summary_table(
            exercise_by_rir[exercise_by_rir_cols],
            group_col="rir_range",
            title="💪 Detalle por RIR range"
        )
        freq_grouped = exercise_df\
            .groupby(pd.Grouper(key='fecha', freq=granularity)).agg({
            'workload': 'sum',
            'weight': 'max',
            'effective_set': 'sum'
            }).reset_index()

        freq_grouped = fs.format_fecha_column(freq_grouped, "fecha", granularity=granularity)

        charts.plot_line_vs_bar(freq_grouped,
                         col_line="workload",
                         col_bars="weight",
                         show_labels='bars'
        )

if __name__ == "__main__":
    main()


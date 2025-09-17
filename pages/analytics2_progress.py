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
from datetime import timedelta, datetime
from utils.data_loader import load_data, filter_by_date, get_date_filters
from utils.kpis import compute_kpis, display_kpis
from utils.tables import calculate_summary_table, double_grouping, display_summary_table
from utils.charts import plot_line_vs_bar, display_exercise_tags, labels
from utils.general import format_fecha_column

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

    # Get user ID from session state if authenticated
    user_id = st.session_state.get("user_id", None)

    # Load data from SQLite database
    df, df_muscles = load_data(user_id=user_id)

    # Check if data is empty
    if df.empty:
        st.warning("No hay datos disponibles en la base de datos.")
        st.info("Por favor, importa datos a través del panel de administración en la página de inicio.")
        return

    # ////////////////// Filtros ////////////////////////
    try:
        min_date, max_date = get_date_filters(df)
        # Default range: last 6 weeks
        today = datetime.today().date()
        default_start = today - timedelta(weeks=36)
        default_end = today

        # Convert Timestamp to .date() with NaT handling
        min_date = min_date.date() if not pd.isna(min_date) else today
        max_date = max_date.date() if not pd.isna(max_date) else today

        # Bound defaults to data limits
        default_start = max(default_start, min_date)
        default_end = min(default_end, max_date)
    except Exception as e:
        st.error(f"Error al procesar fechas: {e}")
        st.info("Por favor, importa datos válidos a través del panel de administración.")
        return

    try:
        start_date, end_date = st.sidebar.date_input(
            "Rango de fechas",
            value=[default_start, default_end],
            min_value=min_date, max_value=max_date
        )

        period_length = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)

    except ValueError:
        st.sidebar.warning("Por favor selecciona un rango válido de fechas (inicio y fin).")
        st.write("Esperando selección de rango de fechas...")
        return

    granularity = st.sidebar.selectbox(
    "Selecciona la granularidad",
    options=["D", "W", "M"],
    index=1,
    format_func=lambda x: {"D": "Diaria", "W": "Semanal", "M": "Mensual"}[x]
    )

    # ////////////////// Resources ///////////////////////
    df_filtered = filter_by_date(df, start_date, end_date)
    df_prev = filter_by_date(df, prev_start, prev_end)
    df_muscles_filtered = filter_by_date(df_muscles, start_date, end_date)
    df_muscles_prev = filter_by_date(df_muscles, prev_start, prev_end)

    # Agregaciones para ejercicios
    groupers = [pd.Grouper(key='fecha', freq=granularity), 'exercise']
    metrics_compound = {'workload': 'sum', '1rm': 'max', 'effective_set': 'sum'}
    metrics_isolated = {'workload': 'sum', 'weight': 'max', 'effective_set': 'sum'}

    compound_agg = double_grouping(
                                df_filtered,
                                groupers=groupers,
                                filter=df_filtered.progress_tracker == 'Compound',
                                metrics=metrics_compound
                                )
    compound_agg_prev = double_grouping(
                                df_prev,
                                groupers=groupers,
                                filter=df_prev.progress_tracker == 'Compound',
                                metrics=metrics_compound
                                )
    isolate_agg = double_grouping(
                                df_filtered,
                                groupers=groupers,
                                filter=df_filtered.progress_tracker == 'Isolate',
                                metrics=metrics_isolated
                                )
    isolate_agg_prev = double_grouping(
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

    kpi_now_compound = compute_kpis(compound_agg, agg_map=agg_map_compound)
    kpi_prev_compound = compute_kpis(compound_agg_prev, agg_map=agg_map_compound)

    kpi_now_isolate = compute_kpis(isolate_agg, agg_map=agg_map_isolate)
    kpi_prev_isolate = compute_kpis(isolate_agg_prev, agg_map=agg_map_isolate)

    compound_exercises = df_filtered[df_filtered["progress_tracker"] == "Compound"]["exercise"].unique()
    isolate_exercises = df_filtered[df_filtered["progress_tracker"] == "Isolate"]["exercise"].unique()

    compound_df_filtered = df_filtered[df_filtered["progress_tracker"] == "Compound"]
    compound_df_prev = df_prev[df_prev["progress_tracker"] == "Compound"]
    isolate_df_filtered = df_filtered[df_filtered["progress_tracker"] == "Isolate"]
    isolate_df_prev = df_prev[df_prev["progress_tracker"] == "Isolate"]

    labels_compound = [labels[4]] + [labels[2]] + [labels[5]]
    labels_isolate = [labels[4]] + [labels[2]] + [labels[6]]

    # Tabla 1
    table_1 = calculate_summary_table(
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
    table_2 = calculate_summary_table(
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
    table_3 = calculate_summary_table(
        df_now=isolate_df_filtered,
        df_prev=isolate_df_prev,
        group_col="exercise",
        metrics=metrics_3
    )
    table_3_cols = [col for col in table_3.columns if "prev" not in col]
    # ////////////////// Display ///////////////////////
    st.title("📊 Análisis Compound Semanal")
    st.markdown(
        f"""
        <div style='color: rgba(213, 212, 213,0.5); font-size: 0.9rem;'>
            <strong>Periodo seleccionado:</strong> {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')} ({period_length} días)
            <br>
            <strong>Comparando con:</strong> {prev_start.strftime('%d %b %Y')} — {prev_end.strftime('%d %b %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )
    display_exercise_tags(compound_exercises)
    display_kpis(
        kpi_now_compound,
        kpi_prev_compound,
        labels=labels_compound
    )
    compound_agg = format_fecha_column(compound_agg, "fecha", granularity=granularity)
    plot_line_vs_bar(
        compound_agg,
        col_line="workload",
        col_bars="1rm",
        show_labels='bars'
    )
    display_summary_table(
        table_1[table_1_cols],
        group_col="rir_range",
        title="💪 Detalle por RIR range"
    )
    display_summary_table(
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

        freq_grouped = format_fecha_column(freq_grouped, "fecha", granularity=granularity)

        plot_line_vs_bar(
            freq_grouped,
            col_line="workload",
            col_bars="1rm",
            show_labels='bars'
        )
        exercise_by_rir = calculate_summary_table(
            df_now=exercise_muscle_filtered,
            df_prev=exercise_muscle_prev,
            group_col="rir_range",
            metrics={"Series Totales": ("sets_by_muscle", "sum")}
        )
        exercise_by_rir_cols = [
            col for col in exercise_by_rir.columns if "prev" not in col
        ]
        display_summary_table(
            exercise_by_rir[exercise_by_rir_cols],
            group_col="rir_range",
            title="💪 Detalle por RIR range"
        )

    st.title("📊 Análisis Detallado - Isolate")
    display_exercise_tags(isolate_exercises)
    display_kpis(
        kpi_now_isolate,
        kpi_prev_isolate,
        labels=labels_isolate
    )
    isolate_agg = format_fecha_column(isolate_agg, "fecha", granularity=granularity)
    plot_line_vs_bar(
        isolate_agg,
        col_line="workload",
        col_bars="weight",
        show_labels='bars'
    )
    display_summary_table(
        table_3[table_3_cols],
        group_col="exercise",
        title="💪 Detalle por ejercicio"
    )

    for exercise in isolate_exercises:
        st.subheader(f"🔍 {exercise}")
        exercise_df = df_filtered[df_filtered["exercise"] == exercise]

        exercise_by_rir = calculate_summary_table(
            df_now=exercise_muscle_filtered,
            df_prev=exercise_muscle_prev,
            group_col="rir_range",
            metrics={"Series Totales": ("sets_by_muscle", "sum")}
        )
        exercise_by_rir_cols = [
            col for col in exercise_by_rir.columns if "prev" not in col
        ]
        display_summary_table(
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

        freq_grouped = format_fecha_column(freq_grouped, "fecha", granularity=granularity)

        plot_line_vs_bar(freq_grouped,
                         col_line="workload",
                         col_bars="weight",
                         show_labels='bars'
        )

if __name__ == "__main__":
    main()


"""
Muscle Analysis Page

This script generates the "Muscle Analysis" page for the Streamlit dashboard. It provides users with insights into their muscle-specific training metrics, including workload, effective sets, and direct sets.

Features:
- **Data Loading**: Fetches user-specific muscle training data from the database.
- **Date Filtering**: Allows users to select a date range for analysis.
- **KPI Calculation**: Computes metrics such as workload, effective sets, and direct sets.
- **Charts and Tables**: Displays visualizations and summary tables for muscle-level metrics.

Modules:
- `load_data`: Loads training data for the authenticated user.
- `filter_by_date`: Filters data based on the selected date range.
- `calculate_summary_table`: Aggregates data for summary tables.
- `plot_muscle_analysis`: Generates visualizations for muscle-specific metrics.
- `display_summary_table`: Renders summary tables for muscle-level metrics.

Dependencies:
- `streamlit`
- `pandas`
- `datetime`
- Utility modules: `data_loader`, `tables`, `charts`, `dashboard_utils`

"""

import streamlit as st

import utils.kpis as kpis
import utils.tables as tables
import utils.charts as charts
import utils.filters_and_sort as fs
import utils.styling as styling

st.set_page_config(page_title="Análisis Muscular", layout="wide")

st.title("Análisis Muscular")

def main():
    """
    Main function to render the Muscle Analysis page.

    This function handles the following tasks:
    - Retrieves user-specific muscle training data from the database.
    - Applies date range filters to the data.
    - Computes metrics such as workload, effective sets, and direct sets.
    - Generates and displays charts and summary tables for muscle-level metrics.

    Returns:
        None
    """

    # Cargar datos
    df_track_record_by_muscles = st.session_state.get("df_track_record_muscles")

    if df_track_record_by_muscles is None:
        st.warning("Datos no cargados. Vuelve a la página principal para inicializarlos.")
        st.stop()

    # Filtros de fechas
    start_date, end_date, prev_start, prev_end, period_length = fs.get_date_filters(df_track_record_by_muscles)

    # ////////////////// Resources ///////////////////////
    df_muscles_filtered = fs.filter_by_date(df_track_record_by_muscles, start_date, end_date)
    df_muscles_prev = fs.filter_by_date(df_track_record_by_muscles, prev_start, prev_end)

    muscle_col = "muscle_name"

    metrics = {
        'Series Directas': ('is_set_principal_for_muscle','sum'),
        'Total Series': ('sets_by_muscle','sum'),
        'Series Efectivas': ('effective_sets_by_muscle','sum'),
        'Workload': ('workload_by_muscle','sum'),
        }

    df_processed = tables.calculate_summary_table(
                                        df_now=df_muscles_filtered,
                                        df_prev=df_muscles_prev,
                                        group_col=muscle_col,
                                        metrics=metrics
                                        )

    prev_cols = [col for col in df_processed.columns if "_prev" in col]
    df_processed.drop(columns=prev_cols, inplace=True)
    df_processed = kpis.compute_difference_between_kpis(df_processed, 'Series Efectivas', 'Total Series')

    table_1_metrics = [muscle_col] + [col for col in df_processed.columns if any(word in col.lower() for word in ['directas', 'total'])]
    table_1_metrics = fs.reorder_columns(table_1_metrics)
    table_1_metrics.remove('Series Efectivas_vs_Total Series')

    table_2_metrics = [muscle_col] + [col for col in df_processed.columns if any(word in col.lower() for word in ['efectivas', 'total'])]
    table_2_metrics = fs.reorder_columns(table_2_metrics)
    table_2_metrics = [col for col in table_2_metrics if col not in ['Series Efectivas_vs_Total Series','%_series_efectivas','Δ_%_series_efectivas']]

    table_3_metrics = [muscle_col] + [col for col in df_processed.columns if any(word in col.lower() for word in ['workload'])]
    table_3_metrics = fs.reorder_columns(table_3_metrics)
    # ////////////////// Display //////////////////////////
    styling.texto_periodo_seleccionado(start_date, end_date, prev_start, prev_end, period_length)
    # Section 1: Direct sets and total sets
    st.subheader("💪 Análisis de series directas y totales")
    # Tabla 1
    tables.display_summary_table(
                        df_processed[table_1_metrics],
                        group_col=muscle_col,
                        title="Resumen por ejercicio (actual vs anterior)"
                        )

    # Section 2: Effective sets and total sets
    st.subheader("💪 Análisis de series efectivas y totales")
    charts.plot_muscle_analysis(
        data=df_processed,
        x1_col="Series Efectivas",
        x2_col="Series Efectivas_vs_Total Series",
        y_col=muscle_col,
        x1_label="Series Efectivas",
        x2_label="Total Series",
        custom_data_labels=['%_series_efectivas', None],
        x1_suffix="%",
        title="Muscle Analysis",
        hide_xaxis=True,
    )

    # Tabla 2
    tables.display_summary_table(
                        df_processed[table_2_metrics],
                        group_col=muscle_col,
                        title="Resumen por ejercicio (actual vs anterior)"
                        )

    # Section 3: Workload
    st.subheader("💪 Análisis de carga de trabajo")

    charts.plot_muscle_analysis(
        data=df_processed,
        x1_col="Δ_Workload",
        y_col=muscle_col,
        x1_label="Δ_Workload",
        title="Muscle Analysis",
        x1_suffix="%",
        hide_xaxis=True,
        data_prefix=[True, False]
    )

    # Tabla 3
    tables.display_summary_table(
                        df_processed[table_3_metrics],
                        group_col=muscle_col,
                        title="Resumen por ejercicio (actual vs anterior)"
                        )

if __name__ == "__main__":
    main()
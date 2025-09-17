import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import sys
import os
from utils.data_loader import load_data, filter_by_date, get_date_filters
from utils.kpis import compute_kpis, display_kpis
from utils.tables import render_day_table, calculate_summary_table, display_summary_table, compute_difference_between_kpis
from utils.charts import labels, plot_line_vs_bar
from utils.styling import inject_mobile_css, is_mobile
from utils.general import format_fecha_column

st.set_page_config(page_title="Dashboard Entrenamiento", layout="wide")

def main():
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

    map_metrics = {"workload": "sum", "effective_set": "sum", "1rm": "max"}
    labels_kpis = [labels[4]] + [labels[2]] + [labels[5]]

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

    kpis_curr = compute_kpis(df_filtered, agg_map=map_metrics)
    kpis_prev = compute_kpis(df_prev, agg_map=map_metrics)

    daily_metrics = calculate_summary_table(
                                        df_now=df_filtered,
                                        group_col="fecha",
                                        metrics=metrics_1,
                                        compare_prev=False
    )
    df_aggregated_processed = calculate_summary_table(
                                        df_now=df_filtered,
                                        df_prev=df_prev,
                                        group_col="routine",
                                        metrics=metrics_2,
    )
    df_muscle_processed = calculate_summary_table(
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
    grouped = compute_difference_between_kpis(grouped, 'Series Efectivas', 'Total Series', drop=True)
    grouped = format_fecha_column(grouped, "fecha", granularity=granularity)
    col_metrics_2 = [col for col in df_aggregated_processed.columns if "prev" not in col]
    col_metrics_3 = [col for col in df_muscle_processed.columns if "prev" not in col]

    # ////////////////// Display ///////////////////////
    st.title("📊 Dashboard de Entrenamiento")
    # Period info display
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
    display_kpis(
        curr=kpis_curr,
        prev=kpis_prev,
        labels=labels_kpis
    )
    plot_line_vs_bar(
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
    display_summary_table(
        daily_metrics,
        group_col="fecha",
        title="📅 Resumen diario",
    )
    display_summary_table(
        df_aggregated_processed[col_metrics_2],
        group_col="routine",
        title="📚 Detalle por rutina"
    )
    display_summary_table(
        df_muscle_processed[col_metrics_3],
        group_col="muscle_name",
        title = "💪 Detalle por músculo"
    )

if __name__ == "__main__":
    main()

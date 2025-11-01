import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

def filter_by_date(df, start_date, end_date):
    """Filter a DataFrame by date range"""
    return df[(df["fecha"] >= pd.to_datetime(start_date)) & (df["fecha"] <= pd.to_datetime(end_date))]

def filter_by_routine(df, routine, routine_col="routine"):
    """
    Filters a DataFrame to return only rows matching the selected routine.
    Raises an error if the column is missing, returns empty if routine not found.
    """
    if routine_col not in df.columns:
        raise KeyError(f"Column '{routine_col}' not found in DataFrame.")
    if routine not in df[routine_col].values:
        st.warning(f"Routine '{routine}' not found in column '{routine_col}'. Returning empty DataFrame.")
        return df.iloc[0:0].copy()
    
    return df[df[routine_col] == routine].copy()

def order_historial(df):
    """
    Orders a DataFrame by 'fecha' descending and 'id_serie' ascending if present.
    Returns the original DataFrame if those columns are missing or DataFrame is empty.
    """
    if df.empty:
        return df

    sort_cols = []
    ascending = []

    if "fecha" in df.columns:
        sort_cols.append("fecha")
        ascending.append(False)
    if "id_set" in df.columns:
        sort_cols.append("id_set")
        ascending.append(True)

    if not sort_cols:
        st.warning("No columns found for ordering. Returning original DataFrame.")
        return df

    return df.sort_values(by=sort_cols, ascending=ascending)

def format_fecha_column(df: pd.DataFrame, col_fecha: str, granularity: str) -> pd.DataFrame:
    """
    Formats the 'fecha' column in df based on the time granularity.
    """
    if 'fecha' not in df.columns:
        raise ValueError("'fecha' column is required.")

    # Ensure it's datetime
    df['fecha'] = pd.to_datetime(df['fecha'])

    if granularity in ['D', 'day']:
        df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d')
    elif granularity in ['W', 'week']:
        df['fecha'] = df['fecha'].dt.strftime('%G-W%V')
    elif granularity in ['M', 'month']:
        df['fecha'] = df['fecha'].dt.strftime('%Y-%m')
    else:
        # fallback to ISO format if unknown granularity
        df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df

def get_date_filters(df, fecha_col=None, label="Rango de fechas", default_weeks=6):
    """
    Crea el selector de rango de fechas en el sidebar y devuelve:
        start_date, end_date, prev_start, prev_end
    """
    if fecha_col is None:
        fecha_col = 'fecha'
    try:
        min_date, max_date = df[fecha_col].min(), df[fecha_col].max()
        today = datetime.today().date()

        # Conversión segura
        if isinstance(min_date, pd.Timestamp):
            min_date = min_date.date()
        if isinstance(max_date, pd.Timestamp):
            max_date = max_date.date()

        # Defaults: últimas N semanas
        default_start = max(today - timedelta(weeks=default_weeks), min_date)
        default_end = min(today, max_date)

        # Validación de fechas
        if min_date > max_date:
            st.error("Error: las fechas del dataset no son válidas.")
            st.stop()

        start_date, end_date = st.sidebar.date_input(
            label,
            value=[default_start, default_end],
            min_value=min_date,
            max_value=max_date,
        )

        # Calcular periodo previo
        period_length = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)

        return start_date, end_date, prev_start, prev_end, period_length

    except ValueError:
        st.sidebar.warning("Por favor selecciona un rango válido de fechas (inicio y fin).")
        st.write("Esperando selección de rango de fechas...")
        st.stop()

    except Exception as e:
        st.error(f"Error al procesar fechas: {e}")
        st.stop()

def reorder_columns(cols: list):
    base_cols = [col for col in cols if not col.startswith("Δ_")]
    reordered = []
    for col in base_cols:
        reordered.append(col)
        delta = f"Δ_{col}"
        if delta in cols:
            reordered.append(delta)
    return reordered
"""
History Page

This script generates the "History" page for the Streamlit dashboard. It allows users to view historical training data by routine or by exercise.

Features:
- **Data Loading**: Fetches user-specific training data from the database.
- **Routine History**: Displays historical data for selected routines.
- **Exercise History**: Displays historical data for selected exercises.

Modules:
- `load_data`: Loads training data for the authenticated user.
- `filter_by_routine`: Filters data based on the selected routine.
- `order_historial`: Orders historical data for display.
- `rep_concatenate`: Formats repetition data for display.

Dependencies:
- `streamlit`
- `pandas`
- Utility modules: `data_loader`, `datawrangling`
- Database module: `db_connector`

"""

import streamlit as st
import pandas as pd
from utils.data_loader import load_data
from services.datawrangling import filter_by_routine, order_historial, rep_concatenate
import database.db_connector as db_connector

st.set_page_config(page_title="Histórico de Rutinas", layout="wide")

# ---------- Data Loading ----------
df, df_muscles = load_data()

# ---------- Page Tabs ----------
st.title('🗓️ Histórico de Entrenamientos')
tab1, tab2 = st.tabs(["Por Rutina", "Por Ejercicio"])

# ---------- Tab 1: Histórico por Rutina ----------
with tab1:
    routines = df['routine'].unique()
    selected_routine = st.selectbox("Selecciona la rutina", routines)

    df_filtered = filter_by_routine(df, selected_routine, 'routine')
    df_filtered = order_historial(df_filtered)

    dates = df_filtered['fecha'].dt.strftime('%Y-%m-%d').unique()[:20]

    for date in dates:
        st.markdown(f"📅 {date}")
        df_date = df_filtered[df_filtered['fecha'].dt.strftime('%Y-%m-%d') == date].copy()
        df_date = rep_concatenate(df_date)

        columns_mapping = {
            'fecha': 'Fecha',
            'exercise': 'Ejercicio',
            'reprange': 'Rango',
            'repreal': 'Reps',
            'weight': 'Peso',
            'rir': 'RIR'
        }

        df_date.rename(columns=columns_mapping, inplace=True)
        df_date['Fecha'] = df_date['Fecha'].dt.strftime('%Y-%m-%d')

        columns_to_show = ['Ejercicio', 'Rango', 'Reps', 'Peso', 'RIR']
        columns_to_show = [col for col in columns_to_show if col in df_date.columns]

        st.dataframe(df_date[columns_to_show].set_index('Ejercicio'))

# ---------- Tab 2: Histórico por Ejercicio ----------
with tab2:
    exercises = df['exercise'].unique()
    selected_exercise = st.selectbox("Selecciona el ejercicio", exercises)

    df_exercise = df[df['exercise'] == selected_exercise].copy()
    df_exercise = order_historial(df_exercise)

    if not df_exercise.empty:
        df_exercise = rep_concatenate(df_exercise)

        columns_mapping = {
            'fecha': 'Fecha',
            'exercise': 'Ejercicio',
            'reprange': 'Rango',
            'repreal': 'Reps',
            'weight': 'Peso',
            'rir': 'RIR'
        }

        df_exercise.rename(columns=columns_mapping, inplace=True)
        df_exercise['Fecha'] = df_exercise['Fecha'].dt.strftime('%Y-%m-%d')

        columns_to_show = ['Fecha', 'Ejercicio', 'Rango', 'Reps', 'Peso', 'RIR']
        columns_to_show = [col for col in columns_to_show if col in df_exercise.columns]

        dates_exercise = df_exercise['Fecha'].unique()[:20]

        for date in dates_exercise:
            st.markdown(f"📅 {date}")
            df_date = df_exercise[df_exercise['Fecha'] == date].copy()
            st.dataframe(df_date[columns_to_show].set_index('Ejercicio'))
    else:
        st.info("No hay registros para este ejercicio.")

# No main function in this script; the logic is executed directly at the module level.
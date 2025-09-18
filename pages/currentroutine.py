"""
Current Routine Page

This script generates the "Current Routine" page for the Streamlit dashboard. It allows users to view, edit, and save their current workout routines, as well as calculate their one-rep max (1RM).

Features:
- **Data Loading**: Fetches user-specific routine data from Google Sheets and the database.
- **Routine History**: Displays historical data for the selected routine.
- **Routine Editing**: Provides an interface for editing and adding exercises to the current routine.
- **Data Validation**: Validates the entered routine data before saving.
- **1RM Calculator**: Includes a calculator for estimating one-rep max values.

Modules:
- `load_dim_data`: Loads dimension data for exercises.
- `read_and_clean_sheet`: Reads and cleans data from Google Sheets.
- `filter_by_routine`: Filters data based on the selected routine.
- `editable_dataframe`: Provides an editable interface for routine data.
- `validate_current_routine`: Validates the entered routine data.
- `load_data_into_gsheet`: Saves validated data back to Google Sheets.
- `run_1rm_calculator`: Runs the one-rep max calculator.

Dependencies:
- `streamlit`
- `pandas`
- `numpy`
- `dotenv`
- `gspread`
- Utility modules: `data_loader`, `tables`, `rm_calculator`, `data_validation`

"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder

from services.datawrangling import order_and_concat_reps, rep_concatenate, filter_by_routine
from utils.data_loader import load_and_prepare_data, load_data, load_dim_data
from services.rm_calculator import run_1rm_calculator
from services.etl_oltp_to_olap import create_exercise_dimension_table
from database.gsheet_connnector import read_and_clean_sheet, load_data_into_gsheet, get_gsheet_credentials
from database.data_validation import validate_current_routine
from utils.tables import reformat_historical_routine_for_display, editable_dataframe

st.set_page_config(page_title="Entrena", layout="wide")

def main():
    """
    Main function to render the Current Routine page.

    This function handles the following tasks:
    - Loads user-specific routine data from Google Sheets and the database.
    - Displays historical data for the selected routine.
    - Provides an interface for editing and adding exercises to the current routine.
    - Validates and saves the entered routine data.
    - Includes a one-rep max (1RM) calculator for estimating maximum lift weights.

    Returns:
        None
    """

    # Get user ID from session state if authenticated
    user_id = st.session_state.get("user_id", None)
    # Cargar variables de entorno
    load_dotenv()

    #  Conectarme a Google Sheets
    client = get_gsheet_credentials()
    fitness_personal_key = os.getenv("GOOGLE_SHEET_KEY_FITNESS_PERSONAL")
    spreadsheet_fitness_personal = client.open_by_key(fitness_personal_key)

    # Cargar datos de la base de datos
    sql_data = load_dim_data()

    # //////////////////// Load Data //////////////////////
    try:
        if "routine_template" not in st.session_state or "df" not in st.session_state:
            df = read_and_clean_sheet(spreadsheet_fitness_personal, worksheet_name='TrackRecord', date_cols=['fecha'])
            routine_template = read_and_clean_sheet(spreadsheet_fitness_personal, worksheet_name='Routines')
            st.session_state["df"] = df
            st.session_state["routine_template"] = routine_template
        else:
            df = st.session_state["df"]
            routine_template = st.session_state["routine_template"]
        
        exercises = sql_data['exercises']

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.info("Por favor, importa datos a través del panel de administración en la página de inicio.")
        return

    # /////////////////////// Filter ///////////////////////

    # Seleccionar la rutina
    routines = df['routine_name'].unique()

    # /////////////////////// Display //////////////////////
    st.title('🏋🏽‍♂️ Entrenamiento')

    # Filter by Routine
    selected_routine = st.selectbox("Selecciona la rutina", routines)
    df_filtered = filter_by_routine(df, selected_routine, 'routine_name')

    # ///////// Section 1: Histórico
    st.subheader("📅 Historial de la rutina")

    # Select a date for show the history
    dates = df_filtered.sort_values(by='fecha', ascending=False)['fecha'].dt.strftime('%Y-%m-%d').unique()
    selected_date = st.selectbox("Historial para esta rutina:", dates)

    # Historico de rutinas
    df_filtered_by_date = df_filtered[df_filtered['fecha'].dt.strftime('%Y-%m-%d') == selected_date]
    df_filtered_by_date = order_and_concat_reps(df_filtered_by_date)
    df_hist, columns_to_show, height = reformat_historical_routine_for_display(df_filtered_by_date)
    st.dataframe(df_hist[columns_to_show].set_index('Ejercicio'), height=height)

    # ///////// Section 2: Ingresar Datos
    st.subheader("📥 Ingreso de rutina")

    # Plantilla de rutinas
    routine_template_filtered = filter_by_routine(routine_template, selected_routine, 'routine_name')
    routine_template_filtered = routine_template_filtered[['exercise', 'repmin', 'repmax']].copy()
    routine_template_filtered = rep_concatenate(routine_template_filtered, "repmin", "repmax").reset_index(drop=True)
    exercises_template = routine_template_filtered.exercise.unique()

    # Lista de ejercicios completos
    capitalized_names = exercises['english_name'].str.capitalize().sort_values().tolist()
    capitalized_names.insert(0, '-')
    
    st.info("**Nota: Rellenar RIR con los siguientes valores: F, 0, 1, 2, 3, 4, 5**")

    all_edited_dfs = []
    for i, exercise_template in enumerate(exercises_template):

        if exercise_template in capitalized_names:
            idx_exercise = capitalized_names.index(exercise_template)
        else:
            st.warning(f"Ejercicio no encontrado: {exercise_template}")
            idx_exercise = 0  # fallback

        exercise_selection = st.selectbox(
            "Selecciona el ejercicio",
            options=capitalized_names,
            index=idx_exercise,
            key=f'selectbox_exercise_{i}',
            label_visibility="hidden"
        )
        edited_df = editable_dataframe(routine_template_filtered, exercise_selection, idx=i)
        all_edited_dfs.append(edited_df)

    # Estado para ejercicios adicionales manuales
    if "extra_blocks" not in st.session_state:
        st.session_state.extra_blocks = []

    if st.button("➕ Agregar ejercicio"):
        st.session_state.extra_blocks.append(capitalized_names[1])

    # Mostrar ejercicios adicionales
    for j, extra_exercise in enumerate(st.session_state.extra_blocks):
        cols = st.columns([6, 1])
        with cols[0]:
            idx = len(exercises_template) + j  # índice único
            selected_extra = st.selectbox(
                "Selecciona el ejercicio adicional",
                options=capitalized_names,
                index=capitalized_names.index(extra_exercise) if extra_exercise in capitalized_names else 0,
                key=f'selectbox_extra_{j}',
                label_visibility="visible"
            )
            st.session_state.extra_blocks[j] = selected_extra
            extra_df = editable_dataframe(routine_template_filtered, selected_extra, idx=idx)
            all_edited_dfs.append(extra_df)

        with cols[1]:
            if st.button("🗑️", key=f"delete_extra_{j}"):
                st.session_state.extra_blocks.pop(j)
                st.rerun()

    # Guardar datos y validar
    if "trigger_guardado" not in st.session_state:
        st.session_state["trigger_guardado"] = False

    if st.button("Guardar datos ingresados"):
        st.session_state["trigger_guardado"] = True

    if st.session_state["trigger_guardado"]:
        combined_df = pd.concat(all_edited_dfs, ignore_index=True)
        if not combined_df.empty:
            combined_df['RIR'] = combined_df['RIR'].apply(lambda x: str(int(x)) if x != "F" else x)
            validated_df = validate_current_routine(combined_df)
            if validated_df is None:
                st.warning("Validación incompleta. Por favor revisa las advertencias.")
                return  # ⚠️ Detenemos sin resetear trigger para permitir confirmar checkboxes
            try:
                st.success("Datos guardados correctamente.")
                st.dataframe(validated_df)
                load_data_into_gsheet(
                    spreadsheet_fitness_personal,
                    df=validated_df,
                    worksheet_name='Test'
                )
                st.session_state["trigger_guardado"] = False  # reset
            except Exception as e:
                st.error(f"Error guardando datos: {e}")
        else:
            st.warning("No hay datos para guardar.")
            st.session_state["trigger_guardado"] = False


    # //////////// Section 3: Calcular RMs
    st.markdown("---")
    st.subheader("🧮 Calculadora de RM")
    st.caption("Calcula cuánto peso máximo podrías levantar entre 1 y 10 repeticiones.")
    run_1rm_calculator()

if __name__ == "__main__":
    main()

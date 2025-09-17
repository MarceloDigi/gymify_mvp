import streamlit as st
import pandas as pd
from utils.data_loader import load_and_prepare_data
from utils.datawrangling import filter_by_routine, rep_concatenate

st.set_page_config(page_title="Plantillas de Rutinas", layout="wide")

# ---------- Data Loading ----------
routine_template = load_and_prepare_data(
    "data/Fitness Personal - Routines.csv",
    snake_case=True
)
exercises = load_and_prepare_data(
    "data/TrackRecord - MuscleRoles.csv",
    snake_case=True
)

# ---------- Display Routine Templates ----------
st.title('📋 Plantillas de Rutinas')
tab1, tab2 = st.tabs(["Rutinas", "Ejercicios"])

# ---------------- Tab 1
with tab1:
    routines = routine_template['routine'].unique()

    for routine in routines:
        st.subheader(f"🏋️ {routine}")

        routine_template_filtered = filter_by_routine(routine_template, routine, 'routine')
        routine_template_filtered = routine_template_filtered[['exercise', 'rep_t_min', 'rep_t_max']].copy()
        routine_template_filtered = rep_concatenate(routine_template_filtered, "rep_t_min", "rep_t_max").reset_index(drop=True)

        columns_mapping = {
            'exercise': 'Ejercicio',
            'reprange': 'Rango'
        }

        routine_template_filtered.rename(columns=columns_mapping, inplace=True)

        columns_to_show = ['Ejercicio', 'Rango']

        st.dataframe(routine_template_filtered[columns_to_show].set_index('Ejercicio'))

# ---------------- Tab 2
with tab2:
    columns_to_show = ['id_exercise','id_muscle','id_rol']
    exercises = exercises[columns_to_show]
    exercises.rename(columns=
        {'id_exercise':'Ejercicio',
         'id_muscle':'Grupo muscular',
         'id_rol':'Rol'
         },
         inplace=True
    )
    row_height = 35  # Approx row height in pixels
    num_rows = exercises.shape[0]
    height = 100 + num_rows * row_height  # 100 for header padding
    st.dataframe(exercises.set_index('Ejercicio'), height=height)
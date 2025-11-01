"""
Routine Templates Page

This script generates the "Routine Templates" page for the Streamlit dashboard. It allows users to view predefined workout routines and their associated exercises.

Features:
- **Data Loading**: Loads routine templates and exercise data from CSV files.
- **Routine Templates**: Displays predefined routines with their exercises and repetition ranges.
- **Exercise Details**: Displays detailed information about exercises, including muscle groups and roles.

Modules:
- `load_and_prepare_data`: Loads and preprocesses data from CSV files.
- `filter_by_routine`: Filters data based on the selected routine.
- `rep_concatenate`: Formats repetition data for display.

Dependencies:
- `streamlit`
- `pandas`
- Utility modules: `data_loader`, `datawrangling`

"""

import streamlit as st
import services.datawrangling as dw
import utils.filters_and_sort as fs

st.set_page_config(page_title="Plantillas de Rutinas", layout="wide")

# ---------- Data Loading ----------
df_templates = st.session_state.get("df_templates")
df_exercise_dimension_table = st.session_state.get("exercise_dimension_table")

if df_templates is None or df_exercise_dimension_table is None:
    st.warning("Datos no cargados. Vuelve a la página principal para inicializarlos.")
    st.stop()

# ---------- Display Routine Templates ----------
st.title('📋 Plantillas de Rutinas')
tab1, tab2 = st.tabs(["Rutinas", "Ejercicios"])

# ---------------- Tab 1
with tab1:
    routines = df_templates['routine_name'].unique()

    for routine in routines:
        st.subheader(f"🏋️ {routine}")

        df_templates_filtered = fs.filter_by_routine(df_templates, routine, 'routine_name')
        df_templates_filtered = df_templates_filtered[['exercise', 'repmin', 'repmax']].copy()
        df_templates_filtered = dw.rep_concatenate(df_templates_filtered, "repmin", "repmax").reset_index(drop=True)

        columns_mapping = {
            'exercise': 'Ejercicio',
            'reprange': 'Rango'
        }

        df_templates_filtered.rename(columns=columns_mapping, inplace=True)

        columns_to_show = ['Ejercicio', 'Rango']

        st.dataframe(df_templates_filtered[columns_to_show].set_index('Ejercicio'))

# ---------------- Tab 2
with tab2:
    columns_to_show = ['exercise_name','muscle_name','rol']
    exercises = df_exercise_dimension_table[columns_to_show]
    exercises.rename(columns=
        {'exercise_name':'Ejercicio',
         'muscle_name':'Grupo muscular',
         'rol':'Rol'
         },
         inplace=True
    )
    row_height = 35  # Approx row height in pixels
    num_rows = exercises.shape[0]
    height = 100 + num_rows * row_height  # 100 for header padding
    st.dataframe(exercises.set_index('Ejercicio'), height=height)

# No main function in this script; the logic is executed directly at the module level.
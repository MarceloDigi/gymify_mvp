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
import services.datawrangling as dw
import utils.filters_and_sort as fs

st.set_page_config(page_title="Histórico de Rutinas", layout="wide")

# ---------- Data Loading ----------
df_track_record = st.session_state.get("df_track_record")

if df_track_record is None:
    st.warning("Datos no cargados. Vuelve a la página principal para inicializarlos.")
    st.stop()

# ---------- Page Tabs ----------
st.title('🗓️ Histórico de Entrenamientos')
tab1, tab2 = st.tabs(["Por Rutina", "Por Ejercicio"])

# ---------- Tab 1: Histórico por Rutina ----------
with tab1:
    routines = sorted(df_track_record['routine'].unique())
    selected_routine = st.selectbox("Selecciona la rutina", routines)

    df_track_record_filtered = fs.filter_by_routine(df_track_record, selected_routine, 'routine')
    df_track_record_filtered = fs.order_historial(df_track_record_filtered)

    dates = df_track_record_filtered['fecha'].dt.strftime('%Y-%m-%d').unique()[:20]

    for date in dates:
        st.markdown(f"📅 {date}")
        df_track_record_date = df_track_record_filtered[df_track_record_filtered['fecha'].dt.strftime('%Y-%m-%d') == date].copy()
        df_track_record_date = dw.rep_concatenate(df_track_record_date)

        columns_mapping = {
            'fecha': 'Fecha',
            'exercise': 'Ejercicio',
            'reprange': 'Rango',
            'repreal': 'Reps',
            'weight': 'Peso',
            'rir': 'RIR'
        }

        df_track_record_date.rename(columns=columns_mapping, inplace=True)
        df_track_record_date['Fecha'] = df_track_record_date['Fecha'].dt.strftime('%Y-%m-%d')

        columns_to_show = ['Ejercicio', 'Rango', 'Reps', 'Peso', 'RIR']
        columns_to_show = [col for col in columns_to_show if col in df_track_record_date.columns]

        st.dataframe(df_track_record_date[columns_to_show].set_index('Ejercicio'))

# ---------- Tab 2: Histórico por Ejercicio ----------
with tab2:
    exercises = sorted(df_track_record['exercise'].unique())
    selected_exercise = st.selectbox("Selecciona el ejercicio", exercises)

    df_track_record_exercise = df_track_record[df_track_record['exercise'] == selected_exercise].copy()
    df_track_record_exercise = fs.order_historial(df_track_record_exercise)

    if not df_track_record_exercise.empty:
        df_track_record_exercise = dw.rep_concatenate(df_track_record_exercise)

        columns_mapping = {
            'fecha': 'Fecha',
            'exercise': 'Ejercicio',
            'reprange': 'Rango',
            'repreal': 'Reps',
            'weight': 'Peso',
            'rir': 'RIR'
        }

        df_track_record_exercise.rename(columns=columns_mapping, inplace=True)
        df_track_record_exercise['Fecha'] = df_track_record_exercise['Fecha'].dt.strftime('%Y-%m-%d')

        columns_to_show = ['Fecha', 'Ejercicio', 'Rango', 'Reps', 'Peso', 'RIR']
        columns_to_show = [col for col in columns_to_show if col in df_track_record_exercise.columns]

        dates_exercise = df_track_record_exercise['Fecha'].unique()[:20]

        for date in dates_exercise:
            st.markdown(f"📅 {date}")
            df_track_record_date = df_track_record_exercise[df_track_record_exercise['Fecha'] == date].copy()
            st.dataframe(df_track_record_date[columns_to_show].set_index('Ejercicio'))
    else:
        st.info("No hay registros para este ejercicio.")

# No main function in this script; the logic is executed directly at the module level.
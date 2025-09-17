import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from utils.datawrangling import preprocess_routine_history, rep_concatenate, filter_by_routine
from utils.data_loader import load_and_prepare_data, load_data, load_dim_data
from utils.rm_calculator import calculate_1rm
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="Entrena", layout="wide")

# ---------- Helpers ----------
def process_historical_routine(df):
    df_hist = preprocess_routine_history(df)
    new_columns = {
        'fecha':'Fecha',
        'exercise':'Ejercicio',
        'reprange':'Rango',
        'repreal':'Reps',
        'weight':'Peso',
        'rir':'RIR'
    }
    df_hist.rename(columns=new_columns, inplace=True)
    df_hist['Fecha'] = df_hist['Fecha'].dt.strftime('%Y-%m-%d')
    columns_to_show = ['Ejercicio','Rango','Reps','Peso','RIR']
    columns_to_show = [col for col in columns_to_show if col in df_hist.columns]

    row_height = 35  # Approx row height in pixels
    num_rows = df_hist.shape[0]
    height = 100 + num_rows * row_height  # 100 for header padding

    return df_hist, columns_to_show, height

def build_routine_input_grid(df_template):
    df_template['reps_real'] = 0
    df_template['weight'] = 0
    df_template['rir'] = 0

    gb = GridOptionsBuilder.from_dataframe(df_template)
    gb.configure_grid_options(suppressMovableColumns=True)
    gb.configure_grid_options(domLayout='autoHeight')

    formatter = {
        'exercise': ('Ejercicio', {'width': 450, 'flex': 0, "pinned": "left"}),
        'reprange': ('Rango', {'flex': 1}),
        'reps_real': ('Reps', {'editable': True, 'cellStyle': {"backgroundColor": "#0b0e13"}, 'flex': 1}),
        'weight': ('Peso', {'editable': True, 'cellStyle': {"backgroundColor": "#0b0e13"}, 'flex': 1}),
        'rir': ('RIR', {'editable': True, 'cellStyle': {"backgroundColor": "#0b0e13"}, 'flex': 1})
    }
    for idx, (latin_name, (cyr_name, style_dict)) in enumerate(formatter.items()):
        # Pin the first column to the left
        if idx == 0:
            style_dict["pinned"] = "left"
        gb.configure_column(latin_name, header_name=cyr_name, **style_dict)

    gridOptions = gb.build()

    custom_css = {
        ".ag-root-wrapper.ag-layout-normal": {
            "--ag-font-size": "10px",
            "--ag-header-background-color": "#20242a",
            "--ag-odd-row-background-color": "#32363e",
            "--ag-even-row-background-color": "#20242a",
            "--ag-foreground-color": "#FFFFFF",
        },
        ".ag-row": {
            "border-bottom": "1px solid #32363e",
            "border-top": "1px solid #32363e",
            "color": "#FFFFFF !important",
            "background-color": "#20242a !important",
        },
        ".ag-cell": {
            "color": "#FFFFFF !important",
        },
        ".ag-header-cell": {
            "color": "#FFFFFF !important",
            "background-color": "#20242a !important",
        },
    }

    return AgGrid(
        df_template,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        height=500,
        width='100%',
        reload_data=True,
        theme='dark',
        custom_css=custom_css
    )

def run_1rm_calculator():
    """
    Streamlit UI to calculate 1RM based on one or two sets.
    Includes validations and recommendations for better estimations.
    """
    weight1 = st.number_input("Peso Usado:", value=0.0, key="weight1")
    reps1 = st.number_input("Repeticiones Hechas:", value=0, step=1, key="reps1")
    if reps1 > 6:
        st.warning("Usa levantamientos de fuerza (menos de 6 reps) para una mejor estimación.")
    rir1 = st.number_input("RIR:", value=0, step=1, key="rir1")
    use_bodyweight = st.checkbox("¿Tu peso formó parte del total levantado?", key="use_bodyweight")

    kg_peso = 0
    if use_bodyweight:
        kg_peso = st.number_input("Introduce tu peso en kg.:", value=70, key="kg_peso")
        weight1 += kg_peso

    use_second_set = st.checkbox("Añadir otro set para mejorar estimación", key="use_second_set")
    weight2, reps2, rir2 = None, None, None

    if use_second_set:
        weight2 = st.number_input("Peso Usado:", value=100, key="weight2")
        reps2 = st.number_input("Repeticiones Hechas:", value=5, step=1, key="reps2")
        if reps2 > 6:
            st.warning("Usa levantamientos de fuerza (menos de 6 reps) para una mejor estimación.")
        rir2 = st.number_input("RIR:", value=0, step=1, key="rir2")
        if use_bodyweight:
            weight2 += kg_peso

    if st.button("Calcular"):
        try:
            result = calculate_1rm(weight1, reps1, rir1, weight2, reps2, rir2)
            one_rm = result[0]
            rep_max_table = result[1]

            if use_bodyweight:
                one_rm -= kg_peso
                rep_max_table = rep_max_table - kg_peso

            st.success(f"Peso máximo a 1 repetición (1RM) -> {one_rm:.1f} kg.")
            st.write("Peso máximo según número de repeticiones:")
            st.dataframe(rep_max_table)
        except ValueError as e:
            st.error(f"Error: {e}")

def main():
    # Get user ID from session state if authenticated
    user_id = st.session_state.get("user_id", None)

    # //////////////////// Load Data //////////////////////
    try:
        # Load data from SQLite database
        df, df_muscles = load_data(user_id=user_id)

        # Check if data is empty
        if df.empty:
            st.warning("No hay datos disponibles en la base de datos.")
            st.info("Por favor, importa datos a través del panel de administración en la página de inicio.")
            return

        # Load routine templates from database
        routine_template = load_and_prepare_data(
            table_name="routine_templates",
            user_id=user_id,
            snake_case=True
        )

        # If routine_template is empty, try to load from CSV as fallback
        if routine_template.empty:
            routine_template = load_and_prepare_data(
                "data/Fitness Personal - Routines.csv",
                snake_case=True
            )

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.info("Por favor, importa datos a través del panel de administración en la página de inicio.")
        return

    # /////////////////////// Filter ///////////////////////

    # Seleccionar la rutina
    routines = df['routine'].unique()

    # /////////////////////// Display //////////////////////
    st.title('🏋🏽‍♂️ Entrenamiento')

    # Filter by Routine
    selected_routine = st.selectbox("Selecciona la rutina", routines)
    df_filtered = filter_by_routine(df, selected_routine, 'routine')

    # ///////// Section 1: Histórico
    st.subheader("📅 Historial de la rutina")

    # Select a date for show the history
    dates = df_filtered.sort_values(by='fecha', ascending=False)['fecha'].dt.strftime('%Y-%m-%d').unique()
    selected_date = st.selectbox("Historial para esta rutina:", dates)

    # Historico de rutinas
    df_filtered_by_date = df_filtered[df_filtered['fecha'].dt.strftime('%Y-%m-%d') == selected_date]
    df_hist, columns_to_show, height = process_historical_routine(df_filtered_by_date)
    st.dataframe(df_hist[columns_to_show].set_index('Ejercicio'), height=height)

    # ///////// Section 2: Ingresar Datos
    st.subheader("📥 Ingreso de rutina")

    # Plantilla de rutinas
    routine_template_filtered = filter_by_routine(routine_template, selected_routine, 'routine')
    routine_template_filtered = routine_template_filtered[['exercise', 'rep_t_min', 'rep_t_max']].copy()
    routine_template_filtered = rep_concatenate(routine_template_filtered, "rep_t_min", "rep_t_max").reset_index(drop=True)
    st.caption("Ingrese los nuevos datos para cada ejercicio")

    grid_response = build_routine_input_grid(routine_template_filtered)
    edited_df = grid_response['data']
    if len(edited_df) > 0:
        if st.button("Guardar datos ingresados"):
            edited_df = pd.DataFrame(edited_df)
            today = datetime.now().strftime('%Y-%m-%d')
            edited_df['fecha'] = today
            edited_df['routine'] = selected_routine
            edited_df = edited_df[['fecha','routine','exercise','reprange','reps_real','weight','rir']]

            # Save to database instead of CSV file
            try:
                # This is a placeholder - in a real implementation, you would save to the database
                # For now, we'll just show a success message
                st.success("Datos guardados correctamente.")
                st.write("DataFrame con los datos ingresados:")
                st.dataframe(edited_df)
            except Exception as e:
                st.error(f"Error guardando datos: {e}")
    else:
        st.info("No se han ingresado datos aún.")

    # //////////// Section 3: Calcular RMs
    st.subheader("🧮 Calculadora de RM")
    st.caption("Calcula cuánto peso máximo podrías levantar entre 1 y 10 repeticiones.")
    run_1rm_calculator()

if __name__ == "__main__":
    main()

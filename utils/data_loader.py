import pandas as pd
import streamlit as st

# Add parent directory to path so we can import database modules
import database.db_connector as connector
import services.etl_oltp_to_olap as etl

@st.cache_data
def load_dim_data(exercises: bool = False,
                  pattern: bool = False,
                  roles: bool = False,
                  pattern_muscle_rol: bool = False,
                  equipments: bool = False,
                  muscles: bool = False,
                  exercise_muscle_rol: bool = False,
                  exercise_dim_table: bool = False
                  ) -> dict:
    
    sql_exercises = connector.query_to_dataframe("SELECT * FROM exercises") if exercises else None
    sql_pattern = connector.query_to_dataframe("SELECT * FROM movement_pattern") if pattern else None
    sql_roles = connector.query_to_dataframe("SELECT * FROM rol_names") if roles else None
    sql_pattern_muscle_rol = connector.query_to_dataframe("SELECT * FROM pattern_muscle_rol") if pattern_muscle_rol else None
    sql_equipments = connector.query_to_dataframe("SELECT * FROM equipments") if equipments else None
    sql_muscles = connector.query_to_dataframe("SELECT * FROM muscles") if muscles else None
    sql_exercise_muscle_rol = connector.query_to_dataframe("SELECT * FROM exercise_muscle_roles") if exercise_muscle_rol else None
    view_exercise_dimension_table = etl.create_exercise_dimension_table() if exercise_dim_table else None

    return {
        "exercises": sql_exercises,
        "patterns": sql_pattern,
        "roles": sql_roles,
        "pattern_muscle_rol": sql_pattern_muscle_rol,
        "equipments": sql_equipments,
        "muscles": sql_muscles,
        "exercise_muscle_roles": sql_exercise_muscle_rol,
        'exercise_dimension_table': view_exercise_dimension_table
    }    

def load_workout_data(track_record: bool = True, 
                      track_record_muscles: bool = True):
    """
    Carga los datos principales (workouts y workouts_by_muscle)
    aplicando el filtro por usuario si está en sesión.
    Retorna:
        - df_track_record
        - df_track_record_by_muscles
    """
    try:
        user_id = st.session_state.get("user_id")
        user_filter = f"WHERE user_id = {user_id}" if user_id else ""

        if track_record:
            df_track_record = connector.query_to_dataframe(
                f"SELECT * FROM workouts {user_filter} ORDER BY fecha DESC"
            )
            # Validación de datos
            if df_track_record.empty:
                st.warning("No hay datos disponibles en la base de datos.")
                st.info("Por favor, importa datos desde el panel de administración en la página de inicio.")
                st.stop()

        if track_record_muscles:
            df_track_record_by_muscles = connector.query_to_dataframe(
                f"SELECT * FROM workouts_by_muscle {user_filter} ORDER BY fecha DESC"
            )
            if track_record:
                return df_track_record, df_track_record_by_muscles
            else:
                return df_track_record_by_muscles
        else:
            if track_record:
                return df_track_record

    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.stop()
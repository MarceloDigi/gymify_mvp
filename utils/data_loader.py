import pandas as pd
import streamlit as st

# Add parent directory to path so we can import database modules
import database.db_connector as connector
import services.etl_oltp_to_olap as etl

@st.cache_data(ttl=600, show_spinner=False)
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

@st.cache_data(ttl=600, show_spinner=False)
def load_workout_data(user_id: int | None,
                      track_record: bool = True, 
                      track_record_muscles: bool = True):
    """
    Carga los datos principales aplicando filtro por user_id si existe.
    Nunca detiene la app (no usa st.stop); devuelve DF vacíos si no hay datos.
    """
    user_filter = f"WHERE id_user = {user_id}" if user_id else ""
    df_track_record = pd.DataFrame()
    df_track_record_by_muscles = pd.DataFrame()
    try:
        if track_record:
            df_track_record = connector.query_to_dataframe(
                f"SELECT * FROM workouts {user_filter} ORDER BY fecha DESC"
            )

        if track_record_muscles:
            df_track_record_by_muscles = connector.query_to_dataframe(
                f"SELECT * FROM workouts_by_muscle {user_filter} ORDER BY fecha DESC"
            )

        # Devuelve según flags
        if track_record and track_record_muscles:
            return df_track_record, df_track_record_by_muscles
        elif track_record:
            return df_track_record
        elif track_record_muscles:
            return df_track_record_by_muscles
        else:
            return pd.DataFrame()  # caso raro

    except Exception as e:
        # No parar la app: devuelve vacíos y deja que la UI avise
        st.error(f"Error al cargar datos: {e}")
        if track_record and track_record_muscles:
            return pd.DataFrame(), pd.DataFrame()
        elif track_record:
            return pd.DataFrame()
        elif track_record_muscles:
            return pd.DataFrame()
        else:
            return pd.DataFrame()
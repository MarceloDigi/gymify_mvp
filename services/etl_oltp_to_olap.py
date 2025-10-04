import pandas as pd
import numpy as np
from typing import Optional, Literal

import database.db_connector as connector
import utils.data_loader as loader

def create_exercise_dimension_table() -> pd.DataFrame:
    query = """
    SELECT 
        e.exercise_name,
        e.english_name,
        p.movement_pattern,
        m.muscle_name,
        r.rol,
        r.rol_multiplier
    FROM exercise_muscle_roles emr
    LEFT JOIN exercises e 
        ON emr.id_exercise = e.id_exercise
    LEFT JOIN movement_pattern p 
        ON emr.id_pattern = p.id_pattern
    LEFT JOIN muscles m 
        ON emr.id_muscle = m.id_muscle
    LEFT JOIN rol_names r 
        ON emr.id_rol = r.id_rol;
    """
    try:
        df = connector.query_to_dataframe(query)
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    return df

def create_pattern_muscle_dim_table():
    query = """
    SELECT
        pmr.*,
        p.*,
        m.id_muscle,
        m.muscle_name,
        r.id_rol,
        r.rol
    FROM pattern_muscle_rol AS pmr
    LEFT JOIN movement_pattern AS p
        ON emr.id_pattern = p.id_pattern
    LEFT JOIN muscles AS m
        ON emr.id_muscle = m.id_muscle
    LEFT JOIN rol_names AS r
        ON emr.id_rol = r.id_rol
    """
    try:
        df = connector.query_to_dataframe(query)
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    return df

def add_exercise(exercise_name: str = None,
                 id_user: float = None,
                 id_pattern: str = None,
                 english_name: Optional[str] = None,
                 id_equipment: Optional[str] = None,
                 id_muscle_isolate: Optional[str] = None,
                 pct_body_lifted: Optional[float] = None,
                 fatigue_score: Optional[Literal[1, 2, 3, 4, 5]] = None,
                 is_time_progression: Optional[Literal[True, False]] = False,
                 is_only_reps_progression: Optional[Literal[True, False]] = False
                 ) -> None:
    
    dict_sql = loader.load_dim_data(
        exercises=True,
        pattern=True,
        pattern_muscle_rol=True,
        equipments=True,
        muscles=True)
    
    sql_exercises = dict_sql['exercises']
    sql_pattern = dict_sql['patterns']
    sql_pattern_muscle_rol = dict_sql['pattern_muscle_rol']
    sql_equipments = dict_sql['equipments']
    sql_muscles = dict_sql['muscles']
    pattern_olap = create_pattern_muscle_dim_table()
    
    extract_cols = ['id_exercise','id_pattern']

    exercise_name = exercise_name.strip().capitalize()

    if english_name is not None:
        english_name = english_name.strip().capitalize()

    if exercise_name is None:
        raise ValueError("Tienes que ingresar un ejercicio")
    
    if exercise_name in sql_exercises.exercise_name.values:
        raise ValueError("Este ejercicio ya existe.")
    
    if id_pattern is None:
        raise ValueError("Tienes que ingresar un patrón de movimiento.")
    
    if id_pattern not in sql_pattern.movement_pattern.values:
        raise ValueError("Ese patrón de movimiento no existe.")
    
    id_pattern = pattern_olap.loc[pattern_olap.movement_pattern == id_pattern,'id_pattern'].values[0]
    if id_pattern == 13:
        if id_muscle_isolate is None:
            raise ValueError("Para los ejercicios de aislamiento necesitas introducir que músculo trabaja")
        else:
            extract_cols.append('id_muscle_isolate')
            id_muscle_isolate = sql_muscles.loc[sql_muscles.muscle_name == id_muscle_isolate,'id_muscle'].values[0]
    else:
        if id_muscle_isolate is not None:
            id_muscle_isolate = None
            print("CUIDADO: Sólo se puede asignar un músculo específico a los ejercicios de aislamiento")
        
    if id_equipment is not None:
        id_equipment = sql_equipments.loc[sql_equipments.equipment_name == id_equipment,'id_equipment'].values[0]

    uses_bodyweight = False if pct_body_lifted is None else True

    id_new = sql_exercises.id_exercise.max() + 1
    new_exercise = pd.DataFrame({
        'id_exercise': [id_new],
        'exercise_name': [exercise_name],
        'id_pattern': [id_pattern],
        'id_muscle_isolate': [id_muscle_isolate],
        'id_user': [id_user],
        'fatigue_score': [fatigue_score],
        'id_equipment': [id_equipment],
        'english_name': [english_name],
        'pct_body_lifted': [pct_body_lifted],
        'uses_bodyweight': [uses_bodyweight],
        'is_time_progression': [is_time_progression],
        'is_only_reps_progression': [is_only_reps_progression],
    })

    subset_extracted = new_exercise[extract_cols]
    #sql_exercises_new = pd.concat([sql_exercises, new_exercise], ignore_index=True)
    
    if 'id_muscle_isolate' in extract_cols:
        subset_extracted.rename(columns={'id_muscle_isolate':'id_muscle'}, inplace=True)
        subset_extracted['id_rol'] = 1
    elif id_pattern is None:
        subset_extracted['id_muscle'] = np.nan
        subset_extracted['id_rol'] = np.nan
    else:
        subset_extracted = subset_extracted.merge(sql_pattern_muscle_rol[['id_pattern','id_muscle','id_rol']], how='left', on='id_pattern')

    #sql_exercise_muscle_rol_new = pd.concat([sql_exercise_muscle_rol, subset_extracted], ignore_index=True)
    try:
        engine = connector.get_engine()
        with engine.begin() as connection:  # inicia una transacción automática
            new_exercise.replace('', np.nan).to_sql('exercises', con=connection, if_exists='append', index=False)
            subset_extracted.replace('', np.nan).to_sql('exercise_muscle_roles', con=connection, if_exists='append', index=False)
        print('Añadido exitosamente a la base de datos.')
    except Exception as e:
        print(f'❌ Error al intentar añadir a la base de datos: {e}')
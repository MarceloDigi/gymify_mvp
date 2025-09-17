import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def create_exercise_dimension_table(sql_exercise_muscle_rol,
                                    sql_exercises,
                                    sql_pattern,
                                    sql_muscles,
                                    sql_roles
                                    ):
    exercise_olap = sql_exercise_muscle_rol.merge(sql_exercises[['id_exercise','exercise_name','english_name']], how='left', on='id_exercise')
    exercise_olap = exercise_olap.merge(sql_pattern, how='left', on='id_pattern')
    exercise_olap = exercise_olap.merge(sql_muscles[['id_muscle','muscle_name']], how='left', on='id_muscle')
    exercise_olap = exercise_olap.merge(sql_roles[['id_rol','rol']], how='left', on='id_rol')

    exercise_olap.drop(['id_exercise','id_pattern','id_muscle','id_rol'], axis=1, inplace=True)

    return exercise_olap

def create_pattern_muscle_dim_table(sql_pattern_muscle_rol, sql_pattern, sql_muscles, sql_roles):
    pattern_olap = sql_pattern_muscle_rol.merge(sql_pattern, how='left', on='id_pattern')
    pattern_olap = pattern_olap.merge(sql_muscles[['id_muscle','muscle_name']], how='left', on='id_muscle')
    pattern_olap = pattern_olap.merge(sql_roles[['id_rol','rol']], how='left', on='id_rol')

    return pattern_olap

def add_exercise(exercise_name: str = None, 
                 id_pattern: str = None, 
                 id_muscle_isolate: str = None,
                 id_user: float = None,
                 fatigue_score: int = None,
                 id_equipment: str = None,
                 english_name: str = None,
                 pct_body_lifted: float = None,
                 pattern_olap=None,
                 sql_muscles=None,
                 sql_equipments=None,
                 sql_exercise_muscle_rol=None
                 ):
    
    engine = create_engine("mysql+pymysql://admin:Macs.991014.@localhost/fitnessdb")
    
    sql_exercises = pd.read_sql("SELECT * FROM exercises", con=engine)
    sql_pattern = pd.read_sql("SELECT * FROM movement_pattern", con=engine)
    sql_roles = pd.read_sql("SELECT * FROM rol_names", con=engine)
    sql_pattern_muscle_rol = pd.read_sql("SELECT * FROM pattern_muscle_rol", con=engine)
    sql_equipments = pd.read_sql("SELECT * FROM equipments", con=engine)
    sql_muscles = pd.read_sql("SELECT * FROM muscles", con=engine)
    pattern_olap = create_pattern_muscle_dim_table(sql_pattern_muscle_rol, sql_pattern, sql_muscles, sql_roles)
    sql_exercise_muscle_rol = pd.read_sql("SELECT * FROM exercise_muscle_roles", con=engine)

    extract_cols = cols = ['id_exercise','id_pattern']

    if exercise_name is None:
        raise ValueError("Tienes que ingresar un ejercicio")
    
    if exercise_name in sql_exercises.exercise_name.values:
        raise ValueError("Este ejercicio ya existe.")
    
    if id_pattern is not None:
        if id_pattern in sql_pattern.movement_pattern.values:
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
        else:
            raise ValueError("Ese patrón de movimiento no existe.")
    else:
        print('CUIDADO: Estas añadiendo un ejercicio sin ningún patrón de movimiento asociado')
    
    if id_equipment is not None:
        id_equipment = sql_equipments.loc[sql_equipments.equipment_name == id_equipment,'id_equipment'].values[0]

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
        'pct_body_lifted': [pct_body_lifted]
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
        with engine.begin() as connection:  # inicia una transacción automática
            new_exercise.replace('', np.nan).to_sql('exercises', con=connection, if_exists='append', index=False)
            subset_extracted.replace('', np.nan).to_sql('exercise_muscle_roles', con=connection, if_exists='append', index=False)
        print('Añadido exitosamente a la base de datos.')
    except Exception as e:
        print(f'❌ Error al intentar añadir a la base de datos: {e}')
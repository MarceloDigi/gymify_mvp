import pandas as pd
import numpy as np
from typing import Optional
import pandasql as psql
import logging
from pathlib import Path
from datetime import datetime

import services.etl_oltp_to_olap as etl
import database.db_connector as connector
import services.datawrangling as dw

# Configura un logger a archivo con timestamp
log_dir = Path.cwd() / "logs"
logfile = log_dir / f"etl_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("--- ETL Input (Empezando) ------------------")

def add_id_set_col(df):
    """
    Add an id_set column to uniquely identify each set in the dataframe.
    """
    query = """
    SELECT id_set
    FROM workouts
    ORDER BY id_set DESC
    LIMIT 1;
    """

    id = connector.query_to_dataframe(query, oltp_db=True)
    last_id = int(id.iloc[0, 0])
    print(last_id)

    df['id_set'] = range(last_id + 1, last_id + 1 + len(df))

    return df

def add_analytic_cols(df):
    """
    Add columns for muscle analytics.
    """
    # Workload and effective set columns
    df['workload'] = df.repreal * df.weight
    df['effective_set'] = np.where(df.rir <= 4, 1, 0)
    return df

def add_1rm_columns(df):
  """
  Add 1RM and is_maxrm columns.
  Using Brzycki formula for reps <= 8
  """
  # Crear columna con las repeticiones efectivas (reps hechas + RIR)
  df['reps_potential'] = df.repreal + df.rir.replace(-1,0).fillna(0)

  df['1rm'] = np.where((df.real_weight < 50) | (df.reps_potential <= 0), np.nan, # Filtramos ejercicios con pocas cargas
                  np.where(df.repreal <= 8, df.real_weight / (1.0278 - (0.0278 * df.reps_potential)),  # Brzycki
                            np.nan  # Fuera de rango de precisión
                    )
                  ).astype(float).round(1)

  return df

def add_ismaxrm_column(df): # <-----------------------------------------------------------------------------------------
      # Identify the rows with the max 1RM
    df['is_maxrm'] = 0
    return df

def add_category_cols(df):
    """
    Create ranges for reps and rir for further analysis.
    """
    df['repreal_range'] = pd.cut(df.repreal, 
                                 bins=[-1,6,10,15,np.inf], 
                                 labels=['Fuerza','Hipertrofía-Fuerza','Hipertrofía-Resistencia','Resistencia']
                                 )
    df['rir_range'] = pd.cut(df.rir, 
                             bins=[-2,0,3,4,np.inf], 
                             labels=['F|0','1|2|3','4','+5']
                             )

    return df

def define_progression_exercises(df, progression_exercises: dict):
    """
    Define a column to identify progression tracking exercises.
    """
    df['progress_tracker'] = df.exercise.map(progression_exercises)
    return df

def add_cols_analytics_metrics(df_metrics=None):
    """
    Add columns in the metrics (body) dataset for further merge with the dwh. 
    """
    if df_metrics is not None:
        ss_metrics = df_metrics[['fecha','peso']].copy()
        ss_metrics = dw.convert_date_columns(ss_metrics, multiple_formats=True)
        ss_metrics['fecha_prev'] = ss_metrics.fecha.shift(1)
        ss_metrics['peso_prev'] = ss_metrics.peso.shift(1)
        ss_metrics = ss_metrics[['fecha_prev','peso_prev','fecha','peso']]

        ss_metrics['delta_peso'] = ss_metrics.peso - ss_metrics.peso_prev
        ss_metrics['delta_fecha'] = np.round((ss_metrics.fecha - ss_metrics.fecha_prev).dt.days,0)

        ss_metrics['delta_daily'] = np.round(ss_metrics.delta_peso/ss_metrics.delta_fecha,3)

        return ss_metrics
    
    return None

def add_real_weight_col(df: pd.DataFrame,
                                weight_body_exercises: Optional[list] = None,
                                df_metrics: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Merge the metrics dataset with the df to compute the real bodyweight
    in each training and added to the total weight lifted in those bodyweight exercises.
    """
    if weight_body_exercises is None:
        weight_body_exercises = [
        'Chin-ups', 
        'Parallel bar dips',
        'Pull-ups',
        'Muscle-ups',
        'Neutral grip pull-ups',
        'Ring chin-ups',
        'Parallel bar dips 210',
        'Barbell squat'
        ]

    df_merged = df.copy()

    if df_metrics is not None:
        df_metrics = add_cols_analytics_metrics(df_metrics)
        query = """
        SELECT 
            df.*, 
            df_metrics.fecha_prev, 
            df_metrics.peso_prev, 
            df_metrics.delta_daily, 
            df_metrics.fecha AS fecha_next
        FROM df
        LEFT JOIN df_metrics ON df.fecha >= df_metrics.fecha_prev AND df.fecha < df_metrics.fecha
        """

        df_merged = psql.sqldf(query, locals())

        date_cols = ['fecha', 'fecha_prev', 'fecha_next']
        df_merged[date_cols] = df_merged[date_cols].apply(pd.to_datetime)
        
        max_weight = df_metrics.loc[df_metrics.fecha == df_metrics.fecha.max(),'peso']
        max_date = df_metrics.loc[df_metrics.fecha == df_metrics.fecha.max(),'fecha']
        
        df_merged.loc[df_merged.fecha_prev.isnull(),'fecha_prev'] = [max_date]
        df_merged.loc[df_merged.peso_prev.isnull(),'peso_prev'] = [max_weight]

        df_merged['current_bodyweight'] = np.round(
            np.where(df_merged.delta_daily.isnull(), 
                        df_merged.peso_prev, 
                    (df_merged.fecha - df_merged.fecha_prev).dt.days * df_merged.delta_daily + df_merged.peso_prev)
                    ,2)
        
        df_merged['real_weight'] = np.where(
                            df_merged.exercise.isin(weight_body_exercises), 
                                df_merged.weight + df_merged.current_bodyweight, 
                                    df_merged.weight)
    else:
        df_merged['current_bodyweight'] = np.nan
        df_merged['real_weight'] = df_merged['weight']
    
    return df_merged

def add_training_days_on_week_col(df): # <-----------------------------------------------------------------------------------------
    """
    Create a column with the number of training days on the week of each training date.
    """
    # Training days on week
    df['training_days_on_week'] = 0
    return df

def merge_muscleroles_and_inputdf(df, df_muscleroles):
    """
    Merge the muscle roles dataframe with the input dataframe to create a dataframe by muscle.
    """
    df_muscleroles = df_muscleroles.replace('',np.nan)
    df_muscleroles['english_name'] = df_muscleroles.english_name.str.capitalize()
    ss_muscleroles = df_muscleroles[['muscle_name','rol','english_name','rol_multiplier']].copy()
    
    # Merge
    df_by_muscle = df.merge(ss_muscleroles, 
                            how='left', 
                            left_on='exercise', 
                            right_on='english_name'
                            ).drop(['english_name'], axis=1)
    
    return df_by_muscle

def add_muscle_analytic_cols(df_by_muscle):
    """
    Create columns specific to the muscles granularity for further analysis.
    """
    df_by_muscle['workload_by_muscle'] = df_by_muscle.workload * df_by_muscle.rol_multiplier
    df_by_muscle['sets_by_muscle'] = np.where(df_by_muscle.rol_multiplier == 1, 1,
                                        np.where(df_by_muscle.rol_multiplier ==  0.1, 0,
                                            0.5))
    df_by_muscle['is_set_principal_for_muscle'] = np.where(df_by_muscle.sets_by_muscle == 1,1,0)

    df_by_muscle.drop(['rol','rol_multiplier'], axis=1, inplace=True)

    return df_by_muscle

def add_effective_set_by_muscle_col(df):
    """
    Create a column with the effective sets by muscle.
    """
    df['effective_sets_by_muscle'] = np.where(df.effective_set.isnull(), 
                                              np.nan, 
                                              df.sets_by_muscle * df.effective_set)
    return df

def reorder_cols(df: pd.DataFrame, df_muscles: pd.DataFrame):
    """
    Reorder columns for better readability.
    """
    order = [
    'id_set',
    'routine',
    'fecha',
    'exercise',
    'repmin',
    'repmax',
    'repreal',
    'weight',
    'rir',
    'workload',
    'technique',
    'real_weight',
    'effective_set',
    'training_days_on_week',
    'is_maxrm',
    '1rm',
    'repreal_range',
    'rir_range',
    'progress_tracker',
    'id_user'
    ]
    order_muscles = [
    'id_set',
    'muscle_name',
    'routine',
    'fecha',
    'exercise',
    'repmin',
    'repmax',
    'repreal',
    'weight',
    'rir',
    'workload',
    'technique',
    'workload_by_muscle',
    'sets_by_muscle',
    'is_set_principal_for_muscle',
    'real_weight',
    'effective_set',
    'effective_sets_by_muscle',
    'training_days_on_week',
    'is_maxrm',
    '1rm',
    'repreal_range',
    'rir_range',
    'progress_tracker',
    'id_user'
    ]

    df = df[order]
    df_muscles = df_muscles[order_muscles]

    return df, df_muscles

def complete_cleaning(input_user_df, muscle_roles):
    """
    Complete cleaning process for the input user dataframe.
    """
    logging.info("Inicio de complete_cleaning()")

    try:
        df = dw.basic_cleanings(
            df=input_user_df,
            date_columns=['fecha'],
            float_cols=['peso'],
            int_cols=['rir', 'reps'],
            rename_cols={'ejercicio': 'exercise', 'reps': 'repreal', 'peso': 'weight'}
        )
        logging.info(f"✅ Basic cleanings completado: {len(df)} filas.")
    except Exception as e:
        logging.exception("❌ Error en basic_cleanings")
        return None, None

    try:
        df['exercise'] = df['exercise'].str.capitalize()
        df = dw.range_col_cleaning(df)
        df = dw.repmin_cleaning(df)
        logging.info(f"✅ Cleaning adicional completado: {len(df)} filas.")
    except Exception as e:
        logging.exception("❌ Error en cleaning adicional")
        return None, None

    try:
        # Feature Engineering
        df = add_id_set_col(df)
        df = add_analytic_cols(df)
        df = add_real_weight_col(df)
        df = add_training_days_on_week_col(df)
        df = add_1rm_columns(df)
        df = add_ismaxrm_column(df)
        df = add_category_cols(df)
        logging.info(f"✅ Feature engineering completado: {len(df)} filas.")
    except Exception as e:
        logging.exception("❌ Error en feature engineering")
        return None, None

    try:
        progression_exercises = {
            'Pull-ups': 'Compound',
            'Romanian deadlift': 'Compound',
            'Parallel bar dips': 'Compound',
            'Smith machine squat': 'Compound',
            'Preacher curl machine': 'Isolate',
            'Dumbbell lateral raise': 'Isolate',
            'Incline machine press': 'Isolate',
            'Machine row': 'Isolate',
            'Calf raise on machine': 'Isolate'
        }

        df = define_progression_exercises(df, progression_exercises)
        df_by_muscle = merge_muscleroles_and_inputdf(df, muscle_roles)
        logging.info(f"✅ Merge muscleroles: {len(df_by_muscle)} filas.")
    except Exception as e:
        logging.exception("❌ Error durante merge muscleroles")
        return None, None

    try:
        df_by_muscle = add_muscle_analytic_cols(df_by_muscle)
        df_by_muscle = add_effective_set_by_muscle_col(df_by_muscle)
        logging.info(f"✅ Cálculo analítico por músculo: {len(df_by_muscle)} filas.")
    except Exception as e:
        logging.exception("❌ Error en add_muscle_analytic_cols o add_effective_set_by_muscle_col")
        return None, None

    try:
        df, df_by_muscle = reorder_cols(df, df_by_muscle)
        logging.info(f"✅ Reordenado de columnas OK. df={len(df)}, df_by_muscle={len(df_by_muscle)}")
    except Exception as e:
        logging.exception("❌ Error en reorder_cols")
        return None, None

    logging.info("✅ ETL completada correctamente")
    return df, df_by_muscle

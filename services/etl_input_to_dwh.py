import pandas as pd
import numpy as np
from typing import Optional
import pandasql as psql
import services.etl_oltp_to_olap as etl
import database.db_connector as connector

def snake_case(df):
    df.columns = df.columns.str.lower().str.replace(' ','_')

def drop_empty_rows(df, fecha_col: str = 'fecha'):
    df.dropna(axis=0, how='all') # Elinimaos filas donde todos los valores son nulos
    df.drop(df[df[fecha_col].isnull()].index, inplace=True) # Eliminamos filas donde la fecha es nula (just in case)
    return df

def convert_date_columns(df, date_columns: list, multiple_formats=False, desired_format='%Y-%m-%d'):
    """
    Converts specified columns in a DataFrame to datetime format.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        date_columns (list): List of column names to convert to datetime.
        multiple_formats (bool): Indicate if there are multiple columns within the same column.
        desired_format (str): Format used by default.

    Returns:
        pd.DataFrame: DataFrame with converted date columns.
    """
    if multiple_formats == False:
        df[date_columns] = df[date_columns].apply(pd.to_datetime, format=desired_format)
    else:
        for col in date_columns:
            df['fecha_1'] = pd.to_datetime(df[col], format='%Y - %m', errors='coerce')
            df['fecha_2'] = pd.to_datetime(df[col], format='%Y - %m - %d', errors='coerce')
            df['fecha_3'] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
            df[col] = df[['fecha_1','fecha_2','fecha_3']].max(1)
            df.drop(['fecha_1', 'fecha_2','fecha_3'], axis=1, inplace=True)

    return df

def convert_right_formats(df, int_cols: list = ['reps','rir'], float_cols: list = ['peso']):
    # Right formats
    pd.set_option('future.no_silent_downcasting', True)

    df = df.replace('',np.nan)
    df[float_cols] = df[float_cols].astype(float)
    df[int_cols] = df[int_cols].astype(int)
    return df

def basic_cleanings(df: pd.DataFrame, 
                    date_columns: list = ['fecha'], 
                    int_cols: list = ['reps','rir'], 
                    float_cols: list = ['peso']):
    
    snake_case(df)
    df = drop_empty_rows(df)
    df = convert_date_columns(df, date_columns=date_columns)
    df = convert_right_formats(df, int_cols=int_cols, float_cols=float_cols)
    df.rename(columns={'ejercicio':'exercise','reps':'repreal','peso':'weight'}, inplace=True)
    return df

def add_id_set_col(df, conn):
    """
    Add an id_set column to uniquely identify each set in the dataframe.
    """
    query = """
    SELECT id_set
    FROM workouts
    ORDER BY id_set DESC
    LIMIT 1;
    """

    id = pd.read_sql(query, con=conn)
    last_id = int(id.iloc[0, 0])

    df['id_set'] = range(last_id + 1, last_id + 1 + len(df))

    return df

def range_col_cleaning(df):
    """
    Clean and split the range column into repmin, repmax and technique.
    """
    # Range column
    range_sep = df['rango'].str.split(' - ', expand=True).rename(columns={0: 'repmin', 1: 'repmax'})
    df = pd.concat([df, range_sep], axis=1).drop(columns=['rango'])
    return df

def repmin_cleaning(df):
    """
    Clean the repmin column into technique and repmin numeric.
    """
    # Technique column and repmin cleaning
    df["technique"] = df["repmin"].where(df["repmin"].str.isalpha())
    df['repmin'] = pd.to_numeric(df['repmin'], errors='coerce')
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
  
  # Identify the rows with the max 1RM
  max_rm_exercise = df.loc[df['1rm'].notnull()].groupby('exercise')['1rm'].max().reset_index()
  max_rm_exercise['is_maxrm'] = 1
  df['is_maxrm'] = 0
  df = df.merge(max_rm_exercise, how='left', on=['exercise','1rm'], suffixes=('','_new'))
  df['is_maxrm'] = df[['is_maxrm','is_maxrm_new']].max(1)

  df.drop(['is_maxrm_new'], axis=1, inplace=True)

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
        query = """
        SELECT df.*, df_metrics.fecha_prev, df_metrics.peso_prev, df_metrics.delta_daily, df_metrics.fecha AS fecha_next
        FROM df
        LEFT JOIN df_metrics ON df.fecha >= df_metrics.fecha_prev AND df.fecha < df_metrics.fecha
        """

        df_merged = psql.sqldf(query, locals())

        df_merged[['fecha', 'fecha_prev', 'fecha_next']] = df_merged[['fecha', 'fecha_prev', 'fecha_next']].apply(pd.to_datetime)
        
        max_weight = df_metrics.loc[df_metrics.fecha == df_metrics.fecha.max(),'peso']
        max_date = df_metrics.loc[df_metrics.fecha == df_metrics.fecha.max(),'fecha']
        
        df_merged.loc[df_merged.fecha_prev.isnull(),'fecha_prev'] = [max_date]
        df_merged.loc[df_merged.peso_prev.isnull(),'peso_prev'] = [max_weight]

        df_merged['current_bodyweight'] = np.round(
                                            np.where(df_merged.delta_daily.isnull(), df_merged.peso_prev, 
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

def add_training_days_on_week_col(df):
    """
    Create a column with the number of training days on the week of each training date.
    """
    # Training days on week
    if 'training_days_on_week' not in df.columns:
        df['year_week'] = df['fecha'].dt.strftime('%G-W%V')
        training_days_by_week = df.groupby('year_week')['fecha'].nunique().reset_index()
        df = df.merge(training_days_by_week, on='year_week', how='left', suffixes=('','_trained')).drop(columns=['year_week'])
        df.rename(columns={'fecha_trained':'training_days_on_week'}, inplace=True)
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
    '1rm',
    'is_maxrm',
    'repreal_range',
    'rir_range',
    'progress_tracker'
    ]
    order_muscles = ['id_set',
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
    '1rm',
    'is_maxrm',
    'repreal_range',
    'rir_range',
    'progress_tracker']

    df = df[order]
    df_muscles = df_muscles[order_muscles]

    return df, df_muscles

def complete_cleaning(input_user_df):
    """
    Complete cleaning process for the input user dataframe.
    """
    conn = connector.get_db_connection()

    df = basic_cleanings(input_user_df)
    df = add_id_set_col(df, conn=conn)
    df = range_col_cleaning(df)
    df = repmin_cleaning(df)
    df = add_analytic_cols(df)
    df = add_real_weight_col(df=df)
    df = add_training_days_on_week_col(df)
    df = add_1rm_columns(df)
    df = add_category_cols(df)

    progression_exercises = {
        'Pull-ups': 'Compound', # Tirón vertical
        'Romanian deadlift': 'Compound', # Bisagra de cadera
        'Parallel bar dips': 'Compound', # Empuje Horizontal
        'Smith machine squat': 'Compound', # Sentadilla
        'Preacher curl machine': 'Isolate',
        'Dumbbell lateral raise': 'Isolate',
        'Incline machine press': 'Isolate',
        'Machine row': 'Isolate',
        'Calf raise on machine': 'Isolate'
    }

    df = define_progression_exercises(df, progression_exercises)

    muscle_roles = etl.create_exercise_dimension_table(conn=conn)

    df_by_muscle = merge_muscleroles_and_inputdf(df, muscle_roles)
    df_by_muscle = add_muscle_analytic_cols(df_by_muscle)
    df_by_muscle = add_effective_set_by_muscle_col(df_by_muscle)

    df, df_by_muscle = reorder_cols(df, df_by_muscle)

    return df, df_by_muscle

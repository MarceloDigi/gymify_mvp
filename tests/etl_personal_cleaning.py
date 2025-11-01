import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
import sys
import warnings
import os
from pathlib import Path

warnings.filterwarnings("ignore")
# Sube a la raíz del proyecto (un nivel arriba de tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database.db_connector as connector
import services.transform_input_to_dwh as etl_input
import services.etl_oltp_to_olap as etl
import services.dump_data as dump
import database.gsheet_connnector as gsheet_conn
import utils.data_loader as loader

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

def clean_my_personal_gsheet(df, workouts_sql):
    # Clean my gsheet
    if any(col in df.columns for col in ['comment', 'workload', 'I/O']):
        df.drop(columns=['comment','workload','I/O'], inplace=True)
    df.replace('', np.nan, inplace=True)
    df.drop(df[df.notnull().sum(1) == 0].index, inplace=True)

    df = convert_date_columns(df, date_columns=['fecha'])

    df['routine_name'] = df.routine_name.replace('#N/A', np.nan)
    mode_by_date = df.groupby('fecha')['routine_name'].apply(lambda x: x.mode().iloc[0]).reset_index()
    df = df.merge(mode_by_date, on='fecha', how='left', suffixes=('_old', '')).drop('routine_name_old', axis=1)

    df.drop('id', axis=1, inplace=True)
    df.rename(columns={'weight':'peso', 'repreal':'reps','routine_name':'routine'}, inplace=True)

    return df

# ========= Data Loading ========= #
client = gsheet_conn.get_gsheet_credentials()
fitness_personal_key = os.getenv("GOOGLE_SHEET_KEY_FITNESS_PERSONAL")
food_tracking = os.getenv("GOOGLE_SHEET_KEY_FOOD")
spreadsheet_fitness_personal = client.open_by_key(fitness_personal_key)
spreadsheet_food_tracking = client.open_by_key(food_tracking)

# ----- Track Record
sheet = spreadsheet_fitness_personal.worksheet('TrackRecord')
records = sheet.get_all_records()
df = pd.DataFrame.from_records(records)

# ----- Routine Template
templates = spreadsheet_fitness_personal.worksheet('Routines')
templates_data = templates.get_all_records()
df_templates = pd.DataFrame.from_records(templates_data)

# ---- Status
status = spreadsheet_fitness_personal.worksheet('OtherInfoTrackRecord')
data = status.get('A1:E')
header = data[0]
status_records = [dict(zip(header, row)) for row in data[1:]]
df_status = pd.DataFrame.from_records(status_records)

# ---- Target
target = spreadsheet_fitness_personal.worksheet('TargetSets')
target_data = target.get_all_records()
df_target = pd.DataFrame.from_records(target_data)

# ---- Metrics
metrics = spreadsheet_food_tracking.worksheet('Metrics')
metrics_data = metrics.get_all_records()
df_metrics = pd.DataFrame.from_records(metrics_data)

# ========= SQL Data Loading ========= #
workouts_by_muscle = connector.query_to_dataframe("SELECT * FROM workouts_by_muscle")
workouts = connector.query_to_dataframe("SELECT * FROM workouts")
muscle_roles = view_exercise_dimension_table = etl.create_exercise_dimension_table()

# ========= Data Cleaning Functions ========= #
print('Último entreno: ', max_date_sql := workouts['fecha'].max())

df = convert_date_columns(df, ['fecha'], multiple_formats=True)
df = df.loc[df.fecha > max_date_sql]
df = clean_my_personal_gsheet(df, workouts)
df['id_user'] = 1  # Mi user_id es 1

# Apply etl_input transformations
df, df_by_muscle = etl_input.complete_cleaning(df, muscle_roles)

# ========= Dump DataFrames into OLTP ========= #
dump.dump_into_sql(df, table_name='workouts', oltp_db=True)
dump.dump_into_sql(df_by_muscle, table_name='workouts_by_muscle', oltp_db=True)
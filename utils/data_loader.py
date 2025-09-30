import pandas as pd
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pathlib import Path
import streamlit as st

# Add parent directory to path so we can import database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_connector import query_to_dataframe

DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "tu_password")
DB_HOST = os.getenv("MYSQLHOST", "interchange.proxy.rlwy.net")
DB_PORT = os.getenv("MYSQLPORT", "44580")
DB_NAME = os.getenv("MYSQLDATABASE", "railway")

@st.cache_data
def load_dim_data():
    engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    sql_exercises = pd.read_sql("SELECT * FROM exercises", con=engine)
    sql_pattern = pd.read_sql("SELECT * FROM movement_pattern", con=engine)
    sql_roles = pd.read_sql("SELECT * FROM rol_names", con=engine)
    sql_pattern_muscle_rol = pd.read_sql("SELECT * FROM pattern_muscle_rol", con=engine)
    sql_equipments = pd.read_sql("SELECT * FROM equipments", con=engine)
    sql_muscles = pd.read_sql("SELECT * FROM muscles", con=engine)
    sql_exercise_muscle_rol = pd.read_sql("SELECT * FROM exercise_muscle_roles", con=engine)

    return {
        "exercises": sql_exercises,
        "patterns": sql_pattern,
        "roles": sql_roles,
        "pattern_muscle_rol": sql_pattern_muscle_rol,
        "equipments": sql_equipments,
        "muscles": sql_muscles,
        "exercise_muscle_roles": sql_exercise_muscle_rol,
    }    

def load_data(aggregated_path=None, muscles_path=None, user_id=None):
    """
    Load workout data and muscle breakdown data from SQLite database

    Parameters:
        aggregated_path: Legacy parameter, not used (kept for compatibility)
        muscles_path: Legacy parameter, not used (kept for compatibility)
        user_id: User ID to filter data by (if None, returns all data)

    Returns:
        df: DataFrame with workout data
        df_muscles: DataFrame with muscle breakdown data
    """
    # Build user filter condition
    user_filter = f"WHERE user_id = {user_id}" if user_id else ""

    # Load workout data
    df = query_to_dataframe(f"""
        SELECT * FROM workouts
        {user_filter}
        ORDER BY fecha DESC
    """)

    # Load muscle breakdown data
    df_muscles = query_to_dataframe(f"""
        SELECT * FROM workouts_by_muscle
        {user_filter}
        ORDER BY fecha DESC
    """)

    # Convert date columns to datetime
    for col in ['fecha', 'fecha_prev', 'fecha_next']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
        if col in df_muscles.columns:
            df_muscles[col] = pd.to_datetime(df_muscles[col])

    return df, df_muscles

def load_and_prepare_data(path=None, datecols=None, snake_case=False, table_name=None, user_id=None):
    """
    Load data from SQLite database or CSV file

    Parameters:
        path: Path to CSV file (legacy, can be None if using table_name)
        datecols: List of date columns to parse (for CSV files)
        snake_case: Whether to convert column names to snake_case
        table_name: Name of the table to load from database
        user_id: User ID to filter data by (if None, returns all data)

    Returns:
        df: DataFrame with data
    """
    if table_name:
        # Build user filter condition
        user_filter = f"WHERE user_id = {user_id}" if user_id else ""

        # Load data from database
        df = query_to_dataframe(f"""
            SELECT * FROM {table_name}
            {user_filter}
        """)

        # Convert date columns to datetime if specified
        if datecols:
            for col in datecols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
    else:
        # Legacy CSV loading
        if datecols is not None:
            df = pd.read_csv(path, parse_dates=datecols)
        else:
            df = pd.read_csv(path)

    # Convert column names to snake_case if requested
    if snake_case:
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")

    return df

def get_date_filters(df, sidebar_label="Rango de fechas"):
    """Get min and max dates from a DataFrame for date filters"""
    min_date = df["fecha"].min()
    max_date = df["fecha"].max()
    return min_date, max_date

def filter_by_date(df, start_date, end_date):
    """Filter a DataFrame by date range"""
    return df[(df["fecha"] >= pd.to_datetime(start_date)) & (df["fecha"] <= pd.to_datetime(end_date))]
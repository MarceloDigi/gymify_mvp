import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Cargar .env con ruta absoluta desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ///////////////////// MySQL Database Connection ////////////////////

DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = os.getenv("MYSQLPORT")
DB_NAME = os.getenv("MYSQLDATABASE")
DWH_DBNAME = os.getenv("DWHDATABASE")

def get_engine(oltp_db: bool = True):
    if oltp_db:
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DWH_DBNAME}"
    if not connection_string:
        raise ValueError("❌ MY_SQL_CONNECTION no está definido en el entorno.")
    print("🔍 Conexión detectada")
    engine = create_engine(connection_string)

    return engine

def get_db_connection():
    engine = get_engine()
    return engine.connect()

def query_to_dataframe(query, params=()) -> pd.DataFrame:
    """Execute a query and return results as a pandas DataFrame"""
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def insert_data(table, data_dict):
    """Insert a row of data into a table"""
    conn = get_db_connection()
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join([f":{key}" for key in data_dict.keys()])
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    result = conn.execute(text(query), data_dict)
    conn.commit()
    last_id = result.lastrowid
    conn.close()
    return last_id

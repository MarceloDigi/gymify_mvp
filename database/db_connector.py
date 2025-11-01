import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import logging
import streamlit as st
from datetime import datetime

# Cargar .env con ruta absoluta desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ///////////////////// MySQL Database Connection ////////////////////
# Configura un logger a archivo con timestamp
log_dir = Path.cwd() / "logs"
logfile = log_dir / f"db_connector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = os.getenv("MYSQLPORT")
DB_NAME = os.getenv("MYSQLDATABASE")
DWH_DBNAME = os.getenv("DWHDATABASE")

@st.cache_resource(show_spinner=False)
def get_engine(oltp_db: bool = True):
    if oltp_db:
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DWH_DBNAME}"
    if not connection_string:
        raise ValueError("❌ MY_SQL_CONNECTION no está definido en el entorno.")

    return create_engine(connection_string, pool_pre_ping=True, pool_recycle=1800)  # ← añade esto

def get_db_connection(oltp_db: bool = True):
    """
        Parameters
    ----------
    oltp_db : bool, optional
        If True, connects to OLTP DB; otherwise connects to DWH (OLAP).
    """
    try:
        engine = get_engine(oltp_db=oltp_db)
        conn = engine.connect()
        logging.debug(f"✅ Database connection (OLTP={oltp_db}) established successfully.")
        return conn

    except Exception as e:
        logging.exception("❌ Error while connecting to the database.")
        return None

@st.cache_data(ttl=600, show_spinner=False)
def query_to_dataframe(query, params=(), oltp_db: bool = True) -> pd.DataFrame:
    """Execute a query and return results as a pandas DataFrame"""
    conn = get_db_connection(oltp_db = oltp_db)
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

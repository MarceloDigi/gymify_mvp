# database/db_connector.py
from pathlib import Path
from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st
import logging, os
from datetime import datetime
from urllib.parse import quote_plus

# ---- Logging: menos ruido y sin escribir archivo en Cloud ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---- Lectura de credenciales: 1) st.secrets 2) os.getenv ----
def _get(key: str, default=None):
    try:
        if key in st.secrets:
            return st.secrets.get(key, default)
    except Exception:
        pass
    return os.getenv(key, default)

def _mysql_url(db_name_key: str) -> str:
    """
    Construye la URL de conexión MySQL de forma segura.
    Usa cualquiera de estos esquemas:
      - db_url (completa)
      - MYSQLUSER / MYSQLPASSWORD / MYSQLHOST / MYSQLPORT / <db_name_key>
    """
    # 1) URL completa si está
    full = _get("db_url")
    if full:
        return full

    # 2) Por partes (soporta tus nombres actuales del .env)
    user = _get("db_user") or _get("MYSQLUSER")
    pwd  = _get("db_password") or _get("MYSQLPASSWORD")
    host = _get("db_host") or _get("MYSQLHOST")
    port = _get("db_port") or _get("MYSQLPORT")
    name = _get("db_name") or _get(db_name_key)  # p.ej. MYSQLDATABASE / DWHDATABASE

    engine = _get("db_engine", "mysql+pymysql")

    # Validaciones mínimas
    if not all([user, pwd, host, name]):
        logging.error(f"DBG user={user} host={host} name={name} port={port}")
        logging.error(f"DBG keys in secrets: {list(getattr(st, 'secrets', {}).keys())}")
        raise RuntimeError("Config DB incompleta: define 'db_url' o las claves por partes (user/password/host/name).")

    # Puerto opcional (evita ':None')
    port_part = f":{port}" if (port and str(port).strip().lower() != "none") else ""

    # Escapar credenciales por si hay símbolos
    return f"{engine}://{quote_plus(user)}:{quote_plus(pwd)}@{host}{port_part}/{name}"

@st.cache_resource(show_spinner=False)
def get_engine(oltp_db: bool = True):
    url = _mysql_url("MYSQLDATABASE" if oltp_db else "DWHDATABASE")
    return create_engine(
        url,
        pool_pre_ping=True,   # comprueba conexión antes de usarla
        pool_recycle=120,     # recicla conexiones para evitar cortes del proxy
        pool_size=2,
        max_overflow=0,
        connect_args={
            "connect_timeout": 10,
            "read_timeout": 10,
            "write_timeout": 10,
            # Muchos proxies de Railway requieren TLS en el puerto externo
            "ssl": {"cert_reqs": ssl.CERT_NONE},  # desactiva verificación del cert (útil con proxy)
            "charset": "utf8mb4",
            "autocommit": True,
        },
    )

def get_db_connection(oltp_db: bool = True):
    try:
        eng = get_engine(oltp_db=oltp_db)
        conn = eng.connect()
        logging.info(f"✅ Conectado a DB (OLTP={oltp_db})")
        return conn
    except Exception as e:
        logging.exception("❌ Error while connecting to the database.")
        return None

@st.cache_data(ttl=600, show_spinner=False)
def query_to_dataframe(query, params=(), oltp_db: bool = True) -> pd.DataFrame:
    conn = get_db_connection(oltp_db=oltp_db)
    if conn is None:
        return pd.DataFrame()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def insert_data(table, data_dict):
    conn = get_db_connection()
    if conn is None:
        raise RuntimeError("No DB connection.")
    cols = ', '.join(data_dict.keys())
    placeholders = ', '.join([f":{k}" for k in data_dict.keys()])
    q = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    result = conn.execute(text(q), data_dict)
    conn.commit()
    last_id = result.lastrowid
    conn.close()
    return last_id

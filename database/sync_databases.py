import os
from pathlib import Path
from dotenv import load_dotenv

backups_path = Path(__file__).resolve().parent.parent.parent / "backups"

# Cargar .env con ruta absoluta desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = os.getenv("MYSQLPORT")
DB_NAME = os.getenv("MYSQLDATABASE")
DWH_DBNAME = os.getenv("DWHDATABASE")

LOCAL_USER = os.getenv("LOCAL_USER")
LOCAL_PASSWORD = os.getenv("LOCAL_PASSWORD")
LOCAL_DBNAME = os.getenv("LOCAL_DBNAME")
LOCAL_DWHDATABASE = os.getenv("LOCAL_DWHDATABASE")

os.system(
    fr'mysqldump -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DB_NAME} > {backups_path}/railway_oltp_backup.sql'
)
os.system(
    fr'mysql -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DBNAME} < {backups_path}/railway_oltp_backup.sql'
)
os.system(
    fr'mysqldump -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DWH_DBNAME} > {backups_path}/railway_olap_backup.sql'
)
os.system(
    fr'mysql -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DWHDATABASE} < {backups_path}/railway_olap_backup.sql'
)
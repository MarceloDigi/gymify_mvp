import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# === Configuración de rutas ===
project_root = Path(__file__).resolve().parent.parent
backups_path = project_root / "backups"
backups_path.mkdir(exist_ok=True)

# === Cargar variables desde .env ===
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# === Variables de entorno ===
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

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# === Función auxiliar ===
def run_cmd(command, message):
    print(f"\n➡️ Ejecutando:\n{command}")
    code = os.system(command)
    if code == 0:
        print(f"✅ {message}")
    else:
        print(f"⚠️ Error ({code}) en: {message}")
    return code

# === Menú principal ===
print("\n🔄 Sincronización MySQL - Local ↔ Railway")
print("----------------------------------------")
print("1️⃣  Local → Railway  (sube tus bases locales al servidor)")
print("2️⃣  Railway → Local  (trae las bases remotas al entorno local)")

choice = input("\n👉 Elige dirección (1 o 2): ").strip()

if choice == "1":
    direction = "to_railway"
elif choice == "2":
    direction = "to_local"
else:
    print("❌ Opción inválida. Debes introducir 1 o 2.")
    exit(1)

# === Elegir tipo de base ===
print("\n📊 Qué deseas sincronizar:")
print("1️⃣  Solo OLTP")
print("2️⃣  Solo OLAP")
print("3️⃣  Ambas")

db_choice = input("\n👉 Elige opción (1, 2 o 3): ").strip()

if db_choice == "1":
    sync_oltp, sync_olap = True, False
elif db_choice == "2":
    sync_oltp, sync_olap = False, True
elif db_choice == "3":
    sync_oltp, sync_olap = True, True
else:
    print("❌ Opción inválida. Debes introducir 1, 2 o 3.")
    exit(1)

# === Confirmación de seguridad ===
direction_text = "LOCAL → RAILWAY" if direction == "to_railway" else "RAILWAY → LOCAL"
bases_text = []
if sync_oltp: bases_text.append("OLTP")
if sync_olap: bases_text.append("OLAP")
bases_str = " y ".join(bases_text)

print(f"\n⚙️ Has elegido sincronizar {bases_str} ({direction_text})")
confirm = input("⚠️ Esto puede sobrescribir datos. ¿Seguro que deseas continuar? (sí/no): ").lower().strip()

if confirm not in ["si", "sí", "yes", "y"]:
    print("🛑 Operación cancelada por el usuario.")
    exit(0)

# === EJECUCIÓN ===
if direction == "to_railway":
    print(f"\n⬆️ Iniciando sincronización: LOCAL → RAILWAY ({bases_str})")

    if sync_oltp:
        run_cmd(
            fr'mysqldump -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DBNAME} > {backups_path}/local_oltp_{timestamp}.sql',
            "Backup local OLTP generado."
        )
        run_cmd(
            fr'mysql -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DB_NAME} < {backups_path}/local_oltp_{timestamp}.sql',
            "OLTP importado en Railway."
        )

    if sync_olap:
        run_cmd(
            fr'mysqldump -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DWHDATABASE} > {backups_path}/local_olap_{timestamp}.sql',
            "Backup local OLAP generado."
        )
        run_cmd(
            fr'mysql -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DWH_DBNAME} < {backups_path}/local_olap_{timestamp}.sql',
            "OLAP importado en Railway."
        )

elif direction == "to_local":
    print(f"\n⬇️ Iniciando sincronización: RAILWAY → LOCAL ({bases_str})")

    if sync_oltp:
        run_cmd(
            fr'mysqldump -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DB_NAME} > {backups_path}/railway_oltp_{timestamp}.sql',
            "Backup remoto OLTP generado."
        )
        run_cmd(
            fr'mysql -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DBNAME} < {backups_path}/railway_oltp_{timestamp}.sql',
            "OLTP importado en Local."
        )

    if sync_olap:
        run_cmd(
            fr'mysqldump -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} -P {DB_PORT} {DWH_DBNAME} > {backups_path}/railway_olap_{timestamp}.sql',
            "Backup remoto OLAP generado."
        )
        run_cmd(
            fr'mysql -u {LOCAL_USER} -p{LOCAL_PASSWORD} {LOCAL_DWHDATABASE} < {backups_path}/railway_olap_{timestamp}.sql',
            "OLAP importado en Local."
        )

print("\n🎉 Sincronización completada con éxito.")

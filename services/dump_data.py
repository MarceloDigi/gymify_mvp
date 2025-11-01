import database.db_connector as connector
import pandas as pd

def dump_into_sql(df: pd.DataFrame, table_name: str, oltp_db: bool = True) -> None:
    try:
        engine = connector.get_engine(oltp_db=oltp_db)
        with engine.begin() as connection:
            df.to_sql(table_name, con=connection, if_exists='append', index=False)
            print(f'✅ Añadido exitosamente a la tabla: {table_name} - {len(df)} filas')
    except Exception as e:
        print(f'❌ Error al intentar añadir a la tabla {table_name}: {e}')
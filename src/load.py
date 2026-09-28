import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from src.extract import extract_all
from src.validate_transform import run_validation

def get_engine():
    conn_str = (
        f"DRIVER={{{config.ODBC_DRIVER}}};"
        f"SERVER={config.SQL_SERVER};"
        f"DATABASE={config.SQL_DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    return create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str))


def load_tables(engine, tables, source):
    for name, df in tables.items():
        df = df.copy()
        df["_LoadedAt"] = datetime.now()
        df["_SourceSystem"] = source
        df.to_sql(name, engine, if_exists="replace", index=False)
        print(f"[load] {name}: {len(df)} rows")



if __name__ == "__main__":
    engine = get_engine()
    data = extract_all()
    governed = run_validation(data)
    load_tables(engine, data, "LegacyERP+ProcurementAPI")
    load_tables(engine, governed, "DataHub")
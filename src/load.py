
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine


sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from src.extract import extract_all
from src.logging_setup import setup_logging
from src.validate_transform import run_validation

logger = logging.getLogger(__name__)

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
        if df.empty:
            logger.warning("%s is empty, loading 0 rows", name)
        df = df.copy()
        df["_LoadedAt"] = datetime.now()
        df["_SourceSystem"] = source
        df.to_sql(name, engine, if_exists="replace", index=False)
        logger.info("%s: %d rows loaded", name, len(df))


def run_sql_script(engine, path):
    """Run a .sql file, splitting it into batches on GO lines like SSMS does."""
    sql = path.read_text(encoding="utf-8-sig")
    batches = re.split(r"^\s*GO\s*$", sql, flags=re.IGNORECASE | re.MULTILINE)
    batches = [b.strip() for b in batches if b.strip()]
    batches = [b for b in batches if not re.fullmatch(r"USE\s+\w+;?", b, flags=re.IGNORECASE)]

    with engine.begin() as conn:
        for batch in batches:
            conn.exec_driver_sql(batch)
    logger.info("%s: %d batch(es) executed", path.name, len(batches))


    



if __name__ == "__main__":
    setup_logging()
    logger.info("Pipeline started")
    engine = get_engine()
    data = extract_all()
    governed = run_validation(data)
    load_tables(engine, data, "LegacyERP+ProcurementAPI")
    load_tables(engine, governed, "DataHub")
    logger.info("Pipeline finished")
"""Orchestrates the P2P Data Hub pipeline end to end."""

import logging
import sys
import time

import requests

import config
from src.extract import extract_all
from src.load import get_engine, load_tables, run_sql_script
from src.logging_setup import setup_logging
from src.validate_transform import run_validation

logger = logging.getLogger("pipeline")


def check_sources(engine):
    """Fail fast if the API or SQL Server are not reachable."""
    resp = requests.get(f"{config.API_BASE_URL}/PurchaseOrderLines_page1.json"
    , timeout=10)
    resp.raise_for_status()
    logger.info("API reachable at %s", config.API_BASE_URL)

    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    logger.info("SQL Server reachable: %s / %s", config.SQL_SERVER
    , config.SQL_DATABASE)


def run_step(name, func, *args):
    """Run one pipeline step, logging its start, end and duration."""
    logger.info("STEP START | %s", name)
    start = time.perf_counter()
    result = func(*args)
    logger.info("STEP OK    | %s (%.1fs)", name, time.perf_counter() - start)
    return result


def main():
    setup_logging()
    logger.info("=" * 60)
    logger.info("Pipeline started")
    start = time.perf_counter()

    try:
        engine = get_engine()
        run_step("Pre-checks", check_sources, engine)
        data = run_step("Extract", extract_all)
        governed = run_step("Validate & transform", run_validation, data)
        run_step("Load staging", load_tables, engine, data, "LegacyERP+ProcurementAPI")
        run_step("Load governed", load_tables, engine, governed, "DataHub")
        run_step("Build dimensions", run_sql_script, engine, config.SQL_DIR / "01_dimensions.sql")
        run_step("Build facts", run_sql_script, engine, config.SQL_DIR / "02_facts.sql")
    except Exception:
        logger.exception("Pipeline FAILED after %.1fs", time.perf_counter() - start)
        return 1

    logger.info("Pipeline SUCCEEDED in %.1fs", time.perf_counter() - start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
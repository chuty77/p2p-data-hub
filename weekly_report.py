"""Weekly report of invoices on hold for the Accounts Payable team."""

import logging
import sys
import time
from datetime import date

import pandas as pd

import config
from src.load import get_engine
from src.logging_setup import setup_logging

logger = logging.getLogger("weekly_report")

QUERY = """
SELECT
    m.InvoiceNumber,
    m.InvoiceDate,
    m.VendorAccount,
    COALESCE(v.VendorName, '** Vendor not in master **') AS VendorName,
    m.POLineKey,
    m.ItemNumber,
    m.OrderedQty,
    m.ReceivedQty,
    m.InvoiceQty,
    m.POUnitPrice,
    m.InvoiceUnitPrice,
    m.PriceVariancePct,
    m.InvoiceAmount,
    m.MatchStatus
FROM fact_three_way_match m
LEFT JOIN dim_vendor v ON v.VendorAccount = m.VendorAccount
"""


NUMERIC_COLS = ["OrderedQty", "ReceivedQty", "InvoiceQty", "POUnitPrice",
                "InvoiceUnitPrice", "PriceVariancePct", "InvoiceAmount"]


def extract_data(engine):
    df = pd.read_sql(QUERY, engine)
    if df.empty:
        raise ValueError("fact_three_way_match is empty: report not generated")
    df[NUMERIC_COLS] = df[NUMERIC_COLS].astype(float)
    logger.info("Extracted %d invoice lines", len(df))
    return df


def build_sheets(df):
    on_hold = df[df["MatchStatus"] != "Matched"]
    total_lines = len(df)
    hold_lines = len(on_hold)

    kpis = pd.DataFrame({
        "Metric": ["Report date", "Total invoice lines", "Lines on hold",
                   "Match rate", "Amount on hold"],
        "Value": [date.today().isoformat(), total_lines, hold_lines,
                  f"{(total_lines - hold_lines) / total_lines:.1%}",
                  f"${on_hold['InvoiceAmount'].sum():,.2f}"],
    })

    by_exception = (
        on_hold.groupby("MatchStatus")
        .agg(InvoiceLines=("InvoiceNumber", "size"),
             AmountOnHold=("InvoiceAmount", "sum"))
        .sort_values("AmountOnHold", ascending=False)
        .reset_index()
        .rename(columns={"MatchStatus": "ExceptionType"})
    )

    by_vendor = (
        on_hold.groupby(["VendorAccount", "VendorName"])
        .agg(InvoiceLines=("InvoiceNumber", "size"),
             AmountOnHold=("InvoiceAmount", "sum"),
             ExceptionTypes=("MatchStatus", lambda s: ", ".join(sorted(s.unique()))))
        .sort_values("AmountOnHold", ascending=False)
        .reset_index()
    )

    detail = on_hold.sort_values("InvoiceAmount", ascending=False)

    logger.info("On hold: %d of %d lines, $%.2f",
                hold_lines, total_lines, on_hold["InvoiceAmount"].sum())
    return kpis, by_exception, by_vendor, detail


def write_report(kpis, by_exception, by_vendor, detail):
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORTS_DIR / f"AP_on_hold_report_{date.today():%Y%m%d}.xlsx"

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        kpis.to_excel(writer, sheet_name="Summary", index=False)
        by_exception.to_excel(writer, sheet_name="Summary", index=False,
                              startrow=len(kpis) + 2)
        by_vendor.to_excel(writer, sheet_name="By Vendor", index=False)
        detail.to_excel(writer, sheet_name="Detail", index=False)

    logger.info("Report saved: %s", path)
    return path


def main():
    setup_logging("weekly_report")
    logger.info("=" * 60)
    logger.info("Weekly report started")
    start = time.perf_counter()

    try:
        engine = get_engine()
        df = extract_data(engine)
        sheets = build_sheets(df)
        write_report(*sheets)
    except Exception:
        logger.exception("Weekly report FAILED after %.1fs", time.perf_counter() - start)
        return 1

    logger.info("Weekly report SUCCEEDED in %.1fs", time.perf_counter() - start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
import logging
import sys 
from pathlib import Path

import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

logger = logging.getLogger(__name__)

def fetch_odata(entity): 
    url = f"{config.API_BASE_URL}/{entity}_page1.json" 
    rows = [] 
    pages = 0 
    while url:
        resp= requests.get(url,timeout=30) 
        resp.raise_for_status() 
        payload = resp.json() 
        rows.extend(payload["value"]) #
        url = payload.get("@odata.nextLink")
        pages += 1
    logger.info("API %s: %d rows in %d page(s)", entity, len(rows), pages)
    return pd.DataFrame(rows) 


def read_legacy_csv(name):
    path = config.SOURCE_DIR / f"{name}.csv"
    df= pd.read_csv(path, dtype=str, keep_default_na=False)
    logger.info("CSV %s: %d rows", name, len(df))
    return df

def extract_all():
    return{
        "stg_vendor": read_legacy_csv("legacy_vendors"),
        "stg_item": read_legacy_csv("legacy_items"),
        "stg_po_line": fetch_odata("PurchaseOrderLines"),
        "stg_receipt": fetch_odata("ProductReceiptLines"),
        "stg_invoice": fetch_odata("VendorInvoiceLines")

}



if __name__ == "__main__":
    from src.logging_setup import setup_logging
    setup_logging()
    extract_all()
        
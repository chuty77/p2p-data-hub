import pandas as pd
import requests 
import sys 

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config


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
    print(f"[extract] {entity}: {len(rows)} rows in {pages} page(s)")
    return pd.DataFrame(rows) 


def read_legacy_csv(name):
    path = config.SOURCE_DIR / f"{name}.csv"
    df= pd.read_csv(path, dtype=str, keep_default_na=False)
    print(f"[extract] CSV {name}: {len(df)} rows")
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
    data= extract_all()
    for name, df in data.items():
        print(name,len(df))
        
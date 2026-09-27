"""
Step 0 - Simulate the source systems (only needed for the demo).

System A: Legacy ERP -> CSV extracts (vendors, items)
System B: Procurement platform -> REST/OData API (purchase order lines, receipts, invoices)

Data quality problems are injected ON PURPOSE so the pipeline has something real to catch.
All company names are fictional.
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

random.seed(42)

VENDOR_NAMES = [
    "Pacific Composites S.A.", "AeroTech Fasteners LLC", "Central Avionics Supply",
    "Heredia Precision Machining", "SkyWire Harness Corp", "Lumen Battery Systems",
    "Orbital Test Labs", "Cartago Metals S.A.", "BlueRidge Electronics", "Vector Sensors Inc",
    "NorthStar Logistics", "Andes Titanium Ltd", "Quantum PCB Works", "Alpine Coatings GmbH",
    "Golfo Industrial Services", "Redwood Software Tools", "Ironclad Tooling Co",
    "Summit Calibration Services", "Coastal Freight CR", "Nimbus Cloud Services",
    "Precision Bearings USA", "Tropic Packaging S.A.", "Helix Motors Inc", "Silver Peak Alloys",
    "Clearview Optics", "Atlas Hydraulics", "Pura Vida Office Supply", "Falcon Adhesives",
    "Meridian Thermal Solutions", "Keystone Safety Equipment", "Crescent Cable Assemblies",
    "Volcan Engineering Consultants", "Evergreen Facility Services", "Zenith Test Equipment",
    "Granite Composites Inc", "Lighthouse IT Services", "Monarch Plastics", "Brightline Relays",
    "Cobalt Power Electronics", "Sierra Fastening Systems",
]
COUNTRY_CUR = {"US": "USD", "CR": "CRC", "DE": "EUR"}


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def build_vendors() -> pd.DataFrame:
    rows = []
    for i, name in enumerate(VENDOR_NAMES, start=1):
        country = "CR" if ("S.A." in name or "CR" in name) else ("DE" if "GmbH" in name else "US")
        rows.append({
            "VendorCode": f"LV{i:04d}",
            "VendorName": name,
            "TaxID": f"{country}-{random.randint(10_000_000, 99_999_999)}",
            "Country": country,
            "Currency": COUNTRY_CUR[country],
            "PaymentTerms": random.choice(["Net30", "Net30", "Net45", "Net60", "Net15"]),
            "Email": f"ap@{name.split()[0].lower().replace('.', '')}.com",
            "Status": "Active",
            "CreatedDate": rand_date(date(2015, 1, 1), date(2024, 12, 31)).isoformat(),
        })
    df = pd.DataFrame(rows)

    # --- Inject realistic master data problems ---
    df.loc[3, "TaxID"] = None                         # missing tax id
    df.loc[17, "TaxID"] = ""                          # blank tax id
    df.loc[5, "PaymentTerms"] = "N30"                 # non-standard terms (fixable)
    df.loc[9, "PaymentTerms"] = "NET 30"
    df.loc[12, "PaymentTerms"] = "2% 10 Net 30"       # not fixable -> exception
    df.loc[14, "Currency"] = "COL"                    # invalid currency
    df.loc[20, "Email"] = "accounts.precisionbearings" # invalid email
    df.loc[25, "Email"] = None
    df.loc[30, "Status"] = "Blocked"                  # blocked vendor that still gets POs

    # Duplicate vendors: same supplier created twice in the legacy system
    dup1 = df.loc[1].copy(); dup1.update({"VendorCode": "LV0041", "VendorName": "AEROTECH FASTENERS, LLC.",
                                          "CreatedDate": "2025-03-10"})
    dup2 = df.loc[8].copy(); dup2.update({"VendorCode": "LV0042", "VendorName": "Blue Ridge Electronics",
                                          "CreatedDate": "2025-06-21"})
    # Same name, different TaxID -> possible duplicate that needs human review
    dup3 = df.loc[6].copy(); dup3.update({"VendorCode": "LV0043", "TaxID": "US-11112222",
                                          "CreatedDate": "2025-08-02"})
    return pd.concat([df, pd.DataFrame([dup1, dup2, dup3])], ignore_index=True)


def build_items() -> pd.DataFrame:
    groups = {
        "AVIONICS": ["Flight Control Board", "Air Data Sensor", "Display Module", "Wiring Harness",
                     "Power Distribution Unit", "IMU Sensor"],
        "RAWMAT": ["Carbon Fiber Prepreg (m2)", "Titanium Sheet", "Aluminum Bar 7075", "Epoxy Resin (kg)",
                   "Copper Wire (m)"],
        "HARDWARE": ["Titanium Fastener Kit", "Precision Bearing", "Hydraulic Fitting", "Rivet Pack",
                     "Connector D38999"],
        "TOOLING": ["Torque Wrench Calibrated", "Composite Mold", "Test Fixture"],
        "SERVICES": ["Calibration Service", "Environmental Testing", "Freight Service", "IT Support Hours",
                     "Engineering Consulting Hours"],
    }
    rows, n = [], 1
    for grp, names in groups.items():
        for nm in names:
            base = {"AVIONICS": 2500, "RAWMAT": 180, "HARDWARE": 45, "TOOLING": 1800, "SERVICES": 120}[grp]
            rows.append({"ItemNumber": f"ITM-{n:04d}", "Description": nm, "ItemGroup": grp,
                         "UoM": "HR" if "Hours" in nm else "EA",
                         "StandardCost": round(base * random.uniform(0.6, 1.6), 2)})
            n += 1
    return pd.DataFrame(rows)


def build_transactions(vendors: pd.DataFrame, items: pd.DataFrame):
    po_lines, receipts, invoices = [], [], []
    vendor_codes = vendors["VendorCode"].tolist()
    inv_seq = 1
    for p in range(1, 151):
        po = f"PO-{25000 + p}"
        vendor = random.choice(vendor_codes)
        if p in (7, 88):
            vendor = "LV9999"                       # vendor that does not exist in master
        order_date = rand_date(date(2025, 1, 1), date(2026, 6, 30))
        for line in range(1, random.randint(1, 4) + 1):
            item = items.sample(1, random_state=random.randint(0, 10_000)).iloc[0]
            item_no = "ITM-9999" if (p == 40 and line == 1) else item["ItemNumber"]  # unknown item
            qty = random.randint(1, 50) if item["ItemGroup"] != "AVIONICS" else random.randint(1, 8)
            price = round(float(item["StandardCost"]) * random.uniform(0.95, 1.05), 2)
            po_lines.append({"PurchaseOrderNumber": po, "LineNumber": line, "VendorAccount": vendor,
                             "ItemNumber": item_no, "OrderedQuantity": qty, "UnitPrice": price,
                             "OrderDate": order_date.isoformat(), "Site": random.choice(["CR-HER", "US-MAR"])})

            # Receipts (product receipts) - some lines not received yet, some partial
            r = random.random()
            rec_qty = 0 if r < 0.10 else (max(1, qty // 2) if r < 0.20 else qty)
            rec_date = order_date + timedelta(days=random.randint(5, 40))
            if rec_qty > 0:
                receipts.append({"ReceiptNumber": f"PR-{len(receipts) + 1:05d}", "PurchaseOrderNumber": po,
                                 "LineNumber": line, "ReceivedQuantity": rec_qty,
                                 "ReceiptDate": rec_date.isoformat()})

            # Vendor invoices
            if random.random() < 0.88:
                inv_qty, inv_price = (rec_qty if rec_qty > 0 else qty), price
                x = random.random()
                if x < 0.08:
                    inv_price = round(price * random.uniform(1.07, 1.20), 2)   # price variance
                elif x < 0.13 and rec_qty > 0:
                    inv_qty = rec_qty + random.randint(1, 5)                    # billed more than received
                inv_no = f"INV-{inv_seq:05d}"; inv_seq += 1
                inv = {"InvoiceNumber": inv_no, "VendorAccount": vendor, "PurchaseOrderNumber": po,
                       "LineNumber": line, "InvoiceQuantity": inv_qty, "InvoiceUnitPrice": inv_price,
                       "InvoiceDate": (rec_date + timedelta(days=random.randint(1, 15))).isoformat()}
                invoices.append(inv)
                if random.random() < 0.03:                                      # duplicate submission
                    invoices.append(dict(inv))
    return po_lines, receipts, invoices


def write_odata_pages(entity: str, rows: list, page_size: int = 100):
    """Write JSON pages that mimic a D365 OData response with @odata.nextLink pagination."""
    config.MOCK_API_DIR.joinpath("data").mkdir(parents=True, exist_ok=True)
    pages = [rows[i:i + page_size] for i in range(0, len(rows), page_size)] or [[]]
    for n, chunk in enumerate(pages, start=1):
        payload = {"@odata.context": f"{config.API_BASE_URL}/$metadata#{entity}", "value": chunk}
        if n < len(pages):
            payload["@odata.nextLink"] = f"{config.API_BASE_URL}/{entity}_page{n + 1}.json"
        (config.MOCK_API_DIR / "data" / f"{entity}_page{n}.json").write_text(json.dumps(payload, indent=1))


def main():
    config.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    vendors, items = build_vendors(), build_items()
    vendors.to_csv(config.SOURCE_DIR / "legacy_vendors.csv", index=False)
    items.to_csv(config.SOURCE_DIR / "legacy_items.csv", index=False)
    po_lines, receipts, invoices = build_transactions(vendors, items)
    write_odata_pages("PurchaseOrderLines", po_lines)
    write_odata_pages("ProductReceiptLines", receipts)
    write_odata_pages("VendorInvoiceLines", invoices)
    print(f"[generate] vendors={len(vendors)} items={len(items)} po_lines={len(po_lines)} "
          f"receipts={len(receipts)} invoices={len(invoices)}")


if __name__ == "__main__":
    main()

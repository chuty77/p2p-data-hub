import logging
import sys
from datetime import datetime 
from pathlib import Path
import re

import pandas as pd 
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")
SUFFIXES= r"\b(LLC|INC|CORP|CO|LTD|GMBH|S\.?A\.?)\b"

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

logger = logging.getLogger(__name__)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

from src.extract import extract_all 



def add_issue (issue, rule_id, description, severity, entity, record_key, 
                field, bad_value, status="Open", blocking=True):
    issue.append({
        "RuleID": rule_id,
        "RuleDescription": description,
        "Severity": severity,
        "Entity": entity,
        "RecordKey": record_key,
        "FieldName": field,
        "BadValue": bad_value,
        "Status": status,
        "IsBlocking": blocking,
        "DetectedAt": datetime.now().isoformat(timespec="seconds")
    })

def normalize_name(name):
    n = re.sub(SUFFIXES, "", name.upper())
    return re.sub(r"[^A-Z0-9]","",n)






def validate_vendors(vendors,issues):
    for idx, row in vendors.iterrows():
        if row["TaxID"].strip()== "":
            add_issue(issues, "VEN-001", "Missing Tax ID", "High", "Vendor",
                    row["VendorCode"], "TaxID", row["TaxID"])
        if row["Currency"] not in config.VALID_CURRENCIES:
            add_issue(issues, "VEN-002", "Invalid currency code", "High", "Vendor",
                    row["VendorCode"], "Currency", row["Currency"])
        email = row["Email"].strip()
        if email == "" or not EMAIL_RE.match(email):
            add_issue(issues, "VEN-003", "Missing or invalid AP email", "Low", "Vendor",
                    row["VendorCode"], "Email", row["Email"], blocking=False)
        terms= row["PaymentTerms"].strip()
        if terms not in config.VALID_PAYMENT_TERMS :
            fixed= config.PAYMENT_TERMS_FIX.get(terms.upper())
            if fixed:
                vendors.at[idx, "PaymentTerms"]= fixed
                add_issue(issues, "VEN-004", "Non-standard payment terms", "Low", "Vendor",
                            row["VendorCode"], "PaymentTerms", terms,
                            status=f"Auto-fixed -> {fixed}", blocking=False)
            else:
                add_issue(issues, "VEN-004", "Non-standard payment terms", "Medium", "Vendor",
                        row["VendorCode"], "PaymentTerms", terms)
    return vendors



def dedupe_by_taxid(vendors, issues):  
    vendors= vendors.sort_values("CreatedDate")
    vendors["SurvivorCode"]= vendors["VendorCode"]
    with_tax= vendors[vendors["TaxID"].str.strip() != ""]
    for tax_id, group in with_tax.groupby("TaxID"):
        if len(group) > 1:
            survivor = group.iloc[0]["VendorCode"] 
            for code in group["VendorCode"].iloc[1:]:
                vendors.loc[vendors["VendorCode"]==code, "SurvivorCode"] = survivor
                add_issue(issues, "VEN-005", "Duplicate vendor (same Tax ID)", "High", "Vendor",
                code, "TaxID", tax_id, status=f"Merged into {survivor}", blocking=False)
    return vendors


def flag_name_duplicates(vendors, issues):
    survivors = vendors[vendors["VendorCode"] == vendors["SurvivorCode"]].copy()
    survivors["NormName"] = survivors["VendorName"].map(normalize_name)

    for norm_name, group in survivors.groupby("NormName"):
        if len(group) > 1:
            group = group.sort_values("CreatedDate")
            first = group.iloc[0]
            for _, row in group.iloc[1:].iterrows():
                add_issue(issues, "VEN-006", "Possible duplicate (same name, different Tax ID)",
                    "Medium", "Vendor", row["VendorCode"], "VendorName",
                    f'{row["VendorName"]} (matches {first["VendorCode"]})')



def build_golden(vendors):
    golden= vendors[vendors["VendorCode"]== vendors["SurvivorCode"]]
    golden= golden.sort_values("VendorCode").reset_index(drop=True)
    golden["VendorAccount"] = [f"VEND-{i:05d}" for i in range(1, len(golden) + 1)]
    return golden


def build_xref(vendors,golden):

    xref= vendors[["VendorCode", "SurvivorCode"]].merge(golden[["VendorCode","VendorAccount"]],
        left_on="SurvivorCode", right_on= "VendorCode", 
        suffixes=("","_survivor"))
    xref= xref[["VendorCode","SurvivorCode","VendorAccount"]]
    xref= xref.rename(columns={"VendorCode": "LegacyVendorCode"})
    xref["MatchType"] ="Self"
    xref.loc[xref["LegacyVendorCode"] != xref["SurvivorCode"], "MatchType"]= "Merged by Tax ID"
    return xref


def write_d365_files(golden,issues):
    config.D365_IMPORT_DIR.mkdir(parents=True,exist_ok=True)
    config.EXCEPTIONS_DIR.mkdir(parents=True,exist_ok=True)
    issues_df = pd.DataFrame(issues)
    blocking= issues_df[issues_df["IsBlocking"]==True]
    blocking_codes = set(blocking["RecordKey"])
    golden["MigrationStatus"]= golden["VendorCode"].map(
        lambda code: "Exception" if code in blocking_codes else "Ready")
    ready = golden[golden["MigrationStatus"]== "Ready"]
    review_count = (golden["MigrationStatus"] == "Exception").sum()
    entity = pd.DataFrame({
        "VENDORACCOUNTNUMBER" : ready["VendorAccount"],
    })
    entity.to_csv(config.D365_IMPORT_DIR / "Vendors_V2_import.csv", index=False)
    blocking.to_csv(config.EXCEPTIONS_DIR / "blocking_issues_for_review.csv", index=False)
    logger.info("D365 files: %d vendors ready | %d sent to review", len(ready), review_count)
    return golden


def run_validation(data):
    issues =[]
    vendors = validate_vendors(data["stg_vendor"].copy(),issues)
    vendors = dedupe_by_taxid(vendors, issues)
    flag_name_duplicates(vendors, issues)
    golden = build_golden(vendors)
    xref = build_xref(vendors, golden)
    golden = write_d365_files(golden, issues)
    logger.info("Validation done: %d golden vendors, %d DQ issues", len(golden), len(issues))
    return {
        "vendor_golden": golden,
        "vendor_xref": xref,
        "dq_issues": pd.DataFrame(issues),
    }
    


if __name__ == "__main__":
    # print(normalize_name("AeroTech Fasteners LLC"))
    # print(normalize_name("AEROTECH FASTENERS, LLC."))
    # print(normalize_name("Blue Ridge Electronics"))
    # print(normalize_name("BlueRidge Electronics"))
    # print(normalize_name("Coastal Freight CR"))
    from src.logging_setup import setup_logging
    setup_logging()
    data = extract_all()
    governed = run_validation(data)
    for name, df in governed.items():
        print(name, len(df))

import sys
from datetime import datetime # trae la herramienta para trabajar con fechas y horas.
#  La vas a usar para anotar cuándo se detectó cada problema.
from pathlib import Path
import re

import pandas as pd 
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")
SUFFIXES= r"\b(LLC|INC|CORP|CO|LTD|GMBH|S\.?A\.?)\b"

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
# display.max_columns, None: le dice a pandas "no hay límite de columnas, muéstralas todas".
# display.width, 200: le da más espacio horizontal para imprimir, para que no parta la tabla en pedazos.

from src.extract import extract_all #trae la función que construiste en B4. 
#Así, este archivo puede pedir los datos sin repetir el código de extracción.




# La función para registrar problemas: def add_issue ():
# Qué hace en general: recibe los datos de un problema, los arma como un diccionario y
# los agrega a una lista llamada issues. Cada problema queda como una fila del registro.
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




# Recibe dos cosas: la tabla de proveedores que vas a revisar, 
# y la lista de problemas donde vas a anotar lo que encuentres.
# Por qué una función para todos los proveedores: aquí vas a ir agregando las demás reglas de 
# proveedores (moneda, correo, términos de pago). Todas juntas en un solo lugar.

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
    for tax_id, group in with_tax.groupby("TaxID"):#group: una tabla pequeña con los proveedores que tienen ese Tax ID.
        if len(group) > 1:
            survivor = group.iloc[0]["VendorCode"] #.iloc[0]: toma la primera fila del grupo,
#por posición. El 0 significa "la primera", porque en Python se cuenta desde cero.
# Diferencia entre .iloc y .loc: .iloc busca por posición ("la primera fila"); 
# .loc busca por condición ("la fila donde el código es LV0041").
# Vas a usar las dos en esta función.
            for code in group["VendorCode"].iloc[1:]:
#.iloc[1:]: toma desde la segunda fila en adelante. El 1: significa "desde la posición 1 hasta el final".
                vendors.loc[vendors["VendorCode"]==code, "SurvivorCode"] = survivor
#en la tabla completa, busca la fila del duplicado y cambia su SurvivorCode 
# por el código del survivor. Así, LV0041 queda apuntando a LV0002.
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


if __name__ == "__main__":
    # print(normalize_name("AeroTech Fasteners LLC"))
    # print(normalize_name("AEROTECH FASTENERS, LLC."))
    # print(normalize_name("Blue Ridge Electronics"))
    # print(normalize_name("BlueRidge Electronics"))
    # print(normalize_name("Coastal Freight CR"))
    data = extract_all()
    issues = []
    vendors = validate_vendors(data["stg_vendor"].copy(), issues)
    vendors = dedupe_by_taxid(vendors, issues)
    flag_name_duplicates(vendors, issues)
    print(pd.DataFrame(issues))
    golden = build_golden(vendors)
    xref = build_xref(vendors, golden)
    print(len(vendors), "vendors ->", len(golden), "golden records")
    print(len(xref), "rows in xref")
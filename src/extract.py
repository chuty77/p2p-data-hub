import pandas as pd
import requests # requests trae la librería para hacer peticiones a la API.
import sys  # sys trae una herramienta de Python que permite controlar cómo 
#se comporta Python, entre otras cosas, dónde busca los archivos.
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))#parent[1] sube dos niveles
#str(...): convierte la ruta en texto, porque sys.path espera texto.
import config


def fetch_odata(entity): # entity el parámetro, un valor que le pasas cuando la usas. 
    #Aquí será el nombre de la entidad: "PurchaseOrderLines", "ProductReceiptLines" o "VendorInvoiceLines"
    url = f"{config.API_BASE_URL}/{entity}_page1.json" #Ahora usa {entity} en vez del nombre fijo, para que funcione con cualquier entidad.
    rows = [] #una lista vacía. Aquí vas a ir acumulando los registros de todas las páginas.
    pages = 0 #un contador para saber cuántas páginas leíste.
    while url:
        resp= requests.get(url,timeout=30) # pedir la página
        resp.raise_for_status() #detenerse si hay error
        payload = resp.json() # convertir la respuesta en diccionario
        rows.extend(payload["value"]) #agrega los registros de esta página a la lista rows
        #Por qué extend y no append: append metería la lista completa como un solo elemento;
        # extend agrega cada registro por separado.
        url = payload.get("@odata.nextLink")
        pages += 1

    print(f"[extract] {entity}: {len(rows)} rows in {pages} page(s)")
    return pd.DataFrame(rows) #convierte la lista de registros en una tabla de pandas y la entrega a quien llamó la función.


def read_legacy_csv(name):
    path = config.SOURCE_DIR / f"{name}.csv"
    df= pd.read_csv(path, dtype=str, keep_default_na=False)
    # dtype=str: le dice a pandas que lea todas las columnas como texto.
    # keep_default_na=False: le dice a pandas que no convierta las celdas vacías en NaN.
    # NaN significa "Not a Number" y es la forma en que pandas marca un dato faltante
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
  
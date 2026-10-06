# %% Imports y conexión
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


pd.set_option("display.float_format", "{:,.2f}".format)
pd.set_option("display.max.columns", None)
pd.set_option("display.width", 300)

# 1. Conexión a SQL Server

url = URL.create(
    "mssql+pyodbc",
    host=r"localhost\SQLEXPRESS",
    database="P2PDataHub",
    query={
        "driver":"ODBC Driver 18 for SQL Server",
        "TrustServerCertificate": "yes"
    },   
)
engine= create_engine(url)

# %% Cargar tablas
# 2. Traer las tablas a DataFrames
fact_po = pd.read_sql("SELECT * FROM fact_po_line", engine)
dim_vendor= pd.read_sql("SELECT * FROM dim_vendor", engine)
dim_item = pd.read_sql("SELECT * FROM dim_item", engine)


# %% Exploración
print(fact_po.shape) # (filas, columnas) --> (372, 10)
print(fact_po.head())  #primeras 5 filas 
fact_po.info()  #columnas, tipos y nulos
print(fact_po.isna().sum()) # nulos por columna
print(fact_po.nunique())  # contador valores distintos por columna
print(fact_po.describe().T) # # estadística de columnas numéricas MIN, MAX, AVG, STDEV y percentiles


# %% Ver todas las columnas
print(fact_po.columns.tolist())
print(dim_vendor.columns.tolist())


# %% Selección de columnas

fact_po["POAmount"]  # una columna → Series
fact_po[["LineNumber", "OrderedQty", "POAmount"]] # varias columnas → DataFrame


# %% Máscara booleana, filtrar columnas

mascara= fact_po["POAmount"] > 10000
print(mascara.head())  # True / False por cada fila
print(mascara.sum())  # cuántas filas cumplen (True cuenta como 1)

print(fact_po.loc[mascara])  # solo las filas con True


# %% Varias condiciones
#Los paréntesis son obligatorios alrededor de cada condición.
#loc[filas, columnas] filtra filas y elige columnas al mismo tiempo, como un WHERE y un SELECT juntos

# %% Varias condiciones
fact_po.loc[
    (fact_po["POAmount"] > 10000) & (fact_po["OrderedQty"] >= 20),
    ["LineNumber", "OrderedQty","UnitPrice", "POAmount"]
]

# %% IN, NOT IN, BETWEEN

fact_po.loc[fact_po["LineNumber"].isin([1,2])] # IN (1, 2)
fact_po.loc[~fact_po["LineNumber"].isin([1,2])] # NOT IN (1, 2)
fact_po.loc[fact_po["UnitPrice"].between(100,500)]

# %% Top 5 por monto
fact_po.sort_values("POAmount", ascending=False).head(5)




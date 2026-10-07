"""Central configuration for the P2P Data Hub pipeline."""
import os
from pathlib import Path

SQL_SERVER = os.getenv("P2P_SQL_SERVER", r"localhost\SQLEXPRESS")

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR= BASE_DIR / "data"/ "source"
MOCK_API_DIR= BASE_DIR / "mock_api"
DB_PATH= BASE_DIR / "output"/ "p2p_data_hub.db"
D365_IMPORT_DIR = BASE_DIR / "output" / "d365_import"
EXCEPTIONS_DIR = BASE_DIR / "output" / "exceptions"
POWERBI_DIR = BASE_DIR / "output" / "powerbi"
SQL_DIR = BASE_DIR / "sql"
LOG_DIR = BASE_DIR / "logs"


API_HOST, API_PORT= "localhost", 8000
API_BASE_URL = F"http://{API_HOST}:{API_PORT}/data" 
SQL_SERVER = r"localhost\SQLEXPRESS"
SQL_DATABASE = "P2PDataHub"
ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


# Business rules (owned by Finance, documented in the data management plan)
PRICE_TOLERANCE = 0.05              
VALID_CURRENCIES= {"USD","CRC", "EUR"}
VALID_PAYMENT_TERMS = {"Net15", "Net30", "Net45", "Net60"}
PAYMENT_TERMS_FIX = {                        # standardization map legacy -> D365
    "N30": "Net30", "NET 30": "Net30", "30 DAYS": "Net30",
    "N45": "Net45", "NET45": "Net45", "N60": "Net60", "NET 15": "Net15",}
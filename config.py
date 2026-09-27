"""Central configuration for the P2P Data Hub pipeline."""

from pathlib import Path
# __file__: es una variable especial que Python llena solo. 
# Contiene la ubicación del archivo que se está ejecutando, en este caso config.py.
# Path(__file__): convierte esa ubicación en un objeto Path para poder trabajar con ella.
# .resolve(): la convierte en la ruta completa y exacta, 
# por ejemplo C:\Users\Paulo\Documents\p2p-data-hub\config.py.
# .parent: sube un nivel, es decir, se queda con la carpeta 
# donde está el archivo: C:\Users\Paulo\Documents\p2p-data-hub.
BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR= BASE_DIR / "data"/ "source"
MOCK_API_DIR= BASE_DIR / "mock_api"
DB_PATH= BASE_DIR / "output"/ "p2p_data_hub.db"
D365_IMPORT_DIR = BASE_DIR / "output" / "d365_import"
EXCEPTIONS_DIR = BASE_DIR / "output" / "exceptions"
POWERBI_DIR = BASE_DIR / "output" / "powerbi"
SQL_DIR = BASE_DIR / "sql"


API_HOST, API_PORT= "localhost", 8000
API_BASE_URL = F"http://{API_HOST}:{API_PORT}/data" 
#Por qué termina en /data y no en un archivo: porque es la base,
#  la parte que se repite siempre. Después, en el código,
#  le agregas el nombre de lo que quieras pedir, 
# por ejemplo PurchaseOrderLines_page1.json. Así escribes la base una sola vez.


# Business rules (owned by Finance, documented in the data management plan)
PRICE_TOLERANCE = 0.05              
VALID_CURRENCIES= {"USD","CRC", "EUR"}
VALID_PAYMENT_TERMS = {"Net15", "Net30", "Net45", "Net60"}
PAYMENT_TERMS_FIX = {                        # standardization map legacy -> D365
    "N30": "Net30", "NET 30": "Net30", "30 DAYS": "Net30",
    "N45": "Net45", "NET45": "Net45", "N60": "Net60", "NET 15": "Net15",}
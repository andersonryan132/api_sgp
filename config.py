import os
from dotenv import load_dotenv
load_dotenv()

# Token que quem chama sua API deve enviar
API_TOKEN = os.getenv("API_TOKEN")

# Credenciais do SGP
SGP_USER = os.getenv("SGP_USER")
SGP_PASS = os.getenv("SGP_PASS")

LOGIN_URL = "https://adtelecom.sgp.net.br/accounts/login/?next=/admin/"
COOKIES_FILE = "sgp_cookies.pkl"

# Segurança: valida se tudo foi carregado
if not API_TOKEN:
    raise RuntimeError("Variável de ambiente API_TOKEN não definida")

if not SGP_USER or not SGP_PASS:
    raise RuntimeError("Variáveis SGP_USER ou SGP_PASS não definidas")
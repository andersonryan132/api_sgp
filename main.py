from fastapi import FastAPI, Header, HTTPException
from sgp_client import disconnect
from config import API_TOKEN

app = FastAPI(title="SGP Disconnect API")

@app.post("/disconnect")
def api_disconnect(contrato_id: str, authorization: str = Header(None)):
    
    # --- Valida token ---
    if not authorization or authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Token inválido")

    # --- Executa disconnect ---
    try:
        disconnect(contrato_id)
        return {"status": "success", "contrato": contrato_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

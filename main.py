from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException
from sgp_client import disconnect, add_cliente_contact
from config import API_TOKEN

app = FastAPI(title="SGP Disconnect API")


class UpdateContatoRequest(BaseModel):
    cliente_id: str
    contato: str


@app.post("/disconnect")
def api_disconnect(contrato_id: str, authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Token invalido")

    try:
        disconnect(contrato_id)
        return {"status": "success", "contrato": contrato_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-phone")
def api_update_phone(payload: UpdateContatoRequest, authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Token invalido")

    try:
        result = add_cliente_contact(
            cliente_id=payload.cliente_id,
            contato=payload.contato,
        )
        return {
            "status": "success" if result.get("ok") else "error",
            "cliente_id": payload.cliente_id,
            "contato": payload.contato,
            "sgp_result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

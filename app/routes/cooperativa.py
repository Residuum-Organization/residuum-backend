from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role, validar_acesso_operacional_ao_ponto
from app.models.descarte import Descarte
from app.models.usuario import Usuario
from app.schemas.admin import RejeitarDescarteRequest
from app.services.descarte_service import rejeitar_descarte_pendente


router = APIRouter(
    prefix="/cooperativa",
    tags=["Cooperativa"],
)


@router.post("/descartes/{id_descarte}/rejeitar")
def rejeitar_descarte_cooperativa(
    id_descarte: int,
    payload: RejeitarDescarteRequest,
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    """Rejeita descarte pendente vinculado a ponto da cooperativa autenticada."""
    descarte = (
        db.query(Descarte).filter(Descarte.id_descarte == id_descarte).first()
    )
    if not descarte:
        raise HTTPException(status_code=404, detail="Descarte nao encontrado")

    validar_acesso_operacional_ao_ponto(cooperativa, descarte.ponto_coleta)
    rejeitar_descarte_pendente(db, descarte, cooperativa, payload.motivo)

    db.commit()
    db.refresh(descarte)
    return {
        "id": descarte.id_descarte,
        "status": descarte.status,
        "motivo_rejeicao": payload.motivo,
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role, validar_acesso_operacional_ao_ponto
from app.models.descarte import Descarte
from app.models.ponto_coleta import PontoColeta
from app.models.usuario import Usuario
from app.schemas.admin import RejeitarDescarteRequest
from app.services.descarte_service import rejeitar_descarte_pendente


router = APIRouter(
    prefix="/cooperativa",
    tags=["Cooperativa"],
)


@router.get("/pontos-coleta")
def listar_pontos_da_cooperativa(
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    """Lista somente os pontos sob responsabilidade da conta operacional."""
    pontos = (
        db.query(PontoColeta)
        .filter(PontoColeta.cooperativa_id == cooperativa.id)
        .order_by(PontoColeta.nome)
        .all()
    )
    return [
        {
            "id": ponto.id,
            "nome": ponto.nome,
            "endereco": ponto.endereco,
            "latitude": ponto.latitude,
            "longitude": ponto.longitude,
            "raio_operacao": ponto.raio_operacao,
            "capacidade_maxima": ponto.capacidade_maxima,
            "tipos_residuos_aceitos": ponto.tipos_residuos_aceitos or [],
            "horario_funcionamento": ponto.horario_funcionamento,
            "status": ponto.status,
            "inventario": ponto.inventario or {},
        }
        for ponto in pontos
    ]


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

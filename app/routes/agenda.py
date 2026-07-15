from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import raise_not_found
from app.database import get_db
from app.dependencies.auth import require_role
from app.models.agenda import Agenda
from app.models.ponto_coleta import PontoColeta
from app.models.usuario import Usuario
from app.schemas.agenda import AgendaCreate, AgendaResponse, AgendaUpdate

router = APIRouter(prefix="/admin/agenda", tags=["Agenda"])


def _validar_ponto(db: Session, ponto_id: int, usuario: Usuario) -> PontoColeta:
    ponto = db.query(PontoColeta).filter(PontoColeta.id == ponto_id).first()
    if not ponto or (usuario.role == "cooperativa" and ponto.cooperativa_id != usuario.id):
        raise_not_found("Ponto de coleta nao encontrado.")
    return ponto


def _validar_agenda(db: Session, agenda_id: int, usuario: Usuario) -> Agenda:
    agenda = db.query(Agenda).filter(Agenda.id == agenda_id).first()
    if not agenda or (
        usuario.role == "cooperativa"
        and agenda.ponto_coleta.cooperativa_id != usuario.id
    ):
        raise_not_found("Agendamento nao encontrado.")
    return agenda


@router.get("", response_model=list[AgendaResponse])
def listar_agendas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    query = db.query(Agenda)
    if usuario.role == "cooperativa":
        query = query.join(PontoColeta).filter(PontoColeta.cooperativa_id == usuario.id)
    return query.order_by(Agenda.data.desc()).all()


@router.post("", response_model=AgendaResponse, status_code=201)
def criar_agendamento(
    payload: AgendaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    _validar_ponto(db, payload.ponto_coleta_id, usuario)
    agenda = Agenda(
        ponto_coleta_id=payload.ponto_coleta_id,
        data=payload.data,
        turno_id=payload.turno_id,
        status="agendado",
    )
    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


@router.put("/{agenda_id}", response_model=AgendaResponse)
def atualizar_agendamento(
    agenda_id: int,
    payload: AgendaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    agenda = _validar_agenda(db, agenda_id, usuario)
    if payload.ponto_coleta_id is not None:
        _validar_ponto(db, payload.ponto_coleta_id, usuario)

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(agenda, key, value)

    db.commit()
    db.refresh(agenda)
    return agenda


@router.delete("/{agenda_id}", status_code=204)
def deletar_agendamento(
    agenda_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    agenda = _validar_agenda(db, agenda_id, usuario)
    db.delete(agenda)
    db.commit()
    return None

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import raise_not_found
from app.database import get_db
from app.dependencies.auth import require_role
from app.models.agenda import Agenda
from app.models.usuario import Usuario
from app.schemas.agenda import AgendaCreate, AgendaResponse, AgendaUpdate

router = APIRouter(prefix="/admin/agenda", tags=["Agenda (Admin)"])

@router.get("", response_model=list[AgendaResponse])
def listar_agendas(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    return db.query(Agenda).order_by(Agenda.data.desc()).all()

@router.post("", response_model=AgendaResponse, status_code=201)
def criar_agendamento(
    payload: AgendaCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    agenda = Agenda(
        ponto_coleta_id=payload.ponto_coleta_id,
        data=payload.data,
        turno_id=payload.turno_id,
        status="agendado"
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
    admin: Usuario = Depends(require_role("admin")),
):
    agenda = db.query(Agenda).filter(Agenda.id == agenda_id).first()
    if not agenda:
        raise_not_found("Agendamento não encontrado.")
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agenda, key, value)
        
    db.commit()
    db.refresh(agenda)
    return agenda

@router.delete("/{agenda_id}", status_code=204)
def deletar_agendamento(
    agenda_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    agenda = db.query(Agenda).filter(Agenda.id == agenda_id).first()
    if not agenda:
        raise_not_found("Agendamento não encontrado.")
        
    db.delete(agenda)
    db.commit()
    return None

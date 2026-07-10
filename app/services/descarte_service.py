from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.descarte import Descarte
from app.models.estoque import Estoque
from app.models.inventario_usuario import InventarioUsuario
from app.models.usuario import Usuario
from app.schemas.descarte import DescarteCreate, DescarteConfirmar
from app.services.audit_service import registrar_acao

def registrar_novo_descarte(db: Session, descarte_data: DescarteCreate):
    novo_descarte = Descarte(**descarte_data.model_dump())
    db.add(novo_descarte)
    db.commit()
    db.refresh(novo_descarte)
    return novo_descarte

def confirmar_e_atualizar_estoque(db: Session, descarte_id: int, dados: DescarteConfirmar):
    # Busca o descarte
    descarte = db.query(Descarte).filter(Descarte.id_descarte == descarte_id).first()
    if not descarte:
        return None

    # Atualiza o status e a quantidade confirmada
    descarte.quantidade_confirmada = dados.quantidade_confirmada
    descarte.status = "concluido"

    # Atualiza ou Cria o registro no Estoque
    estoque_item = db.query(Estoque).filter(Estoque.tipo_residuo == descarte.tipo_residuo).first()
    
    if estoque_item:
        estoque_item.quantidade_total += dados.quantidade_confirmada
    else:
        novo_estoque = Estoque(
            tipo_residuo=descarte.tipo_residuo,
            quantidade_total=dados.quantidade_confirmada
        )
        db.add(novo_estoque)

    db.commit()
    db.refresh(descarte)
    return descarte


def rejeitar_descarte_pendente(
    db: Session,
    descarte: Descarte,
    operador: Usuario,
    motivo: str,
) -> Descarte:
    """Rejeita um descarte pendente e libera reserva de inventario, se houver."""
    if descarte.status != "pendente":
        raise HTTPException(
            status_code=400,
            detail="Apenas descartes pendentes podem ser rejeitados",
        )

    status_anterior = descarte.status
    descarte.status = "rejeitado"

    if descarte.inventario_usuario_id:
        item = (
            db.query(InventarioUsuario)
            .filter(
                InventarioUsuario.id == descarte.inventario_usuario_id,
                InventarioUsuario.usuario_id == descarte.usuario_id,
            )
            .first()
        )
        if item:
            reservada_atual = float(item.quantidade_reservada or 0)
            item.quantidade_reservada = max(
                reservada_atual - float(descarte.quantidade),
                0,
            )
            if item.status in ("em_transferencia",):
                item.status = "disponivel"

    registrar_acao(
        db,
        admin_id=operador.id,
        action="descarte.rejeitar",
        target_type="descarte",
        target_id=descarte.id_descarte,
        motivo=motivo,
        payload={"status_anterior": status_anterior},
    )
    return descarte

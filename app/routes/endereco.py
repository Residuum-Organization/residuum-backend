"""
Rotas de Endereço

Gerencia o endereço do usuário autenticado.
O id do usuário é sempre obtido do token, nunca de path/body.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.endereco import Endereco
from app.models.usuario import Usuario
from app.schemas.endereco import EnderecoCreate

router = APIRouter(tags=["Endereço"])


@router.put("/me/endereco")
def upsert_endereco(
    dados: EnderecoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Cria ou atualiza o endereço do usuário autenticado.

    Se o usuário ainda não tem endereço, cria um novo e vincula.
    Se já tem, atualiza os campos do endereço existente.
    """
    if usuario.endereco_id is None:
        novo = Endereco(**dados.model_dump())
        db.add(novo)
        db.flush()
        usuario.endereco_id = novo.id_end
        endereco = novo
    else:
        endereco = db.query(Endereco).filter(Endereco.id_end == usuario.endereco_id).first()
        for campo, valor in dados.model_dump().items():
            setattr(endereco, campo, valor)

    db.commit()
    db.refresh(endereco)

    return {
        "id_end": endereco.id_end,
        "rua": endereco.rua,
        "bairro": endereco.bairro,
        "numero": endereco.numero,
        "cep": endereco.cep,
        "cidade": endereco.cidade,
    }

from sqlalchemy.orm import Session
from app.models.ponto_coleta import PontoColeta
from app.models.notificacao import Notificacao

def verificar_capacidade_e_notificar(db: Session, ponto: PontoColeta):
    peso_total = sum(ponto.inventario.values()) if ponto.inventario else 0.0
    
    if ponto.capacidade_maxima and peso_total >= ponto.capacidade_maxima:
        if ponto.status != "cheio":
            ponto.status = "cheio"
            
            mensagem_alerta = f"O Ponto de Coleta '{ponto.nome}' atingiu sua capacidade máxima."
            nova_notificacao = Notificacao(
                mensagem=mensagem_alerta, 
                tipo="ponto_cheio",
                ponto_coleta_id=ponto.id 
            )
            
            db.add(nova_notificacao)
            db.commit()
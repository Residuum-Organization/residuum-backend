import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app  # noqa: F401 - registra todos os modelos no metadata
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.ponto_coleta import PontoColeta
from app.models.transferencia_lote import TransferenciaLote
from app.models.usuario import Usuario
from app.routes.inventario_usuario import transferir_itens_em_lote
from app.schemas.inventario_usuario import InventarioLoteTransferir


class TransferenciaLoteIntegracaoTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.usuario = Usuario(
            nome="Morador Teste",
            email="morador@example.com",
            telefone="92999999999",
            senha_hash="hash",
            role="usuario",
        )
        self.ponto = PontoColeta(
            nome="Ponto Teste",
            endereco="Rua Teste",
            latitude=-3.0,
            longitude=-60.0,
            raio_operacao=1000,
            tipos_residuos_aceitos=["plástico", "papel"],
            status="ativo",
            ativo=1,
        )
        self.session.add_all([self.usuario, self.ponto])
        self.session.flush()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _criar_item(self, tipo: str, quantidade: float) -> InventarioUsuario:
        item = InventarioUsuario(
            usuario_id=self.usuario.id,
            tipo_residuo=tipo,
            quantidade=quantidade,
            quantidade_reservada=0,
            codigo_barras="001234567890",
            sem_rotulo=False,
            status="disponivel",
        )
        self.session.add(item)
        self.session.commit()
        return item

    def _payload(self, itens: list[dict], chave: str) -> InventarioLoteTransferir:
        return InventarioLoteTransferir(
            itens=itens,
            ponto_coleta_id=self.ponto.id,
            usuario_lat=-3.0,
            usuario_long=-60.0,
            usuario_precisao=8,
            chave_idempotencia=chave,
        )

    def test_repeticao_idempotente_nao_duplica_reserva(self):
        item = self._criar_item("plastico", 5)
        payload = self._payload(
            [{"item_id": item.id, "quantidade": 3}],
            "lote-idempotente-001",
        )

        primeira = transferir_itens_em_lote(payload, self.session, self.usuario)
        segunda = transferir_itens_em_lote(payload, self.session, self.usuario)

        self.session.refresh(item)
        self.assertEqual(primeira["id"], segunda["id"])
        self.assertEqual(item.quantidade_reservada, 3)
        self.assertEqual(self.session.query(Descarte).count(), 1)
        self.assertEqual(self.session.query(TransferenciaLote).count(), 1)

    def test_item_invalido_nao_cria_lote_parcial(self):
        item_valido = self._criar_item("plastico", 5)
        item_invalido = self._criar_item("papel", 1)
        payload = self._payload(
            [
                {"item_id": item_valido.id, "quantidade": 2},
                {"item_id": item_invalido.id, "quantidade": 2},
            ],
            "lote-atomico-001",
        )

        with self.assertRaises(HTTPException):
            transferir_itens_em_lote(payload, self.session, self.usuario)

        self.session.refresh(item_valido)
        self.session.refresh(item_invalido)
        self.assertEqual(item_valido.quantidade_reservada, 0)
        self.assertEqual(item_invalido.quantidade_reservada, 0)
        self.assertEqual(self.session.query(Descarte).count(), 0)
        self.assertEqual(self.session.query(TransferenciaLote).count(), 0)


if __name__ == "__main__":
    unittest.main()

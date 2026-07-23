import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app  # noqa: F401 - registra todos os modelos no metadata
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.pontuacao import Pontuacao
from app.models.ponto_coleta import PontoColeta
from app.models.transferencia_lote import TransferenciaLote
from app.models.usuario import Usuario
from app.routes.descarte import confirmar_descarte
from app.routes.inventario_usuario import transferir_itens_em_lote
from app.schemas.descarte import DescarteConfirmar
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
        self.admin = Usuario(
            nome="Admin Teste",
            email="admin@example.com",
            telefone="92888888888",
            senha_hash="hash",
            role="admin",
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
        self.session.add_all([self.usuario, self.admin, self.ponto])
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

    def _criar_descarte_pendente(self, codigo: str = "001234567890") -> Descarte:
        item = self._criar_item("plastico", 1)
        item.codigo_barras = codigo
        item.quantidade_reservada = 1
        item.status = "em_transferencia"
        descarte = Descarte(
            quantidade=1,
            tipo_residuo=item.tipo_residuo,
            status="pendente",
            usuario_id=self.usuario.id,
            ponto_coleta_id=self.ponto.id,
            inventario_usuario_id=item.id,
        )
        self.session.add(descarte)
        self.session.commit()
        return descarte

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

    def test_retry_que_aguardou_lock_retorna_lote_concorrente(self):
        item = self._criar_item("plastico", 5)
        lote_existente = TransferenciaLote(
            id="00000000-0000-0000-0000-000000000001",
            usuario_id=self.usuario.id,
            ponto_coleta_id=self.ponto.id,
            chave_idempotencia="lote-concorrente-001",
            usuario_lat=-3.0,
            usuario_long=-60.0,
            usuario_precisao=8,
            status="pendente",
            total_itens=1,
            peso_total=5,
            pontos_estimados=50,
        )
        item.quantidade_reservada = 5
        item.status = "em_transferencia"
        descarte_existente = Descarte(
            quantidade=5,
            tipo_residuo=item.tipo_residuo,
            status="pendente",
            usuario_id=self.usuario.id,
            ponto_coleta_id=self.ponto.id,
            inventario_usuario_id=item.id,
            transferencia_lote_id=lote_existente.id,
        )
        self.session.add_all([lote_existente, descarte_existente])
        self.session.commit()

        payload = self._payload(
            [{"item_id": item.id, "quantidade": 5}],
            "lote-concorrente-001",
        )
        with patch(
            "app.routes.inventario_usuario._buscar_lote_por_idempotencia",
            side_effect=[None, lote_existente],
        ):
            resposta = transferir_itens_em_lote(payload, self.session, self.usuario)

        self.session.refresh(item)
        self.assertEqual(resposta["id"], lote_existente.id)
        self.assertEqual(item.quantidade_reservada, 5)
        self.assertEqual(self.session.query(Descarte).count(), 1)

    def test_admin_tambem_precisa_identificar_produto(self):
        descarte = self._criar_descarte_pendente()

        with self.assertRaises(HTTPException) as contexto:
            asyncio.run(
                confirmar_descarte(
                    descarte.id_descarte,
                    DescarteConfirmar(quantidade_confirmada=1),
                    self.session,
                    self.admin,
                )
            )

        self.assertEqual(contexto.exception.status_code, 422)
        self.assertEqual(descarte.status, "pendente")
        self.assertEqual(self.usuario.pontuacao_total or 0, 0)

    def test_confirmacoes_acumulam_pontos_e_estoque(self):
        primeiro = self._criar_descarte_pendente("001234567891")
        segundo = self._criar_descarte_pendente("001234567892")

        for descarte, codigo in (
            (primeiro, "001234567891"),
            (segundo, "001234567892"),
        ):
            asyncio.run(
                confirmar_descarte(
                    descarte.id_descarte,
                    DescarteConfirmar(
                        quantidade_confirmada=1,
                        codigo_barras_validado=codigo,
                    ),
                    self.session,
                    self.admin,
                )
            )

        self.session.refresh(self.usuario)
        self.session.refresh(self.ponto)
        self.assertEqual(self.usuario.pontuacao_total, 20)
        self.assertEqual(self.ponto.inventario["plastico"], 2)
        self.assertEqual(self.session.query(Pontuacao).count(), 2)


if __name__ == "__main__":
    unittest.main()

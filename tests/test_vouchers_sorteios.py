import unittest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app  # noqa: F401 - registra todos os modelos no metadata
from app.models.bilhete_sorteio import BilheteSorteio
from app.models.descarte import Descarte
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.resgate_voucher import ResgateVoucher
from app.models.sorteio import Sorteio
from app.models.usuario import Usuario
from app.models.voucher import Voucher
from app.routes.pontuacao import registrar_resgate_pontos
from app.routes.sorteio import comprar_bilhete
from app.routes.voucher import resgatar_voucher
from app.schemas.pontuacao import PontuacaoResgateCreate
from app.services.extrato_pontos_service import montar_extrato_pontos_usuario
from app.services.saldo_service import SaldoInsuficiente, debitar_pontos


class SaldoTestCase(unittest.TestCase):
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
            pontuacao_total=100,
        )
        self.session.add(self.usuario)
        self.session.flush()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _voucher(self, custo=40, estoque=5) -> Voucher:
        voucher = Voucher(
            titulo="Voucher Teste",
            parceiro="Parceiro",
            custo_pontos=custo,
            quantidade_disponivel=estoque,
            status="ativo",
        )
        self.session.add(voucher)
        self.session.flush()
        return voucher

    def _sorteio(self, custo=30) -> Sorteio:
        sorteio = Sorteio(titulo="Sorteio Teste", premio="Bicicleta", custo_pontos=custo, status="ativo")
        self.session.add(sorteio)
        self.session.flush()
        return sorteio

    def _descarte_gps(self):
        self.session.add(
            Descarte(
                quantidade=1,
                quantidade_confirmada=1,
                tipo_residuo="plastico",
                status="confirmado",
                usuario_id=self.usuario.id,
                usuario_lat=-3.1,
                usuario_long=-60.0,
            )
        )
        self.session.flush()

    def _resgatar(self, voucher, chave=None):
        resposta = Response()
        dados = resgatar_voucher(voucher.id, resposta, self.session, self.usuario, chave)
        return dados, resposta.status_code

    def _comprar(self, sorteio, chave=None):
        resposta = Response()
        dados = comprar_bilhete(sorteio.id, resposta, self.session, self.usuario, chave)
        return dados, resposta.status_code

    def _saldo(self) -> int:
        return self.session.execute(
            text("SELECT pontuacao_total FROM usuario WHERE id = :id"), {"id": self.usuario.id}
        ).scalar()

    # --- helper de debito ---

    def test_debito_le_o_saldo_do_banco_e_nao_do_objeto_em_memoria(self):
        self.session.commit()
        # Outra operacao mexeu no saldo por fora desta sessao.
        self.session.execute(text("UPDATE usuario SET pontuacao_total = 10"))
        with self.assertRaises(SaldoInsuficiente):
            debitar_pontos(self.session, self.usuario.id, 50, origem="resgate", descricao="x")
        self.assertEqual(self._saldo(), 10)

    def test_debito_sem_saldo_nao_registra_extrato(self):
        with self.assertRaises(SaldoInsuficiente):
            debitar_pontos(self.session, self.usuario.id, 101, origem="resgate", descricao="x")
        self.assertEqual(self.session.query(ResgatePontuacao).count(), 0)
        self.assertEqual(self._saldo(), 100)

    def test_debito_negativo_e_recusado(self):
        with self.assertRaises(ValueError):
            debitar_pontos(self.session, self.usuario.id, -5, origem="resgate", descricao="x")

    # --- vouchers ---

    def test_resgate_debita_baixa_estoque_e_registra_origem(self):
        voucher = self._voucher(custo=40, estoque=5)
        dados, _ = self._resgatar(voucher)

        self.assertEqual(self._saldo(), 60)
        self.assertEqual(voucher.quantidade_disponivel, 4)
        evento = self.session.query(ResgatePontuacao).one()
        self.assertEqual(evento.origem, "voucher")
        self.assertEqual(evento.pontos_utilizados, 40)
        self.assertEqual(evento.referencia, dados.codigo)

    def test_resgate_sem_saldo_nao_muda_nada(self):
        voucher = self._voucher(custo=500)
        with self.assertRaises(HTTPException) as erro:
            self._resgatar(voucher)
        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(self._saldo(), 100)
        self.assertEqual(voucher.quantidade_disponivel, 5)
        self.assertEqual(self.session.query(ResgateVoucher).count(), 0)

    def test_reenvio_com_mesma_chave_devolve_o_mesmo_resgate(self):
        voucher = self._voucher(custo=40)
        primeiro, _ = self._resgatar(voucher, chave="abc-1")
        segundo, status_segundo = self._resgatar(voucher, chave="abc-1")

        self.assertEqual(primeiro.id, segundo.id)
        self.assertEqual(primeiro.codigo, segundo.codigo)
        self.assertEqual(status_segundo, 200)
        self.assertEqual(self._saldo(), 60)
        self.assertEqual(voucher.quantidade_disponivel, 4)
        self.assertEqual(self.session.query(ResgateVoucher).count(), 1)
        self.assertEqual(self.session.query(ResgatePontuacao).count(), 1)

    def test_reenvio_com_chave_funciona_mesmo_com_o_ultimo_do_estoque(self):
        voucher = self._voucher(custo=40, estoque=1)
        primeiro, _ = self._resgatar(voucher, chave="ultimo")
        segundo, _ = self._resgatar(voucher, chave="ultimo")
        self.assertEqual(primeiro.id, segundo.id)
        self.assertEqual(voucher.quantidade_disponivel, 0)

    def test_sem_chave_cada_pedido_e_um_resgate(self):
        voucher = self._voucher(custo=40)
        self._resgatar(voucher)
        self._resgatar(voucher)
        self.assertEqual(self._saldo(), 20)
        self.assertEqual(self.session.query(ResgateVoucher).count(), 2)

    def test_chave_de_outro_voucher_e_conflito(self):
        a = self._voucher(custo=10)
        b = self._voucher(custo=10)
        self._resgatar(a, chave="mesma")
        with self.assertRaises(HTTPException) as erro:
            self._resgatar(b, chave="mesma")
        self.assertEqual(erro.exception.status_code, 409)
        self.assertEqual(self._saldo(), 90)

    # --- sorteios ---

    def test_bilhete_debita_e_registra_origem(self):
        self._descarte_gps()
        sorteio = self._sorteio(custo=30)
        bilhete, _ = self._comprar(sorteio)

        self.assertEqual(bilhete.numero, 1)
        self.assertEqual(self._saldo(), 70)
        evento = self.session.query(ResgatePontuacao).one()
        self.assertEqual(evento.origem, "sorteio")
        self.assertEqual(evento.referencia, f"sorteio:{sorteio.id}:bilhete:1")

    def test_bilhete_sem_saldo_nao_muda_nada(self):
        self._descarte_gps()
        sorteio = self._sorteio(custo=500)
        with self.assertRaises(HTTPException) as erro:
            self._comprar(sorteio)
        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(self._saldo(), 100)
        self.assertEqual(self.session.query(BilheteSorteio).count(), 0)

    def test_reenvio_com_mesma_chave_devolve_o_mesmo_bilhete(self):
        self._descarte_gps()
        sorteio = self._sorteio(custo=30)
        primeiro, _ = self._comprar(sorteio, chave="k1")
        segundo, status_segundo = self._comprar(sorteio, chave="k1")

        self.assertEqual(primeiro.id, segundo.id)
        self.assertEqual(status_segundo, 200)
        self.assertEqual(self._saldo(), 70)
        self.assertEqual(self.session.query(BilheteSorteio).count(), 1)

    def test_segundo_bilhete_com_outra_chave_continua_recusado(self):
        self._descarte_gps()
        sorteio = self._sorteio(custo=30)
        self._comprar(sorteio, chave="k1")
        with self.assertRaises(HTTPException) as erro:
            self._comprar(sorteio, chave="k2")
        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(self._saldo(), 70)

    def test_chave_de_outro_sorteio_e_conflito(self):
        self._descarte_gps()
        a = self._sorteio(custo=10)
        b = self._sorteio(custo=10)
        self._comprar(a, chave="mesma")
        with self.assertRaises(HTTPException) as erro:
            self._comprar(b, chave="mesma")
        self.assertEqual(erro.exception.status_code, 409)

    # --- extrato ---

    def test_extrato_traz_a_origem_de_cada_debito(self):
        self._descarte_gps()
        self._resgatar(self._voucher(custo=10))
        self._comprar(self._sorteio(custo=10))
        registrar_resgate_pontos(
            PontuacaoResgateCreate(pontos=5, descricao="Resgate manual"), self.session, self.usuario
        )

        itens = montar_extrato_pontos_usuario(self.usuario, self.session)["itens"]
        origens = sorted(i["origem"] for i in itens if i["pontos"] < 0)
        self.assertEqual(origens, ["resgate", "sorteio", "voucher"])
        self.assertEqual(self._saldo(), 75)


if __name__ == "__main__":
    unittest.main()

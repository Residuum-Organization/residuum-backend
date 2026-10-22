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
from app.models.notificacao import Notificacao
from app.models.resgate_voucher import ResgateVoucher
from app.models.sorteio import Sorteio
from app.models.usuario import Usuario
from app.models.voucher import Voucher, VoucherCodigo
from app.routes.notificacao import (
    listar_minhas_notificacoes,
    listar_notificacoes_nao_lidas,
    marcar_minha_notificacao_como_lida,
)
from app.routes.pontuacao import registrar_resgate_pontos
from app.routes.sorteio import comprar_bilhete, sortear_vencedor
from app.routes.voucher import (
    adicionar_codigos_voucher,
    listar_codigos_voucher,
    obter_voucher,
    remover_codigo_voucher,
    resgatar_voucher,
)
from app.schemas.pontuacao import PontuacaoResgateCreate
from app.schemas.voucher import VoucherCodigosCreate
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


    # --- codigos do parceiro ---

    def _admin(self) -> Usuario:
        admin = Usuario(
            nome="Admin Teste",
            email="admin@example.com",
            telefone="92988888888",
            senha_hash="hash",
            role="admin",
            pontuacao_total=0,
        )
        self.session.add(admin)
        self.session.flush()
        return admin

    def _adicionar_codigos(self, voucher, codigos):
        return adicionar_codigos_voucher(
            voucher.id, VoucherCodigosCreate(codigos=codigos), self.session, self._admin_obj
        )

    @property
    def _admin_obj(self):
        if not hasattr(self, "_admin_cache"):
            self._admin_cache = self._admin()
        return self._admin_cache

    def test_codigos_do_parceiro_somam_ao_estoque_e_ignoram_repetidos_e_espacos(self):
        voucher = self._voucher(custo=10, estoque=0)
        resposta = self._adicionar_codigos(voucher, [" AAA111 ", "BBB222", "AAA111", "  "])

        self.assertEqual(resposta.disponiveis, 2)
        self.assertEqual(voucher.quantidade_disponivel, 2)
        self.assertEqual([c.codigo for c in resposta.codigos], ["AAA111", "BBB222"])

    def test_codigo_ja_cadastrado_em_qualquer_voucher_e_conflito(self):
        a = self._voucher()
        b = self._voucher()
        self._adicionar_codigos(a, ["REPETIDO"])
        with self.assertRaises(HTTPException) as erro:
            self._adicionar_codigos(b, ["NOVO", "REPETIDO"])
        self.assertEqual(erro.exception.status_code, 409)
        self.assertEqual(self.session.query(VoucherCodigo).count(), 1)

    def test_codigo_maior_que_o_limite_e_recusado(self):
        voucher = self._voucher()
        with self.assertRaises(HTTPException) as erro:
            self._adicionar_codigos(voucher, ["X" * 41])
        self.assertEqual(erro.exception.status_code, 400)

    def test_resgate_entrega_o_codigo_do_parceiro_na_ordem(self):
        voucher = self._voucher(custo=10, estoque=0)
        self._adicionar_codigos(voucher, ["AAA111", "BBB222"])

        primeiro, _ = self._resgatar(voucher)
        segundo, _ = self._resgatar(voucher)

        self.assertEqual((primeiro.codigo, segundo.codigo), ("AAA111", "BBB222"))
        listagem = listar_codigos_voucher(voucher.id, self.session, self._admin_obj)
        self.assertEqual((listagem.disponiveis, listagem.resgatados), (0, 2))
        self.assertEqual(voucher.quantidade_disponivel, 0)

    def test_sem_codigo_disponivel_esgota_mesmo_com_estoque_manual(self):
        voucher = self._voucher(custo=10, estoque=0)
        self._adicionar_codigos(voucher, ["UNICO"])
        self._resgatar(voucher)
        voucher.quantidade_disponivel = 5  # admin aumentou o numero, mas nao ha codigo
        with self.assertRaises(HTTPException) as erro:
            self._resgatar(voucher)
        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(self._saldo(), 90)

    def test_voucher_sem_codigos_cadastrados_continua_gerando_codigo_proprio(self):
        voucher = self._voucher(custo=10)
        dados, _ = self._resgatar(voucher)
        self.assertTrue(dados.codigo.startswith("RSDM-"))

    def test_remover_codigo_tira_do_estoque_e_nao_remove_entregue(self):
        voucher = self._voucher(estoque=0)
        resposta = self._adicionar_codigos(voucher, ["AAA111", "BBB222"])
        id_a, id_b = (c.id for c in resposta.codigos)
        self._resgatar(voucher)  # entrega AAA111

        remover_codigo_voucher(voucher.id, id_b, self.session, self._admin_obj)
        self.assertEqual(voucher.quantidade_disponivel, 0)
        with self.assertRaises(HTTPException) as erro:
            remover_codigo_voucher(voucher.id, id_a, self.session, self._admin_obj)
        self.assertEqual(erro.exception.status_code, 400)

    # --- validade e instrucoes ---

    def test_validade_do_codigo_vem_do_voucher(self):
        voucher = self._voucher(custo=10)
        voucher.validade_codigo_dias = 30
        dados, _ = self._resgatar(voucher)

        esperado = datetime.now(timezone.utc) + timedelta(days=30)
        valido_ate = dados.valido_ate.replace(tzinfo=dados.valido_ate.tzinfo or timezone.utc)
        self.assertLess(abs((valido_ate - esperado).total_seconds()), 60)
        self.assertIn("Use até", dados.instrucoes_uso)

    def test_sem_validade_nao_ha_prazo_nem_linha_de_validade(self):
        voucher = self._voucher(custo=10)
        dados, _ = self._resgatar(voucher)
        self.assertIsNone(dados.valido_ate)
        self.assertNotIn("Use até", dados.instrucoes_uso)

    def test_codigo_vencido_aparece_como_expirado(self):
        voucher = self._voucher(custo=10)
        dados, _ = self._resgatar(voucher)
        resgate = self.session.query(ResgateVoucher).one()
        resgate.valido_ate = datetime.now(timezone.utc) - timedelta(days=1)

        from app.routes.voucher import listar_meus_resgates_voucher

        itens = listar_meus_resgates_voucher(self.session, self.usuario)
        self.assertEqual(itens[0].status, "expirado")

    def test_detalhe_traz_instrucoes_padrao_com_o_parceiro(self):
        voucher = self._voucher()
        detalhe = obter_voucher(voucher.id, self.session)
        self.assertIn("Parceiro", detalhe.instrucoes_uso)
        self.assertIn("Meus resgates", detalhe.instrucoes_uso)

    def test_detalhe_usa_o_texto_do_admin_e_avisa_o_prazo(self):
        voucher = self._voucher()
        voucher.instrucoes = "Mostre o código no caixa."
        voucher.validade_codigo_dias = 15
        detalhe = obter_voucher(voucher.id, self.session)
        self.assertTrue(detalhe.instrucoes_uso.startswith("Mostre o código no caixa."))
        self.assertIn("15 dias", detalhe.instrucoes_uso)

    def test_detalhe_de_voucher_inativo_nao_aparece(self):
        voucher = self._voucher()
        voucher.status = "inativo"
        with self.assertRaises(HTTPException) as erro:
            obter_voucher(voucher.id, self.session)
        self.assertEqual(erro.exception.status_code, 404)

    # --- notificacao do sorteio ---

    def _outro_morador(self) -> Usuario:
        outro = Usuario(
            nome="Outro Morador",
            email="outro@example.com",
            telefone="92977777777",
            senha_hash="hash",
            role="usuario",
            pontuacao_total=100,
        )
        self.session.add(outro)
        self.session.flush()
        self.session.add(
            Descarte(
                quantidade=1,
                quantidade_confirmada=1,
                tipo_residuo="plastico",
                status="confirmado",
                usuario_id=outro.id,
                usuario_lat=-3.1,
                usuario_long=-60.0,
            )
        )
        self.session.flush()
        return outro

    def _sorteio_apurado(self):
        """Dois participantes compram bilhete e o admin apura."""
        self._descarte_gps()
        outro = self._outro_morador()
        sorteio = self._sorteio(custo=10)
        self._comprar(sorteio)
        comprar_bilhete(sorteio.id, Response(), self.session, outro, None)
        sorteio.status = "encerrado"
        resultado = sortear_vencedor(sorteio.id, self.session, self._admin_obj)
        return sorteio, outro, resultado

    def test_apuracao_avisa_o_ganhador_e_os_demais_participantes(self):
        sorteio, outro, resultado = self._sorteio_apurado()

        avisos = self.session.query(Notificacao).filter(Notificacao.usuario_id.isnot(None)).all()
        por_usuario = {a.usuario_id: a for a in avisos}
        self.assertEqual(len(avisos), 2)
        ganhador_id = resultado["usuario_id"]
        perdedor_id = ({self.usuario.id, outro.id} - {ganhador_id}).pop()
        self.assertEqual(por_usuario[ganhador_id].tipo, "sorteio_ganhador")
        self.assertIn("Bicicleta", por_usuario[ganhador_id].mensagem)
        self.assertEqual(por_usuario[perdedor_id].tipo, "sorteio_resultado")

    def test_morador_ve_e_marca_apenas_os_proprios_avisos(self):
        sorteio, outro, _ = self._sorteio_apurado()

        meus = listar_minhas_notificacoes(self.session, self.usuario)
        self.assertEqual(len(meus), 1)
        self.assertFalse(meus[0].lida)

        marcar_minha_notificacao_como_lida(meus[0].id, self.session, self.usuario)
        self.assertTrue(self.session.get(Notificacao, meus[0].id).lida)

        aviso_do_outro = self.session.query(Notificacao).filter(Notificacao.usuario_id == outro.id).one()
        with self.assertRaises(HTTPException) as erro:
            marcar_minha_notificacao_como_lida(aviso_do_outro.id, self.session, self.usuario)
        self.assertEqual(erro.exception.status_code, 404)

    def test_avisos_de_morador_nao_aparecem_no_painel_operacional(self):
        self._sorteio_apurado()
        alertas = listar_notificacoes_nao_lidas(None, self.session, self._admin_obj)
        self.assertEqual(alertas, [])


if __name__ == "__main__":
    unittest.main()

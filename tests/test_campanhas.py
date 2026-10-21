import unittest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app  # noqa: F401 - registra todos os modelos no metadata
from app.models.campanha import Campanha, CampanhaRequisito
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.usuario import Usuario
from app.routes.campanha import (
    obter_campanha,
    participar_campanha,
    progresso_campanha,
    receber_recompensa_campanha,
)
from app.schemas.campanha import RequisitoInput
from app.services import campanha_service

COCA = "7894900011517"


class CampanhaTestCase(unittest.TestCase):
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
            pontuacao_total=0,
        )
        self.session.add(self.usuario)
        self.session.flush()
        self.agora = datetime.now(timezone.utc)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _campanha(self, requisitos=(), **kwargs) -> Campanha:
        dados = {
            "titulo": "Campanha Teste",
            "patrocinador": "Parceiro",
            "pontos_recompensa": 0,
            "status": "ativa",
        }
        dados.update(kwargs)
        campanha = Campanha(**dados)
        campanha.requisitos = [CampanhaRequisito(**r) for r in requisitos]
        self.session.add(campanha)
        self.session.flush()
        return campanha

    def _descarte(self, quantidade=1, quando=None, tipo="lata", codigo=COCA, status="confirmado", inventario=None):
        descarte = Descarte(
            quantidade=quantidade,
            quantidade_confirmada=quantidade if status == "confirmado" else None,
            tipo_residuo=tipo,
            status=status,
            usuario_id=self.usuario.id,
            codigo_barras_validado=codigo,
            data_desc=quando or (self.agora - timedelta(days=1)),
            inventario_usuario_id=inventario,
        )
        self.session.add(descarte)
        self.session.flush()
        return descarte

    def _lata_coca(self, quantidade):
        return {"papel": "missao", "tipo_residuo": "lata", "codigos_barras": [COCA], "quantidade": quantidade}

    def _apos_adesao(self):
        return datetime.now(timezone.utc) + timedelta(hours=1)

    # --- detalhe ---------------------------------------------------------

    def test_detalhe_retorna_acesso_condicoes_e_requisitos(self):
        campanha = self._campanha(
            acesso="privada",
            condicoes="Descartar 5 latas.",
            requisitos=[{**self._lata_coca(5), "papel": "entrada"}],
        )

        resposta = obter_campanha(campanha.id, self.session)

        self.assertEqual(resposta.acesso, "privada")
        self.assertEqual(resposta.condicoes, "Descartar 5 latas.")
        self.assertEqual(resposta.requisitos[0].codigos_barras, [COCA])

    def test_detalhe_nao_expoe_campanha_inativa_nem_encerrada(self):
        inativa = self._campanha(status="inativa")
        encerrada = self._campanha(data_fim=self.agora - timedelta(days=1))
        futura = self._campanha(data_inicio=self.agora + timedelta(days=1))

        for campanha in (inativa, encerrada, futura):
            with self.assertRaises(HTTPException) as erro:
                obter_campanha(campanha.id, self.session)
            self.assertEqual(erro.exception.status_code, 404)

    # --- adesao ----------------------------------------------------------

    def test_adesao_publica_e_gratuita_e_nao_credita_pontos(self):
        campanha = self._campanha(pontos_recompensa=50, requisitos=[self._lata_coca(3)])

        inscricao = participar_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(inscricao.pontos_concedidos, 0)
        self.assertEqual(self.usuario.pontuacao_total, 0)

    def test_adesao_repetida_e_rejeitada(self):
        campanha = self._campanha()
        participar_campanha(campanha.id, self.session, self.usuario)

        with self.assertRaises(HTTPException) as erro:
            participar_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(erro.exception.status_code, 400)

    def test_campanha_privada_aceita_adesao_mas_so_libera_bonus_apos_a_entrada(self):
        campanha = self._campanha(
            acesso="privada",
            pontos_recompensa=80,
            requisitos=[{**self._lata_coca(5), "papel": "entrada"}, self._lata_coca(1)],
        )
        self._descarte(quantidade=9)  # antes de participar: nao conta para nada

        participar_campanha(campanha.id, self.session, self.usuario)
        estado = progresso_campanha(campanha.id, self.session, self.usuario)
        self.assertTrue(estado["participando"])
        self.assertEqual(estado["entrada"][0]["atual"], 0)
        self.assertFalse(estado["acesso_liberado"])

        # missao cumprida, mas a entrada ainda nao: sem recompensa
        self._descarte(quantidade=1, quando=self._apos_adesao())
        self.assertFalse(progresso_campanha(campanha.id, self.session, self.usuario)["recompensa_disponivel"])
        with self.assertRaises(HTTPException) as bloqueada:
            receber_recompensa_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(bloqueada.exception.status_code, 403)
        self.assertEqual(self.usuario.pontuacao_total, 0)

        self._descarte(quantidade=4, quando=self._apos_adesao())
        estado = progresso_campanha(campanha.id, self.session, self.usuario)
        self.assertTrue(estado["acesso_liberado"])
        inscricao = receber_recompensa_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(inscricao.pontos_concedidos, 80)
        self.assertEqual(self.usuario.pontuacao_total, 80)

    def test_sem_adesao_nenhum_requisito_acumula_progresso(self):
        campanha = self._campanha(
            acesso="privada",
            requisitos=[{**self._lata_coca(2), "papel": "entrada"}, self._lata_coca(2)],
        )
        self._descarte(quantidade=5, quando=self._apos_adesao())

        estado = progresso_campanha(campanha.id, self.session, self.usuario)

        self.assertFalse(estado["participando"])
        self.assertEqual(estado["entrada"][0]["atual"], 0)
        self.assertEqual(estado["missoes"][0]["atual"], 0)
        self.assertTrue(estado["pode_participar"])

    def test_requisito_ignora_descarte_pendente_de_outro_produto_e_fora_da_vigencia(self):
        campanha = self._campanha(
            acesso="privada",
            data_inicio=self.agora - timedelta(days=10),
            requisitos=[{**self._lata_coca(2), "papel": "entrada"}],
        )
        participar_campanha(campanha.id, self.session, self.usuario)
        depois = self._apos_adesao()
        self._descarte(quantidade=1, status="pendente", quando=depois)
        self._descarte(quantidade=1, codigo="7891000100103", quando=depois)
        self._descarte(quantidade=1, tipo="vidro", quando=depois)
        self._descarte(quantidade=1, quando=self.agora - timedelta(days=30))

        estado = progresso_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(estado["entrada"][0]["atual"], 0)
        self.assertFalse(estado["acesso_liberado"])

    def test_codigo_de_barras_vem_do_item_do_inventario(self):
        item = InventarioUsuario(usuario_id=self.usuario.id, tipo_residuo="lata", quantidade=3, codigo_barras=COCA)
        self.session.add(item)
        self.session.flush()
        campanha = self._campanha(
            acesso="privada",
            requisitos=[{**self._lata_coca(3), "papel": "entrada"}],
        )
        participar_campanha(campanha.id, self.session, self.usuario)
        self._descarte(quantidade=3, codigo=None, inventario=item.id, quando=self._apos_adesao())

        estado = progresso_campanha(campanha.id, self.session, self.usuario)

        self.assertTrue(estado["entrada_cumprida"])
        self.assertTrue(estado["acesso_liberado"])

    # --- missoes e recompensa -------------------------------------------

    def test_missao_so_conta_descarte_depois_da_adesao(self):
        campanha = self._campanha(pontos_recompensa=50, requisitos=[self._lata_coca(2)])
        self._descarte(quantidade=5)  # antes de participar: nao conta
        participar_campanha(campanha.id, self.session, self.usuario)

        antes = progresso_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(antes["missoes"][0]["atual"], 0)

        self._descarte(quantidade=2, quando=self._apos_adesao())
        depois = progresso_campanha(campanha.id, self.session, self.usuario)
        self.assertTrue(depois["missoes_cumpridas"])
        self.assertTrue(depois["recompensa_disponivel"])

    def test_missao_nao_conta_descarte_anterior_a_adesao_mesmo_com_vigencia_aberta(self):
        campanha = self._campanha(
            pontos_recompensa=10,
            data_inicio=self.agora - timedelta(days=60),
            requisitos=[self._lata_coca(1)],
        )
        self._descarte(quantidade=3, quando=self.agora - timedelta(days=5))
        participar_campanha(campanha.id, self.session, self.usuario)

        estado = progresso_campanha(campanha.id, self.session, self.usuario)

        self.assertFalse(estado["recompensa_disponivel"])

    def test_quem_nao_participa_nao_recebe_bonus(self):
        campanha = self._campanha(pontos_recompensa=50, requisitos=[self._lata_coca(1)])
        self._descarte(quantidade=3, quando=self._apos_adesao())

        with self.assertRaises(HTTPException) as erro:
            receber_recompensa_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(erro.exception.status_code, 403)
        self.assertEqual(self.usuario.pontuacao_total, 0)

    def test_recompensa_exige_missoes_completas_e_paga_uma_unica_vez(self):
        campanha = self._campanha(pontos_recompensa=50, requisitos=[self._lata_coca(2)])
        participar_campanha(campanha.id, self.session, self.usuario)
        self._descarte(quantidade=1, quando=self._apos_adesao())

        with self.assertRaises(HTTPException) as incompleta:
            receber_recompensa_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(incompleta.exception.status_code, 400)
        self.assertEqual(self.usuario.pontuacao_total, 0)

        self._descarte(quantidade=1, quando=self._apos_adesao())
        inscricao = receber_recompensa_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(inscricao.pontos_concedidos, 50)
        self.assertEqual(self.usuario.pontuacao_total, 50)

        with self.assertRaises(HTTPException) as repetida:
            receber_recompensa_campanha(campanha.id, self.session, self.usuario)
        self.assertEqual(repetida.exception.status_code, 400)
        self.assertEqual(self.usuario.pontuacao_total, 50)

    # --- definicao -------------------------------------------------------

    def test_definicao_invalida_e_rejeitada(self):
        entrada = RequisitoInput(papel="entrada", quantidade=1)
        missao = RequisitoInput(papel="missao", quantidade=1)
        casos = [
            ("privada", 0, []),  # privada sem entrada
            ("publica", 0, [entrada]),  # entrada em campanha publica
            ("publica", 30, []),  # paga pontos sem missao
        ]
        for acesso, pontos, requisitos in casos:
            with self.assertRaises(HTTPException) as erro:
                campanha_service.validar_definicao(acesso, pontos, requisitos)
            self.assertEqual(erro.exception.status_code, 400)

        campanha_service.validar_definicao("publica", 30, [missao])
        campanha_service.validar_definicao("privada", 30, [entrada, missao])


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app  # noqa: F401 - registra todos os modelos no metadata
from app.models.campanha import Campanha
from app.models.usuario import Usuario
from app.routes.campanha import obter_campanha, participar_campanha


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

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _campanha(self, **kwargs) -> Campanha:
        dados = {
            "titulo": "Campanha Teste",
            "patrocinador": "Parceiro",
            "pontos_recompensa": 50,
            "status": "ativa",
        }
        dados.update(kwargs)
        campanha = Campanha(**dados)
        self.session.add(campanha)
        self.session.flush()
        return campanha

    def test_detalhe_retorna_campos_informativos(self):
        campanha = self._campanha(
            produto_elegivel="Lata de alumínio",
            meta_quantidade=20,
            condicoes="Descartar 20 latas no período.",
        )

        resposta = obter_campanha(campanha.id, self.session)

        self.assertEqual(resposta.produto_elegivel, "Lata de alumínio")
        self.assertEqual(resposta.meta_quantidade, 20)
        self.assertEqual(resposta.condicoes, "Descartar 20 latas no período.")

    def test_detalhe_nao_expoe_campanha_inativa_nem_encerrada(self):
        agora = datetime.now(timezone.utc)
        inativa = self._campanha(status="inativa")
        encerrada = self._campanha(data_fim=agora - timedelta(days=1))
        futura = self._campanha(data_inicio=agora + timedelta(days=1))

        for campanha in (inativa, encerrada, futura):
            with self.assertRaises(HTTPException) as erro:
                obter_campanha(campanha.id, self.session)
            self.assertEqual(erro.exception.status_code, 404)

    def test_adesao_credita_pontos_por_padrao(self):
        campanha = self._campanha()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CAMPANHA_BONUS_NA_ADESAO", None)
            inscricao = participar_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(inscricao.pontos_concedidos, 50)
        self.assertEqual(self.usuario.pontuacao_total, 50)

    def test_adesao_sem_bonus_quando_desligado_por_configuracao(self):
        campanha = self._campanha()

        with patch.dict(os.environ, {"CAMPANHA_BONUS_NA_ADESAO": "false"}):
            inscricao = participar_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(inscricao.pontos_concedidos, 0)
        self.assertEqual(self.usuario.pontuacao_total, 0)

    def test_adesao_repetida_e_rejeitada_sem_novo_credito(self):
        campanha = self._campanha()
        participar_campanha(campanha.id, self.session, self.usuario)

        with self.assertRaises(HTTPException) as erro:
            participar_campanha(campanha.id, self.session, self.usuario)

        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(self.usuario.pontuacao_total, 50)


if __name__ == "__main__":
    unittest.main()

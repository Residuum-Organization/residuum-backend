import unittest

from pydantic import ValidationError

from app.schemas.descarte import DescarteCreate
from app.schemas.inventario_usuario import InventarioLoteTransferir, InventarioUsuarioCreate
from app.services.identificacao_residuo_service import validar_identificacao_confirmacao
from app.services.transferencia_lote_service import calcular_status_lote


class CadastroIdentificacaoTestCase(unittest.TestCase):
    def test_preserva_zeros_a_esquerda_do_codigo(self):
        item = InventarioUsuarioCreate(
            tipo_residuo="plastico",
            quantidade=1,
            codigo_barras=" 07891234567890 ",
        )
        self.assertEqual(item.codigo_barras, "07891234567890")
        self.assertFalse(item.sem_rotulo)

    def test_aceita_embalagem_sem_rotulo_sem_codigo(self):
        item = InventarioUsuarioCreate(
            tipo_residuo="plastico",
            quantidade=1,
            sem_rotulo=True,
        )
        self.assertIsNone(item.codigo_barras)

    def test_exige_codigo_quando_item_tem_rotulo(self):
        with self.assertRaises(ValidationError):
            InventarioUsuarioCreate(tipo_residuo="plastico", quantidade=1)

    def test_rejeita_codigo_em_embalagem_sem_rotulo(self):
        with self.assertRaises(ValidationError):
            InventarioUsuarioCreate(
                tipo_residuo="plastico",
                quantidade=1,
                codigo_barras="123",
                sem_rotulo=True,
            )


class ConfirmacaoIdentificacaoTestCase(unittest.TestCase):
    def test_confirma_codigo_correspondente(self):
        resultado = validar_identificacao_confirmacao(
            codigo_cadastrado="00123",
            item_sem_rotulo=False,
            codigo_validado="00123",
            confirmado_sem_rotulo=False,
            identificacao_manual=None,
        )
        self.assertEqual(resultado, ("00123", False, None))

    def test_rejeita_codigo_diferente(self):
        with self.assertRaisesRegex(ValueError, "não corresponde"):
            validar_identificacao_confirmacao(
                codigo_cadastrado="00123",
                item_sem_rotulo=False,
                codigo_validado="00124",
                confirmado_sem_rotulo=False,
                identificacao_manual=None,
            )

    def test_exige_descricao_manual_para_item_sem_rotulo(self):
        with self.assertRaisesRegex(ValueError, "Descreva manualmente"):
            validar_identificacao_confirmacao(
                codigo_cadastrado=None,
                item_sem_rotulo=True,
                codigo_validado=None,
                confirmado_sem_rotulo=True,
                identificacao_manual=" ",
            )

    def test_confirma_identificacao_manual(self):
        resultado = validar_identificacao_confirmacao(
            codigo_cadastrado=None,
            item_sem_rotulo=True,
            codigo_validado=None,
            confirmado_sem_rotulo=True,
            identificacao_manual=" Garrafa plástica transparente ",
        )
        self.assertEqual(resultado, (None, True, "Garrafa plástica transparente"))


class ContratoTransferenciaTestCase(unittest.TestCase):
    def test_rejeita_qrcode_no_descarte(self):
        with self.assertRaises(ValidationError):
            DescarteCreate(
                quantidade=1,
                tipo_residuo="plastico",
                usuario_lat=-3.0,
                usuario_long=-60.0,
                ponto_coleta_id=1,
                qrcode_token="token-antigo",
            )

    def test_calcula_status_parcial_quando_lote_tem_rejeicao(self):
        self.assertEqual(calcular_status_lote(["confirmado", "rejeitado"]), "parcial")

    def test_mantem_lote_pendente_ate_finalizar_todos_itens(self):
        self.assertEqual(calcular_status_lote(["confirmado", "pendente"]), "pendente")

    def test_rejeita_item_duplicado_no_lote(self):
        with self.assertRaises(ValidationError):
            InventarioLoteTransferir(
                itens=[
                    {"item_id": 1, "quantidade": 1},
                    {"item_id": 1, "quantidade": 1},
                ],
                ponto_coleta_id=1,
                usuario_lat=-3.0,
                usuario_long=-60.0,
                chave_idempotencia="transferencia-123",
            )


if __name__ == "__main__":
    unittest.main()

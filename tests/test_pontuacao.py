import unittest

from app.services.pontuacao_service import PONTOS_POR_UNIDADE, calcular_pontos_proporcionais


class PontuacaoTestCase(unittest.TestCase):
    def test_uma_unidade_vale_cinco_pontos(self):
        self.assertEqual(PONTOS_POR_UNIDADE, 5)
        self.assertEqual(calcular_pontos_proporcionais(1, 1), 5)

    def test_faixas_de_recompensa_batem_com_os_descartes(self):
        # Tabela inicial: 10 pontos = 2 descartes, 25 = 5, 100 = 20, 1.000 = 200.
        for descartes, pontos in ((2, 10), (5, 25), (10, 50), (20, 100), (50, 250), (100, 500), (200, 1000)):
            self.assertEqual(calcular_pontos_proporcionais(descartes, descartes), pontos)

    def test_usa_a_quantidade_confirmada(self):
        self.assertEqual(calcular_pontos_proporcionais(4, 2), 10)

    def test_quantidade_invalida_nao_pontua(self):
        self.assertEqual(calcular_pontos_proporcionais(0, 3), 0)
        self.assertEqual(calcular_pontos_proporcionais(3, -1), 0)


if __name__ == "__main__":
    unittest.main()

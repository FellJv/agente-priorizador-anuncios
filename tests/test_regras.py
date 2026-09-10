"""Testes das regras de diagnóstico e da trava de aprovação.

Rodar com:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import aprovacao
import regras


def anuncio(**alteracoes):
    """Anúncio saudável, usado como base. Cada teste altera só o que importa."""
    base = {
        "sku": "SKU-0000",
        "anuncio_id": "ANUN-0000",
        "titulo": "Molinete de pesca 5000 com carretel de fibra e 5 rolamentos",
        "fotos": 6,
        "atributos_preenchidos": 12,
        "atributos_totais": 12,
        "visitas_30d": 500,
        "vendas_30d": 20,
        "estoque": 50,
    }
    base.update(alteracoes)
    return base


class TestCalculoDePrioridade(unittest.TestCase):
    def test_formula_conhecida(self):
        # (5 * 1.0) / (1 + 1) * 10 = 25.0
        self.assertEqual(regras.calcular_prioridade(5, 1, 1.0, 1), 25.0)

    def test_mais_impacto_gera_mais_prioridade(self):
        baixo = regras.calcular_prioridade(2, 2, 0.9, 2)
        alto = regras.calcular_prioridade(5, 2, 0.9, 2)
        self.assertGreater(alto, baixo)

    def test_mais_esforco_reduz_prioridade(self):
        barato = regras.calcular_prioridade(5, 1, 0.9, 1)
        caro = regras.calcular_prioridade(5, 5, 0.9, 1)
        self.assertLess(caro, barato)

    def test_mais_risco_reduz_prioridade(self):
        seguro = regras.calcular_prioridade(5, 2, 0.9, 1)
        arriscado = regras.calcular_prioridade(5, 2, 0.9, 5)
        self.assertLess(arriscado, seguro)

    def test_confianca_invalida(self):
        with self.assertRaises(ValueError):
            regras.calcular_prioridade(5, 2, 1.5, 1)

    def test_esforco_zero(self):
        with self.assertRaises(ValueError):
            regras.calcular_prioridade(5, 0, 0.9, 1)


class TestDiagnostico(unittest.TestCase):
    def codigos(self, alvo):
        return {a["codigo"] for a in regras.diagnosticar(alvo)}

    def test_anuncio_saudavel_nao_gera_achado(self):
        self.assertEqual(regras.diagnosticar(anuncio()), [])

    def test_titulo_curto(self):
        self.assertIn("TITULO_CURTO", self.codigos(anuncio(titulo="Vara de pesca")))

    def test_ficha_tecnica_incompleta(self):
        self.assertIn("SEM_FICHA_TECNICA", self.codigos(anuncio(atributos_preenchidos=4)))

    def test_poucas_fotos(self):
        self.assertIn("POUCAS_FOTOS", self.codigos(anuncio(fotos=2)))

    def test_visita_sem_venda_e_conversao_baixa(self):
        self.assertIn("CONVERSAO_BAIXA", self.codigos(anuncio(visitas_30d=800, vendas_30d=0)))

    def test_sem_visita_nao_e_conversao_baixa(self):
        # Anúncio sem tráfego tem outro problema: não está sendo encontrado.
        achados = self.codigos(anuncio(visitas_30d=5, vendas_30d=0))
        self.assertIn("SEM_VISITA", achados)
        self.assertNotIn("CONVERSAO_BAIXA", achados)

    def test_estoque_critico(self):
        self.assertIn("ESTOQUE_CRITICO", self.codigos(anuncio(vendas_30d=30, estoque=4)))

    def test_estoque_parado_nao_e_critico(self):
        # Sem venda no período, estoque baixo não é urgência de reposição.
        self.assertNotIn("ESTOQUE_CRITICO", self.codigos(anuncio(vendas_30d=0, estoque=1, visitas_30d=500)))


class TestPriorizacao(unittest.TestCase):
    def test_ordena_do_maior_para_o_menor(self):
        ruim = anuncio(sku="SKU-9999", titulo="Rede", fotos=1, atributos_preenchidos=1,
                       visitas_30d=3, vendas_30d=0)
        fila = regras.priorizar(regras.diagnosticar(ruim))
        notas = [item["prioridade"] for item in fila]
        self.assertEqual(notas, sorted(notas, reverse=True))


class TestTravaDeAprovacao(unittest.TestCase):
    def item(self):
        achados = regras.diagnosticar(anuncio(titulo="Vara de pesca"))
        return aprovacao.montar_fila(achados)[0]

    def test_item_nasce_pendente(self):
        self.assertEqual(self.item()["status"], aprovacao.STATUS_PENDENTE)

    def test_execucao_bloqueada_sem_aprovacao(self):
        with self.assertRaises(PermissionError):
            aprovacao.executar(self.item())

    def test_execucao_bloqueada_apos_rejeicao(self):
        item = aprovacao.registrar_decisao(self.item(), aprovado=False, responsavel="Revisor")
        with self.assertRaises(PermissionError):
            aprovacao.executar(item)

    def test_execucao_liberada_apos_aprovacao(self):
        item = aprovacao.registrar_decisao(self.item(), aprovado=True, responsavel="Revisor")
        self.assertIn("[simulado]", aprovacao.executar(item))

    def test_decisao_exige_responsavel(self):
        with self.assertRaises(ValueError):
            aprovacao.registrar_decisao(self.item(), aprovado=True, responsavel="")

    def test_decisao_guarda_quem_e_quando(self):
        item = aprovacao.registrar_decisao(self.item(), aprovado=True, responsavel="Revisor")
        self.assertEqual(item["decidido_por"], "Revisor")
        self.assertIsNotNone(item["decidido_em"])


if __name__ == "__main__":
    unittest.main()

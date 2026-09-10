"""Regras de diagnóstico e priorização de anúncios.

Este módulo é o núcleo do agente e não conversa com nenhum sistema externo:
entra um anúncio (dicionário), saem os problemas encontrados e a prioridade.

Manter as regras separadas do restante do código tem um motivo prático:
é a parte que precisa de teste automatizado, porque é ela que decide o que
uma pessoa vai revisar primeiro.
"""

# Pesos usados no cálculo de prioridade.
# impacto e confianca aumentam a prioridade; esforco e risco reduzem.
PESOS = {
    "impacto": 1.0,
    "confianca": 1.0,
    "esforco": 1.0,
    "risco": 1.0,
}

# Cada regra descreve um problema que sabemos diagnosticar.
#
# impacto   -> quanto a correção tende a mexer no resultado (1 a 5)
# esforco   -> quanto custa corrigir (1 a 5)
# confianca -> quanto confiamos no diagnóstico (0.0 a 1.0)
# risco     -> risco de a correção causar dano (1 a 5)
REGRAS = [
    {
        "codigo": "TITULO_CURTO",
        "descricao": "Título com menos de 40 caracteres: perde termos de busca.",
        "acao": "Reescrever o título incluindo tipo de produto, medida e material.",
        "impacto": 5,
        "esforco": 1,
        "confianca": 0.95,
        "risco": 1,
        "teste": lambda a: len(a["titulo"]) < 40,
    },
    {
        "codigo": "SEM_FICHA_TECNICA",
        "descricao": "Atributos obrigatórios da categoria não preenchidos.",
        "acao": "Preencher a ficha técnica: marca, modelo, medida e material.",
        "impacto": 5,
        "esforco": 2,
        "confianca": 0.9,
        "risco": 1,
        "teste": lambda a: a["atributos_preenchidos"] < a["atributos_totais"],
    },
    {
        "codigo": "POUCAS_FOTOS",
        "descricao": "Menos de 4 fotos: reduz conversão e qualidade do anúncio.",
        "acao": "Subir fotos adicionais, incluindo escala e detalhe do produto.",
        "impacto": 4,
        "esforco": 3,
        "confianca": 0.85,
        "risco": 1,
        "teste": lambda a: a["fotos"] < 4,
    },
    {
        "codigo": "CONVERSAO_BAIXA",
        "descricao": "Recebe visitas mas não vende: problema de oferta, não de tráfego.",
        "acao": "Revisar preço, frete e descrição antes de investir em anúncio pago.",
        "impacto": 5,
        "esforco": 3,
        "confianca": 0.7,
        "risco": 3,
        "teste": lambda a: a["visitas_30d"] >= 100 and a["vendas_30d"] == 0,
    },
    {
        "codigo": "SEM_VISITA",
        "descricao": "Quase sem visitas: o anúncio não está sendo encontrado.",
        "acao": "Revisar categoria e título; conferir se o anúncio está ativo e completo.",
        "impacto": 3,
        "esforco": 2,
        "confianca": 0.6,
        "risco": 1,
        "teste": lambda a: a["visitas_30d"] < 20,
    },
    {
        "codigo": "ESTOQUE_CRITICO",
        "descricao": "Estoque insuficiente para a média de vendas do período.",
        "acao": "Sinalizar reposição antes da ruptura; evitar pausa do anúncio.",
        "impacto": 4,
        "esforco": 2,
        "confianca": 0.9,
        "risco": 2,
        "teste": lambda a: a["vendas_30d"] > 0 and a["estoque"] < a["vendas_30d"],
    },
]


def calcular_prioridade(impacto, esforco, confianca, risco):
    """Converte impacto, esforço, confiança e risco em uma nota de prioridade.

    A fórmula é deliberadamente simples e legível: quem revisa precisa
    entender por que um item ficou na frente do outro.

        prioridade = (impacto * confianca) / (esforco + risco)

    O resultado é multiplicado por 10 apenas para a leitura ficar mais
    confortável, e arredondado em duas casas.
    """
    if esforco <= 0 or risco <= 0:
        raise ValueError("esforco e risco precisam ser maiores que zero")
    if not 0 <= confianca <= 1:
        raise ValueError("confianca precisa estar entre 0 e 1")

    numerador = impacto * PESOS["impacto"] * confianca * PESOS["confianca"]
    denominador = esforco * PESOS["esforco"] + risco * PESOS["risco"]
    return round((numerador / denominador) * 10, 2)


def diagnosticar(anuncio):
    """Aplica todas as regras a um anúncio e devolve a lista de achados.

    Cada achado carrega a nota de prioridade e o motivo, para que a decisão
    apresentada a uma pessoa seja auditável.
    """
    achados = []
    for regra in REGRAS:
        if not regra["teste"](anuncio):
            continue
        achados.append({
            "sku": anuncio["sku"],
            "anuncio_id": anuncio["anuncio_id"],
            "codigo": regra["codigo"],
            "descricao": regra["descricao"],
            "acao_sugerida": regra["acao"],
            "impacto": regra["impacto"],
            "esforco": regra["esforco"],
            "confianca": regra["confianca"],
            "risco": regra["risco"],
            "prioridade": calcular_prioridade(
                regra["impacto"], regra["esforco"], regra["confianca"], regra["risco"]
            ),
        })
    return achados


def priorizar(achados):
    """Ordena os achados: prioridade maior primeiro, empate resolvido pelo SKU."""
    return sorted(achados, key=lambda a: (-a["prioridade"], a["sku"], a["codigo"]))

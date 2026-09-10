"""Agente priorizador de anúncios — ponto de entrada.

Fluxo: lê os dados, diagnostica, prioriza, monta a fila de aprovação e
imprime o relatório. Nada é alterado em sistema externo.

Uso:
    python src/agente.py
    python src/agente.py --dados dados/anuncios_exemplo.csv --top 5
    python src/agente.py --aprovar-tudo "Jose Victor"   # simula a decisão humana
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aprovacao
import regras

CAMPOS_NUMERICOS = [
    "fotos", "atributos_preenchidos", "atributos_totais",
    "visitas_30d", "vendas_30d", "estoque",
]


def carregar(caminho):
    """Lê o CSV de anúncios e converte os campos numéricos.

    Uma linha malformada não derruba a execução: ela é reportada e ignorada,
    porque um dado ruim não deve impedir o diagnóstico dos demais.
    """
    anuncios, problemas = [], []
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for numero, linha in enumerate(csv.DictReader(arquivo), start=2):
            try:
                for campo in CAMPOS_NUMERICOS:
                    linha[campo] = int(linha[campo])
                anuncios.append(linha)
            except (ValueError, KeyError, TypeError) as erro:
                problemas.append(f"linha {numero}: {erro}")
    return anuncios, problemas


def relatorio(fila, total_anuncios, top):
    linhas = []
    linhas.append("=" * 78)
    linhas.append("FILA DE TRABALHO SUGERIDA — aguardando revisão humana")
    linhas.append("=" * 78)
    linhas.append(f"Anúncios analisados: {total_anuncios}")
    linhas.append(f"Achados priorizados: {len(fila)}")
    linhas.append("")

    if not fila:
        linhas.append("Nenhum problema encontrado com as regras atuais.")
        return "\n".join(linhas)

    for item in fila[:top]:
        linhas.append(f"#{item['item_id']}  prioridade {item['prioridade']}  [{item['status']}]")
        linhas.append(f"    SKU {item['sku']}  ·  {item['anuncio_id']}  ·  {item['codigo']}")
        linhas.append(f"    Problema: {item['descricao']}")
        linhas.append(f"    Ação sugerida: {item['acao_sugerida']}")
        linhas.append(
            f"    Por que nesta posição: impacto {item['impacto']}, "
            f"esforço {item['esforco']}, confiança {item['confianca']}, "
            f"risco {item['risco']}"
        )
        linhas.append("")

    if len(fila) > top:
        linhas.append(f"... e outros {len(fila) - top} achados de prioridade menor.")
        linhas.append("")

    linhas.append("-" * 78)
    linhas.append("Nenhuma alteração foi aplicada. O agente analisa e recomenda;")
    linhas.append("a decisão e a execução dependem de aprovação humana registrada.")
    return "\n".join(linhas)


def main():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="Agente priorizador de anúncios")
    parser.add_argument("--dados", default=os.path.join(raiz, "dados", "anuncios_exemplo.csv"))
    parser.add_argument("--top", type=int, default=5, help="quantos achados detalhar")
    parser.add_argument("--aprovar-tudo", metavar="RESPONSAVEL",
                        help="simula a aprovação humana de todos os itens")
    parser.add_argument("--log", default=os.path.join(raiz, "saida", "auditoria.jsonl"))
    args = parser.parse_args()

    anuncios, problemas = carregar(args.dados)
    for aviso in problemas:
        print(f"[dado ignorado] {aviso}", file=sys.stderr)

    achados = []
    for anuncio in anuncios:
        achados.extend(regras.diagnosticar(anuncio))

    fila = aprovacao.montar_fila(regras.priorizar(achados))
    print(relatorio(fila, len(anuncios), args.top))

    if args.aprovar_tudo:
        print()
        print(f"Aprovação registrada por: {args.aprovar_tudo}")
        for item in fila:
            aprovacao.registrar_decisao(item, aprovado=True, responsavel=args.aprovar_tudo)
        for item in fila[:args.top]:
            print("   ", aprovacao.executar(item))

    caminho = aprovacao.gravar_log(fila, args.log)
    print()
    print(f"Trilha de auditoria: {os.path.relpath(caminho, raiz)}")


if __name__ == "__main__":
    main()

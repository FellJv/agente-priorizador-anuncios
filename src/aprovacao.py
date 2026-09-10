"""Fila de aprovação e trilha de auditoria.

Este módulo existe para deixar explícito o limite do agente: ele monta a fila
e registra o que foi decidido. A alteração real no marketplace acontece só
depois de uma aprovação registrada — e, neste repositório de portfólio,
não acontece de forma alguma, porque não há integração de escrita.
"""

import json
import os
from datetime import datetime, timezone

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_REJEITADO = "rejeitado"


def _agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def montar_fila(achados):
    """Transforma os achados em itens de fila, todos pendentes de decisão."""
    fila = []
    for i, achado in enumerate(achados, start=1):
        item = dict(achado)
        item["item_id"] = i
        item["status"] = STATUS_PENDENTE
        item["decidido_por"] = None
        item["decidido_em"] = None
        fila.append(item)
    return fila


def registrar_decisao(item, aprovado, responsavel):
    """Registra a decisão humana sobre um item da fila.

    Não recebe valor padrão para `responsavel` de propósito: decisão sem
    responsável identificado não serve como trilha de auditoria.
    """
    if not responsavel:
        raise ValueError("toda decisão precisa de um responsável identificado")

    item["status"] = STATUS_APROVADO if aprovado else STATUS_REJEITADO
    item["decidido_por"] = responsavel
    item["decidido_em"] = _agora()
    return item


def executar(item):
    """Ponto único onde uma alteração externa poderia ser aplicada.

    Duas travas propositais:

    1. Item sem aprovação registrada nunca chega à execução.
    2. Este repositório é uma implementação de referência e não integra
       escrita em nenhum sistema externo, então a função apenas descreve
       o que seria feito.
    """
    if item.get("status") != STATUS_APROVADO:
        raise PermissionError(
            "execução bloqueada: item sem aprovação humana registrada "
            f"(status atual: {item.get('status')})"
        )
    return (
        f"[simulado] aplicaria em {item['anuncio_id']} (SKU {item['sku']}): "
        f"{item['acao_sugerida']}"
    )


def gravar_log(fila, caminho):
    """Grava a trilha de auditoria em JSON, uma linha por evento."""
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        for item in fila:
            arquivo.write(json.dumps(item, ensure_ascii=False) + "\n")
    return caminho

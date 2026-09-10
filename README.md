# Agente priorizador de anúncios

Implementação de referência de um agente que analisa anúncios de marketplace,
diagnostica problemas, prioriza as correções e entrega uma **fila de trabalho
revisada por uma pessoa** — em vez de um relatório que ninguém lê ou de uma
automação que altera as coisas por conta própria.

Este repositório é o meu portfólio: reproduz o raciocínio e a arquitetura dos
agentes que desenvolvo no dia a dia, com dados fictícios e sem nenhuma
integração de escrita. Os projetos completos estão em repositório privado.

**Autor:** José Victor Pereira Lança — assistente de e-commerce na Riomar Equipesca
e estudante de Engenharia da Computação na Univesp.
[LinkedIn](https://www.linkedin.com/in/felljv/) · fell123shi@gmail.com

---

## O problema

Uma operação de e-commerce com centenas de anúncios ativos gera mais sinal do
que qualquer pessoa consegue ler. Os painéis dos marketplaces mostram métricas
por anúncio, mas não respondem a pergunta que importa numa segunda-feira:

> Tenho duas horas hoje. Quais anúncios eu conserto primeiro?

Sem essa resposta, a correção acontece por impressão — o anúncio que alguém
lembrou, o que um cliente reclamou. Os problemas mais caros ficam invisíveis
justamente porque são silenciosos: o anúncio que recebe 1.500 visitas e não
vende nenhuma unidade não aparece em lugar nenhum como urgência.

## A abordagem

O agente não tenta adivinhar o que fazer. Ele aplica regras explícitas, atribui
uma nota de prioridade a cada achado e explica por que aquele item ficou na
frente dos outros. Quem revisa consegue discordar — e discordar é a parte
importante, porque é ela que corrige as regras.

```
dados dos anúncios
        │
        ▼
   diagnóstico            regras explícitas, uma por tipo de problema
        │
        ▼
   priorização            (impacto × confiança) ÷ (esforço + risco)
        │
        ▼
 fila de aprovação        todo item nasce "pendente"
        │
        ▼
  decisão humana  ────────────────► rejeitado (fim, registrado)
        │
        │ aprovado + responsável identificado
        ▼
     execução             ponto único de escrita, bloqueado sem aprovação
        │
        ▼
trilha de auditoria       quem decidiu, o quê e quando
```

### Por que humano no loop

A trava não é enfeite. `aprovacao.executar()` levanta `PermissionError` se o
item não tiver aprovação registrada, e `registrar_decisao()` recusa decisão sem
responsável identificado — decisão anônima não serve como auditoria.

O motivo é prático: em marketplace, uma alteração errada aplicada em massa
custa vendas e reputação, e nem tudo é reversível com um clique. Então o agente
faz o trabalho de análise, que é o caro, e deixa a decisão com quem responde
por ela. É o padrão que uso nos projetos reais.

### Por que essa fórmula de prioridade

```
prioridade = (impacto × confiança) ÷ (esforço + risco) × 10
```

Quatro fatores, escolhidos porque são os que mudam a ordem do trabalho:

| Fator | O que mede | Efeito |
|---|---|---|
| **impacto** | quanto a correção tende a mexer no resultado (1–5) | aumenta |
| **confiança** | quanto o diagnóstico é confiável (0–1) | aumenta |
| **esforço** | quanto custa corrigir (1–5) | reduz |
| **risco** | risco de a correção causar dano (1–5) | reduz |

A fórmula é simples de propósito. Um modelo mais elaborado daria notas melhor
calibradas e ninguém entenderia por que o item 7 está na frente do item 3 — e
uma fila que ninguém entende é uma fila que ninguém segue.

Um caso concreto de como isso ordena o trabalho: título curto tem impacto alto,
esforço baixo e risco baixo, então sobe. Conversão baixa também tem impacto
alto, mas exige revisar preço e frete (esforço maior) e mexer em preço é
arriscado, então desce — mesmo sendo um problema grave.

## Regras implementadas

| Código | Diagnóstico |
|---|---|
| `TITULO_CURTO` | Título com menos de 40 caracteres: perde termos de busca |
| `SEM_FICHA_TECNICA` | Atributos obrigatórios da categoria em branco |
| `POUCAS_FOTOS` | Menos de 4 fotos |
| `CONVERSAO_BAIXA` | Recebe visitas e não vende: problema de oferta, não de tráfego |
| `SEM_VISITA` | Quase sem visitas: o anúncio não está sendo encontrado |
| `ESTOQUE_CRITICO` | Estoque abaixo da média de vendas do período |

Duas regras que parecem iguais e não são: `SEM_VISITA` e `CONVERSAO_BAIXA`.
Anúncio sem tráfego e anúncio com tráfego que não converte têm causas
diferentes e correções diferentes — tratá-los como o mesmo problema é o erro
mais comum aqui. Há teste garantindo que um não seja diagnosticado como o outro.

## Como rodar

Só a biblioteca padrão do Python 3.9+. Sem dependências, sem instalação.

```bash
# fila de trabalho a partir dos dados de exemplo
python src/agente.py

# detalhar mais achados
python src/agente.py --top 10

# simular a decisão humana e ver a trava de execução liberar
python src/agente.py --aprovar-tudo "Seu Nome"

# testes
python -m unittest discover -s tests -v
```

Saída de exemplo: [`exemplos/saida_exemplo.txt`](exemplos/saida_exemplo.txt)

## Estrutura

```
src/regras.py      diagnóstico e cálculo de prioridade — o núcleo, todo testado
src/aprovacao.py   fila, decisão humana, trava de execução e auditoria
src/agente.py      leitura dos dados, relatório e linha de comando
dados/             CSV de exemplo com 10 anúncios fictícios
tests/             21 testes cobrindo as regras e a trava de aprovação
```

O núcleo (`regras.py`) não conhece arquivo, rede nem API: entra um dicionário,
sai a lista de achados. É o que permite testar a decisão sem subir nada e o que
permitiria trocar a fonte de dados — CSV hoje, API amanhã — sem tocar na lógica.

## Limites deste repositório

Ditos com clareza, porque um portfólio que promete mais do que entrega não
serve para avaliação técnica:

- **Não integra escrita em sistema externo.** `executar()` descreve a ação em
  vez de aplicá-la. A integração real exige credenciais, tratamento de erro
  parcial de API, idempotência e paginação — nada disso está aqui.
- **Dados fictícios.** Os 10 anúncios são inventados. Nenhum dado real de
  cliente, fornecedor ou preço, e nenhuma credencial em nenhum ponto do
  histórico.
- **Pesos não calibrados com dados.** Impacto, esforço, confiança e risco vêm
  da minha experiência operando a loja, não de regressão. Calibrar exigiria
  medir o efeito das correções aprovadas ao longo do tempo — que é justamente
  o passo seguinte previsto.
- **Sem interface.** É linha de comando. O painel de revisão existe nos
  projetos privados, não aqui.

## Próximos passos

1. Fechar o ciclo: medir o resultado das correções aprovadas e usar isso para
   recalibrar os pesos, em vez de estimá-los.
2. Teste A/B por regra, para saber quais diagnósticos realmente valem.
3. Fonte de dados plugável (API no lugar do CSV) sem alterar `regras.py`.
4. Painel de revisão da fila, com decisão em lote e histórico por anúncio.

## Licença

MIT — veja [LICENSE](LICENSE).

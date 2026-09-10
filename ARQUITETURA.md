# Arquitetura dos agentes que desenvolvo

Este documento descreve o padrão que aplico nos dois projetos que desenvolvo
em sociedade — **Optimize**, para otimização de anúncios de marketplace, e
**Controle Inteligente de Produção**, para decisão de produção. O código deste
repositório é uma implementação reduzida do mesmo padrão, com dados fictícios.

## O padrão: loop de valor

Nenhum dos dois projetos começou pela tecnologia. Os dois começaram por uma
decisão que estava sendo tomada mal — e a mesma sequência resolve os dois:

1. **Definir o problema e o resultado esperado.** "Quais anúncios corrigir
   primeiro", não "usar IA em marketplace".
2. **Medir a linha de base.** Sem saber como a decisão é tomada hoje, não há
   como afirmar que o agente melhorou algo.
3. **Coletar dado confiável.** Dado incompleto tratado como completo produz
   recomendação confiante e errada, que é o pior resultado possível.
4. **Analisar e recomendar.** Aqui entra o agente.
5. **Validar com uma pessoa.** Aprovação registrada, por item.
6. **Executar de forma controlada**, com limite de volume e rollback.
7. **Registrar a decisão e o resultado.**
8. **Medir o efeito** e realimentar as regras.

O agente ocupa o passo 4. Todo o resto é engenharia em volta dele — e é o resto
que decide se o agente é utilizável ou só uma demonstração.

## Três estágios de autonomia

Nunca coloco um agente para escrever em sistema externo no primeiro dia. A
progressão é:

| Estágio | O que o agente faz | O que a pessoa faz |
|---|---|---|
| **Observação** | analisa e registra o que faria | compara com o que faria e corrige as regras |
| **Recomendação** | entrega a fila priorizada | decide item por item |
| **Autonomia limitada** | executa regras já validadas, dentro de limite | audita a amostra e o log |

O código deste repositório está no estágio de recomendação, que é onde os
projetos reais estão hoje. A autonomia limitada só entra depois que uma regra
específica acumulou histórico de aprovação — e mesmo aí, com teto de volume.

## Decisões de projeto e o motivo de cada uma

**Núcleo puro, sem efeito colateral.** `regras.py` recebe um dicionário e
devolve achados. Não abre arquivo, não chama API, não escreve log. Isso permite
testar a decisão sem infraestrutura, e trocar a fonte de dados sem risco de
alterar o comportamento.

**Fórmula legível em vez de modelo opaco.** Quem revisa precisa poder discordar
da ordem — e a discordância é o que calibra as regras. Um score que ninguém
consegue explicar não recebe discordância, recebe abandono.

**Confiança como fator separado do impacto.** Um diagnóstico certeiro de
problema pequeno e um chute sobre problema grande não podem ter a mesma nota.
Separar os dois deixa explícito quando o agente está inseguro.

**Trava de execução no código, não na documentação.** "Precisa de aprovação"
escrito no README é intenção; `PermissionError` em `executar()` é garantia.

**Falha parcial é falha.** Uma linha de dado malformada é reportada e ignorada,
nunca convertida em zero silencioso — porque zero é um valor válido que dispara
regras e produziria diagnóstico falso.

**Auditoria com responsável identificado.** `registrar_decisao()` recusa
decisão sem responsável. Log sem autor não reconstrói o que aconteceu.

## O que muda nos projetos reais

O que existe nos projetos privados e não está aqui:

- **Integração de leitura** com a API do marketplace e com o ERP: autenticação
  OAuth 2.0, paginação, limite de requisição, retentativa limitada.
- **Integração de escrita**, com idempotência, limite de volume por execução e
  rollback por item.
- **Persistência** do histórico de achados e decisões, para medir o efeito das
  correções e recalibrar os pesos.
- **Painel de revisão** da fila, com decisão em lote.
- **Separação de ambiente e permissão** entre leitura e escrita, e credenciais
  fora do código.

A ordem dessa lista não é acidental: leitura, decisão e auditoria vêm antes da
escrita. Um agente que lê bem e recomenda bem já entrega valor; um que escreve
antes de ser confiável entrega prejuízo.

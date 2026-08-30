# Experimentos

> **Idioma:** Português (Brasil) · [Original em inglês](../EXPERIMENTS.md)

Este documento registra evidência de benchmarks live do Controlled Autonomy Lab. Ele é intencionalmente mais restrito do que um leaderboard de modelos: o objetivo principal é observar como a mesma tarefa de análise de incidente se comporta à medida que o controle se desloca de código determinístico da aplicação para execução dirigida pelo modelo.

Para a comparação compacta entre três providers, veja [`FROZEN_THREE_PROVIDER_BENCHMARK.md`](FROZEN_THREE_PROVIDER_BENCHMARK.md).

## Pergunta experimental

> Dado o mesmo incidente, limite de evidência, evaluator de grounding e padrão de autonomia, o que muda quando o fluxo de controle e o comportamento do provider/modelo mudam?

As comparações mais fortes são **dentro de um único provider**, onde incidente e configuração do provider permanecem fixos enquanto o padrão de autonomia muda. Resultados entre providers continuam úteis, mas comparam um bundle de modelo, transporte, configuração de reasoning, tokenização, infraestrutura e comportamento do provider em vez de isolar apenas o modelo.

## Setup compartilhado

Os três experimentos repetidos usaram:

- incidente: `INC-001`;
- Git commit: `1f8f8b892b033957c73e6260f12edb75e321462c`;
- repetições: `5` por padrão;
- seis padrões por provider;
- ordem inicial dos padrões rotacionada deterministicamente entre os ciclos;
- nenhum retry oculto;
- Grounding Evaluation v1 determinístico;
- artefatos de benchmark metadata-only;
- agregados de execução e grounding calculados apenas sobre execuções bem-sucedidas;
- todas as tentativas usadas nas taxas de confiabilidade.

Nos três experimentos, **90/90 execuções de padrão concluíram com sucesso**. Nenhum experimento repetido registrou falha por rate limit ou provider error.

Os seis padrões foram:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

## Experimento 1 — OpenAI GPT-5.6 Luna

Configuração:

- provider: `openai`;
- modelo: `gpt-5.6-luna`;
- transporte: OpenAI Responses API nativa;
- max output tokens: `4000`;
- timeout: `60s`;
- reasoning effort: provider-defined/default;
- intervalo entre tentativas do benchmark: `2s`;
- status: completo (`30/30`).

| Padrão | Calls | Tools | Tokens médios | Latência p50 | Unsupported | Proposed | Causality | Grounding | Trajetórias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 877 | 8,847.6 ms | 0.0 | 0.0 | 0.6 | 100.0% | 1 |
| Chaining | 3.0 | 0.0 | 3,838 | 28,317.4 ms | 0.2 | 0.0 | 0.4 | 90.0% | 1 |
| Routing | 2.0 | 0.0 | 910 | 8,611.5 ms | 0.0 | 0.0 | 1.8 | 100.0% | 1 |
| Parallel | 4.0 | 0.0 | 5,530 | 24,791.8 ms | 0.8 | 0.2 | 0.0 | 92.8% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 1,576 | 9,382.9 ms | 0.0 | 0.0 | 0.2 | 100.0% | 1 |
| Agent | 2.0 | 5.0 | 1,662 | 10,376.4 ms | 0.0 | 0.0 | 0.2 | 100.0% | 1 |

### Observações OpenAI

**Routing foi o padrão OpenAI de menor latência** nesta amostra (`8.61s` p50), pouco à frente de augmented (`8.85s`). Ambos tiveram ratio de specific grounding de `100%`.

**Evaluator-optimizer também atingiu `100%` de specific grounding** com duas chamadas de modelo e `9.38s` p50. Neste experimento, a etapa adicional de avaliação não produziu a maior latência nem o maior uso de tokens.

**O bounded agent atingiu `100%` de specific grounding com uma única trajetória observada em cinco execuções.** Ele teve média de duas chamadas de modelo e cinco chamadas de ferramentas, com `10.38s` p50.

**Chaining e parallelization foram os dois padrões OpenAI mais fracos em specific grounding e também os dois mais lentos.** Chaining atingiu `90.0%` com `28.32s` p50; parallel atingiu `92.8%` com `24.79s` p50.

Uma cautela separada aparece em **routing**: ele teve `100%` de specific grounding enquanto apresentou média de `1.8` causal overclaims por execução. Grounding Evaluation v1 trata deliberadamente suporte factual exato e causal overclaim como dimensões diferentes. Portanto, `100%` de specific grounding não deve ser interpretado como “resposta completamente correta”.

## Experimento 2 — Groq GPT-OSS 20B

Configuração:

- provider: `groq`;
- modelo: `openai/gpt-oss-20b`;
- transporte: Chat Completions compatível com OpenAI;
- max output tokens: `900`;
- timeout: `30s`;
- reasoning effort: `medium`;
- intervalo entre tentativas: `30s`;
- status: completo (`30/30`).

| Padrão | Calls | Tools | Tokens médios | Latência p50 | Unsupported | Proposed | Causality | Grounding | Trajetórias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 1,250 | 1,485.6 ms | 1.6 | 0.4 | 0.6 | 88.3% | 1 |
| Chaining | 3.0 | 0.0 | 4,087 | 4,263.2 ms | 1.6 | 2.0 | 1.2 | 67.4% | 1 |
| Routing | 2.0 | 0.0 | 1,769 | 2,116.3 ms | 1.8 | 0.0 | 0.6 | 87.8% | 1 |
| Parallel | 4.0 | 0.0 | 5,890 | 3,093.8 ms | 1.4 | 0.2 | 0.2 | 87.1% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 2,248 | 2,111.4 ms | 1.4 | 0.0 | 0.0 | 88.5% | 1 |
| Agent | 5.2 | 4.2 | 4,342 | 4,000.4 ms | 2.4 | 1.4 | 0.4 | 82.6% | 4 |

### Observações Groq

**Augmented foi o padrão Groq de menor latência** (`1.49s` p50). Evaluator-optimizer e routing vieram em seguida, ambos próximos de `2.11s`.

**Evaluator-optimizer teve o maior ratio de specific grounding no experimento Groq** (`88.5%`) e média zero de causal overclaim, com duas chamadas de modelo.

**Chaining foi o padrão Groq mais fraco em specific grounding** (`67.4%`). Também apresentou média de `1.2` causal overclaims e `2.0` detalhes propostos por execução.

**O bounded agent mostrou substancialmente mais variação de trajetória que qualquer outro padrão.** Cinco execuções produziram quatro trajetórias únicas, com `5.2` chamadas de modelo e `4.2` chamadas de ferramentas em média.

## Experimento 3 — Anthropic Claude Sonnet 5

Configuração:

- provider: `anthropic`;
- modelo: `claude-sonnet-5`;
- transporte: Anthropic Messages API;
- max output tokens: `4000`;
- timeout: `60s`;
- reasoning effort: provider-defined/default;
- intervalo entre tentativas: `10s`;
- status: completo (`30/30`).

| Padrão | Calls | Tools | Tokens médios | Latência p50 | Unsupported | Proposed | Causality | Grounding | Trajetórias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 1,786 | 15,713.2 ms | 0.6 | 0.0 | 0.6 | 95.3% | 1 |
| Chaining | 3.0 | 0.0 | 6,027 | 39,311.0 ms | 1.2 | 0.2 | 1.2 | 82.1% | 1 |
| Routing | 2.0 | 0.0 | 1,827 | 14,397.9 ms | 2.0 | 0.0 | 1.8 | 84.6% | 1 |
| Parallel | 4.0 | 0.0 | 9,284 | 40,371.3 ms | 0.6 | 0.0 | 1.4 | 94.8% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 3,053 | 16,210.0 ms | 0.4 | 0.4 | 0.8 | 96.7% | 1 |
| Agent | 2.0 | 5.0 | 4,354 | 16,876.2 ms | 0.8 | 0.6 | 1.4 | 93.6% | 1 |

### Observações Anthropic

**Routing foi o padrão Anthropic de menor latência** (`14.40s` p50), seguido de augmented (`15.71s`) e evaluator-optimizer (`16.21s`).

**Evaluator-optimizer teve o maior ratio Anthropic de specific grounding** (`96.7%`). Também foi materialmente mais barato e rápido que chaining e parallelization dentro do bundle Anthropic.

**Chaining novamente teve o menor ratio de specific grounding** (`82.1%`). Parallelization teve o maior p50 (`40.37s`) e maior uso médio de tokens (`9,284`).

**O bounded agent Anthropic mostrou a mesma topologia grossa do OpenAI**: duas chamadas de modelo, cinco chamadas de ferramentas e uma trajetória observada em cinco execuções.

O CSV Anthropic reportou taxa de preservação de incerteza de `1.0` para todos os padrões nesta amostra. Isso é evidência descritiva destas execuções, não garantia geral do provider.

## Visão cross-provider

A tabela abaixo é apenas descritiva. Ela **não** isola qualidade de modelo, porque transporte do provider, configuração de reasoning, orçamento de output, tokenização, infraestrutura e pacing diferem.

### Specific grounding

| Padrão | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | 95.3% |
| Chaining | 90.0% | 67.4% | 82.1% |
| Routing | 100.0% | 87.8% | 84.6% |
| Parallel | 92.8% | 87.1% | 94.8% |
| Evaluator-optimizer | 100.0% | 88.5% | 96.7% |
| Agent | 100.0% | 82.6% | 93.6% |

### Latência p50

| Padrão | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 8.85s | 1.49s | 15.71s |
| Chaining | 28.32s | 4.26s | 39.31s |
| Routing | 8.61s | 2.12s | 14.40s |
| Parallel | 24.79s | 3.09s | 40.37s |
| Evaluator-optimizer | 9.38s | 2.11s | 16.21s |
| Agent | 10.38s | 4.00s | 16.88s |

Nessas execuções, o bundle OpenAI teve ratio de specific grounding maior em cinco dos seis padrões; Anthropic foi maior em parallelization. Groq teve menor latência p50 nos seis padrões. Essas são propriedades dos **bundles provider/modelo/configuração testados**, não prova de um ranking inerente entre modelos.

Contagens brutas de tokens não devem ser comparadas como unidades equivalentes entre providers. Dentro de um provider, ainda são úteis para entender o custo relativo dos seis padrões de control flow.

## Achados com suporte mais forte atualmente

### 1. Chaining não apresentou vantagem de grounding

Chaining teve o menor ratio de specific grounding nos três experimentos repetidos: `90.0%` na OpenAI, `67.4%` na Groq e `82.1%` na Anthropic. Também esteve entre os padrões de maior latência em todos os providers.

Um mecanismo plausível é que handoffs sequenciais criem múltiplas oportunidades para introdução e propagação de inferências não suportadas, mas o experimento atual **não** testa diretamente esse mecanismo.

### 2. Evaluator-optimizer foi consistentemente competitivo

Evaluator-optimizer atingiu `100%` de specific grounding na OpenAI e o maior grounding nos experimentos Groq (`88.5%`) e Anthropic (`96.7%`).

O resultado sustenta estudo mais profundo de loops de avaliação/revisão, mas não estabelece que um LLM evaluator seja, por si só, prova de correção factual.

### 3. Autonomia do agente expôs comportamento de trajetória dependente de provider/modelo

| Bundle | Model calls | Tool calls | Trajetórias únicas |
| --- | ---: | ---: | ---: |
| OpenAI | 2.0 | 5.0 | 1 |
| Groq | 5.2 | 4.2 | 4 |
| Anthropic | 2.0 | 5.0 | 1 |

OpenAI e Anthropic produziram a mesma topologia grossa do agente em cinco execuções. Groq produziu quatro trajetórias únicas, mais chamadas de modelo e menos chamadas de ferramentas em média.

Essa é a evidência mais clara até aqui para a distinção central do lab:

> Quando código determinístico da aplicação controla o próximo passo, a topologia de execução é estável por construção. Quando o modelo controla o próximo passo, o comportamento do modelo/provider pode alterar a própria trajetória de execução.

Essa afirmação está limitada às execuções observadas e não diz que um estilo de trajetória seja universalmente melhor.

### 4. Specific grounding e disciplina causal são separados

Specific grounding alto não garantiu baixo causal overclaim. OpenAI routing atingiu `100%` de specific grounding com média de `1.8` causal overclaims por execução; Anthropic routing teve a mesma média de `1.8` achados causais com `84.6%` de specific grounding.

Grounding Evaluation v1, portanto, mantém separados suporte factual específico, parâmetros propostos, causal overclaim e preservação de incerteza.

### 5. Mais chamadas de modelo não melhoraram grounding de forma monotônica

Chaining e parallelization usam mais chamadas de modelo que augmented ou routing, mas nenhum demonstrou vantagem consistente de grounding. Neste experimento, complexidade de workflow e grounding factual não foram monotônicos.

## Ameaças à validade

Estes resultados devem ser lidos com várias limitações:

1. **Um único fixture de incidente.** Todas as execuções usam `INC-001`; os achados podem não generalizar para outros domínios, níveis de ambiguidade, conjuntos de ferramentas ou formatos de evidência.
2. **Amostra pequena.** Cinco repetições por padrão/provider revelam sinais úteis de variância, mas não sustentam afirmações estatísticas fortes.
3. **Confounding do bundle de provider.** OpenAI, Groq e Anthropic diferem em modelo, transporte, infraestrutura, tokenização, max output, configuração de reasoning e pacing.
4. **Caps de output diferentes.** OpenAI e Anthropic usaram `4000`; Groq usou `900`. Os caps foram selecionados após smoke calibration específica do provider e impedem afirmação apples-to-apples de orçamento de tokens.
5. **Pacing diferente.** Os intervalos foram OpenAI `2s`, Groq `30s` e Anthropic `10s`. Esses intervalos existem somente entre tentativas independentes do benchmark e não serializam chamadas internas de um padrão.
6. **Escopo do Grounding evaluator.** Grounding Evaluation v1 é deliberadamente limitado e lexical/estrutural. Não é sistema NLI nem métrica universal de correção.
7. **Sem corpos de resposta persistidos.** Os artefatos são metadata-only por design. Análise forense em nível de claim exige observação separadamente aprovada ou fixtures estáticos.
8. **Variação do serviço live.** Condições de rede e do provider afetam latência. Os p50 descrevem estas execuções, não comportamento garantido de serviço.
9. **Sem normalização de custo ainda.** Tokens são registrados, mas custo USD provider-aware ainda não foi normalizado.

## O que não é afirmado

Estes experimentos não estabelecem que:

- agentes sejam melhores que workflows;
- workflows sejam mais seguros que agentes;
- um provider/modelo seja universalmente melhor que outro;
- Groq seja universalmente mais rápida que OpenAI ou Anthropic;
- evaluator-optimizer garanta correção;
- chaining seja universalmente ruim;
- mais chamadas de modelo necessariamente reduzam ou aumentem alucinações;
- `100%` de specific grounding signifique uma resposta completamente correta;
- a aceitação por um LLM evaluator prove groundedness;
- contagens brutas de tokens sejam diretamente comparáveis entre providers.

## Próximos experimentos

Os próximos passos mais úteis são:

1. repetir os seis padrões em fixtures de incidentes adicionais antes de aumentar repetições em `INC-001`;
2. fortalecer avaliação determinística relacional/contextual usando a claim matrix rotulada por humanos;
3. comparar o comportamento estático do claim evaluator entre semantic judges independentes;
4. adicionar normalização de custo provider-aware em USD preservando metadados brutos de tokens do provider;
5. comparar a aceitação do evaluator-optimizer com achados determinísticos e semânticos em nível de claim.

## Nota de reprodutibilidade

Os experimentos repetidos OpenAI, Groq e Anthropic documentados aqui foram todos executados a partir do Git commit:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

A execução Anthropic congelada produziu exatamente `30` linhas metadata-only em `runs.jsonl`, correspondendo a cinco repetições em seis padrões.

Smokes e calibrações anteriores usaram transportes, orçamentos de output, pacing, evaluators ou commits posteriores diferentes. Eles continuam úteis como evidência de debugging/calibração, mas são deliberadamente excluídos desta comparação congelada de experimentos repetidos.

# Benchmark Congelado com Três Providers

> **Idioma:** Português (Brasil) · [Original em inglês](../FROZEN_THREE_PROVIDER_BENCHMARK.md)

## Propósito

Este documento consolida o benchmark repetido de arquitetura para três bundles provider/modelo sobre a mesma implementação congelada.

Ele não é um leaderboard de modelos. O experimento compara **bundles provider/modelo/configuração** mantendo fixos o incidente, os seis padrões de arquitetura, o runner do benchmark, o Grounding Evaluation v1 determinístico, a política de retries e o limite de persistência.

## Setup congelado

Os três experimentos repetidos usam:

- incidente: `INC-001`;
- Git commit: `1f8f8b892b033957c73e6260f12edb75e321462c`;
- repetições: `5` por padrão;
- seis padrões por provider;
- `30` execuções de padrão por provider;
- `90` execuções no total;
- rotação determinística da ordem inicial dos padrões;
- nenhum retry oculto;
- artefatos de benchmark metadata-only;
- Grounding Evaluation v1 determinístico.

Todas as **90/90 execuções concluíram com sucesso**. Nenhum experimento repetido registrou falha por rate limit ou provider error.

Os seis padrões são:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

## Bundles de provider

| Bundle | Transporte | Max output tokens | Timeout | Reasoning | Intervalo entre tentativas |
| --- | --- | ---: | ---: | --- | ---: |
| OpenAI `gpt-5.6-luna` | Responses API nativa | 4000 | 60s | provider-defined/default | 2s |
| Groq `openai/gpt-oss-20b` | Chat Completions compatível com OpenAI | 900 | 30s | medium | 30s |
| Anthropic `claude-sonnet-5` | Anthropic Messages API | 4000 | 60s | provider-defined/default | 10s |

Os diferentes transportes, orçamentos de tokens, infraestrutura do provider, tokenização e configurações de reasoning fazem parte dos bundles testados. Resultados cross-provider, portanto, descrevem os bundles e não qualidade isolada do modelo.

## Specific grounding por padrão

| Padrão | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | 95.3% |
| Chaining | 90.0% | 67.4% | 82.1% |
| Routing | 100.0% | 87.8% | 84.6% |
| Parallel | 92.8% | 87.1% | 94.8% |
| Evaluator-optimizer | 100.0% | 88.5% | 96.7% |
| Agent | 100.0% | 82.6% | 93.6% |

Média dos seis agregados de grounding por padrão, apresentada apenas como resumo descritivo compacto:

- OpenAI: `97.1%`;
- Anthropic: `91.2%`;
- Groq: `83.6%`.

Essa média não é uma estimativa estatística de acurácia geral do modelo. Ela calcula a média de seis resumos em nível de padrão sobre um único fixture de incidente.

## Latência p50 por padrão

| Padrão | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 8.85s | 1.49s | 15.71s |
| Chaining | 28.32s | 4.26s | 39.31s |
| Routing | 8.61s | 2.12s | 14.40s |
| Parallel | 24.79s | 3.09s | 40.37s |
| Evaluator-optimizer | 9.38s | 2.11s | 16.21s |
| Agent | 10.38s | 4.00s | 16.88s |

Groq teve a menor latência p50 em todos os padrões nesta amostra. Anthropic teve o maior p50 em cinco dos seis padrões; parallelization foi ligeiramente mais lenta que chaining na Anthropic.

Esses valores descrevem condições live dos providers durante as execuções e não são garantias de nível de serviço.

## Uso de tokens por padrão

| Padrão | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 877 | 1,250 | 1,786 |
| Chaining | 3,838 | 4,087 | 6,027 |
| Routing | 910 | 1,769 | 1,827 |
| Parallel | 5,530 | 5,890 | 9,284 |
| Evaluator-optimizer | 1,576 | 2,248 | 3,053 |
| Agent | 1,662 | 4,342 | 4,354 |

Contagens brutas de tokens são úteis **dentro de um provider** para comparar padrões. Elas não são unidades de contabilização equivalentes entre providers porque tokenizers, contabilização de reasoning e semântica das APIs diferem.

## Achados unsupported, proposed e causal

### OpenAI

| Padrão | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 0.0 | 0.0 | 0.6 |
| Chaining | 0.2 | 0.0 | 0.4 |
| Routing | 0.0 | 0.0 | 1.8 |
| Parallel | 0.8 | 0.2 | 0.0 |
| Evaluator-optimizer | 0.0 | 0.0 | 0.2 |
| Agent | 0.0 | 0.0 | 0.2 |

### Groq

| Padrão | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 1.6 | 0.4 | 0.6 |
| Chaining | 1.6 | 2.0 | 1.2 |
| Routing | 1.8 | 0.0 | 0.6 |
| Parallel | 1.4 | 0.2 | 0.2 |
| Evaluator-optimizer | 1.4 | 0.0 | 0.0 |
| Agent | 2.4 | 1.4 | 0.4 |

### Anthropic

| Padrão | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 0.6 | 0.0 | 0.6 |
| Chaining | 1.2 | 0.2 | 1.2 |
| Routing | 2.0 | 0.0 | 1.8 |
| Parallel | 0.6 | 0.0 | 1.4 |
| Evaluator-optimizer | 0.4 | 0.4 | 0.8 |
| Agent | 0.8 | 0.6 | 1.4 |

Specific grounding e disciplina causal permanecem dimensões separadas. Por exemplo, OpenAI routing teve `100%` de specific grounding com média de `1.8` achados de causalidade; Anthropic routing teve `84.6%` de grounding e a mesma média de `1.8` em causality.

## Achados mais fortes nos três bundles

### 1. Chaining foi o padrão com grounding mais consistentemente fraco

Chaining teve o menor ratio de specific grounding nos três experimentos:

- OpenAI: `90.0%`;
- Groq: `67.4%`;
- Anthropic: `82.1%`.

Também esteve entre os padrões de maior latência em cada provider. Isso é evidência de que decomposição sequencial não criou vantagem de grounding para este incidente.

Um mecanismo plausível é a propagação de inferências não suportadas através de handoffs sequenciais, mas o benchmark repetido não prova diretamente esse mecanismo.

### 2. Evaluator-optimizer foi consistentemente competitivo

Evaluator-optimizer empatou no maior grounding na OpenAI (`100%`) e foi o padrão de maior grounding tanto na Groq (`88.5%`) quanto na Anthropic (`96.7%`).

Também permaneceu materialmente mais barato e rápido que chaining e parallelization dentro de OpenAI e Anthropic. O resultado sustenta estudo adicional de loops de evaluator/revisão, mas um LLM evaluator não é, por si só, evidência de correção.

### 3. O comportamento de trajetória do agente dependeu fortemente do bundle provider/modelo

| Bundle | Model calls | Tool calls | Trajetórias únicas |
| --- | ---: | ---: | ---: |
| OpenAI | 2.0 | 5.0 | 1 |
| Groq | 5.2 | 4.2 | 4 |
| Anthropic | 2.0 | 5.0 | 1 |

OpenAI e Anthropic produziram a mesma topologia grossa do agente nas cinco execuções: duas chamadas de modelo, as cinco ferramentas read-only e uma trajetória observada. Groq produziu quatro trajetórias, mais chamadas de modelo e menos chamadas de ferramentas em média.

Isso fortalece a observação central do lab sobre o limite de controle:

> Quando o modelo passa a controlar seleção de ferramentas e o próximo passo, o comportamento do provider/modelo pode alterar a própria trajetória de execução.

Isso **não** estabelece que um estilo de trajetória seja universalmente melhor.

### 4. Mais estrutura de workflow não melhorou grounding de forma monotônica

Parallelization e chaining usaram mais chamadas de modelo que augmented ou routing, mas nenhum mostrou vantagem consistente de grounding. A relação entre número de chamadas e grounding, portanto, não foi monotônica nessas execuções.

### 5. Grounding e disciplina causal devem permanecer métricas separadas

Specific grounding alto não garantiu baixo causal overclaim. Isso aparece especialmente em routing e em alguns padrões Anthropic. Uma única pontuação agregada de hallucination esconderia essa distinção.

## Observações dentro de cada provider

### OpenAI

- menor p50: routing (`8.61s`);
- maior grounding: augmented, routing, evaluator-optimizer e agent (`100%`);
- menor grounding: chaining (`90.0%`);
- topologia do agente: estável, uma trajetória.

### Groq

- menor p50: augmented (`1.49s`);
- maior grounding: evaluator-optimizer (`88.5%`);
- menor grounding: chaining (`67.4%`);
- topologia do agente: maior variância de trajetória observada (`4`).

### Anthropic

- menor p50: routing (`14.40s`);
- maior grounding: evaluator-optimizer (`96.7%`);
- menor grounding: chaining (`82.1%`);
- topologia do agente: estável, uma trajetória;
- parallelization consumiu mais tokens (`9,284`) e teve maior p50 (`40.37s`).

## Ameaças à validade

1. **Um único fixture de incidente.** Todas as 90 execuções usam `INC-001`.
2. **Amostra repetida pequena.** `n=5` por padrão/provider expõe variância, mas não sustenta afirmações estatísticas fortes.
3. **Confounding do bundle de provider.** Modelo, transporte, infraestrutura, tokenização, caps de output e configurações de reasoning diferem.
4. **Caps de output diferentes.** OpenAI e Anthropic usaram `4000`; Groq usou `900` após calibração específica do provider.
5. **Pacing diferente.** Os intervalos foram 2s, 30s e 10s, respectivamente.
6. **Escopo do Grounding v1.** O evaluator é limitado e lexical/estrutural, não correção semântica universal nem NLI.
7. **Persistência metadata-only.** Corpos brutos das respostas são deliberadamente excluídos dos artefatos do benchmark repetido.
8. **Variação do serviço live.** Latência inclui condições reais de provider/rede.
9. **Sem normalização de custo.** Contagens brutas de tokens ainda não são convertidas em custo USD provider-aware.

## O que não é afirmado

O benchmark de 90 execuções não estabelece que:

- um modelo seja universalmente melhor que outro;
- agentes sejam melhores que workflows;
- workflows sejam mais seguros que agentes;
- Groq seja universalmente mais rápida;
- evaluator-optimizer garanta correção;
- chaining seja universalmente ruim;
- `100%` de specific grounding signifique resposta completamente correta;
- contagens de tokens sejam diretamente comparáveis entre providers.

## Próximos experimentos

Os próximos passos de maior valor são:

1. repetir os seis padrões em fixtures adicionais de incidentes;
2. fortalecer avaliação determinística relacional/contextual usando a claim matrix rotulada por humanos;
3. adicionar normalização de custo provider-aware preservando metadados brutos de tokens;
4. comparar comportamento estático do claim evaluator entre judges independentes;
5. revisar tamanho de amostra somente depois de aumentar a diversidade de incidentes.

Aumentar repetições apenas em `INC-001` tem menor valor neste estágio do que adicionar novos tipos de incidentes.

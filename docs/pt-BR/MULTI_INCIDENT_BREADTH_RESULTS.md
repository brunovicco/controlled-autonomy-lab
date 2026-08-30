# Resultados do Multi-Incident Breadth Benchmark

> **Idioma:** Português (Brasil) · [Original em inglês](../MULTI_INCIDENT_BREADTH_RESULTS.md)

## Propósito

Este documento reporta a geração breadth multi-incidente principal do Controlled Autonomy Lab.

O experimento estende o benchmark repetido anterior com três providers alterando a postura da evidência em quatro incidentes canônicos, enquanto mantém fixos os seis padrões de arquitetura.

O objetivo não é produzir um leaderboard de modelos.

Ele faz uma pergunta de arquitetura mais restrita:

> As propriedades observadas de augmented generation, chaining, routing, parallelization, loops evaluator-optimizer e bounded tool-using agents persistem quando a evidência muda de correlação para causas confirmadas e para um caso inconclusivo que exige abstention?

A geração breadth é intencionalmente descritiva:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

Há uma execução por célula. Portanto, os resultados sustentam observações e hipóteses orientadas à arquitetura, não afirmações de significância estatística.

---

## Limite experimental congelado

A geração breadth principal foi congelada em:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Os três bundles de provider executaram exatamente essa implementação.

O commit congelado inclui o comportamento do benchmark que preserva esgotamento dos limites do bounded agent como evidência do benchmark, em vez de permitir que isso escape como uma exceção não classificada do runner.

Gerações históricas de calibração não são misturadas aos resultados reportados aqui.

Gerações excluídas incluem:

- a calibração breadth OpenAI anterior em `14863271f5054756f59227175847e9521b0621c3`;
- a geração Groq pré-fix que expôs a falha do runner do bounded agent;
- a calibração Groq pós-fix executada acidentalmente com `max_tokens=1200`.

Somente a geração principal explicitamente congelada é analisada abaixo.

---

## Incidentes canônicos

| Incidente | Postura da evidência |
| --- | --- |
| `INC-001` | correlação sem causa atual comprovada |
| `INC-002` | causa por deployment explicitamente confirmada |
| `INC-003` | causa por dependência explicitamente confirmada |
| `INC-004` | evidência inconclusiva; abstention esperada |

Esses incidentes variam intencionalmente a quantidade de autoridade causal suportada pela evidência.

Essa distinção importa porque specific factual grounding e correção causal são avaliados separadamente.

---

## Padrões de arquitetura

Os mesmos seis padrões foram executados para cada combinação incidente/provider:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

O agente continua intencionalmente restrito.

Ele usa ferramentas read-only, allowlist explícita, limites de passos e de chamadas de ferramentas. Não pode reiniciar serviços, escrever configuração, executar comandos shell, realizar rollback ou alterar estado de produção.

O benchmark, portanto, avalia **autonomia limitada**, não operação autônoma irrestrita.

---

## Bundles de provider

| Bundle | Modelo | Transporte | Max output tokens | Timeout | Reasoning | Intervalo entre tentativas |
| --- | --- | --- | ---: | ---: | --- | ---: |
| OpenAI | `gpt-5.6-luna` | Responses API nativa | 4000 | 60s | provider-defined/default | 2s |
| Groq | `openai/gpt-oss-20b` | API compatível com OpenAI | 900 | 30s | medium | 30s |
| Anthropic | `claude-sonnet-5` | Anthropic Messages API | 4000 | 60s | provider-defined/default | 10s |

Transporte, infraestrutura do provider, tokenização, limites de output, configuração de reasoning e condições live do serviço fazem parte de cada bundle testado.

Comparações cross-provider, portanto, descrevem **bundles provider/modelo/API/config**, não qualidade isolada do modelo.

---

# Disponibilidade antes de qualidade

Disponibilidade é analisada separadamente da qualidade das respostas.

Uma célula com rate limit ou provider error não recebe grounding zero, correção causal zero nem qualquer outro valor de qualidade imputado.

## Geração principal

| Provider | Tentativas | Sucesso | Rate limited | Provider error | Conclusão |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 0 | 0 | 100.0% |
| Groq | 24 | 12 | 12 | 0 | 50.0% |
| Anthropic | 24 | 23 | 0 | 1 | 95.8% |
| **Total** | **72** | **59** | **12** | **1** | **81.9%** |

As falhas da Groq não ficaram distribuídas por padrão de arquitetura.

Em vez disso:

- `INC-001`: 6/6 bem-sucedidas;
- `INC-002`: 6/6 bem-sucedidas;
- `INC-003`: 6/6 com rate limit;
- `INC-004`: 6/6 com rate limit.

Assim, todo padrão possui exatamente duas células Groq observadas e duas com rate limit.

Isso é um confound de disponibilidade no nível do provider, e não evidência de que os seis padrões de arquitetura falharam independentemente na mesma taxa.

Anthropic teve um provider error:

```text
INC-003 / chaining
Anthropic request failed
```

A célula é preservada como evidência de disponibilidade do provider e não é reexecutada nem convertida em observação de qualidade.

---

# Resultados no nível de arquitetura

Métricas de qualidade, custo, latência e trajetória abaixo usam somente células em que:

```text
status = ok
```

| Padrão | Observado | Grounding médio | Causal overclaims | Células sem overclaim | Média model calls | Média tool calls | Tokens médios | Latência p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 10/12 | 97.8% | 3 | 70.0% | 1.0 | 0.0 | 1,264 | 7.69s |
| Chaining | 9/12 | 74.4% | 5 | 66.7% | 3.0 | 0.0 | 4,769 | 26.34s |
| Routing | 10/12 | 92.8% | 2 | 80.0% | 2.0 | 0.0 | 1,560 | 7.15s |
| Parallel | 10/12 | 94.9% | 7 | 60.0% | 4.0 | 0.0 | 7,141 | 21.81s |
| Evaluator-optimizer | 10/12 | 97.6% | 4 | 70.0% | 2.4 | 0.0 | 3,427 | 9.13s |
| Agent | 10/12 | 95.4% | **0** | **100.0%** | 2.5 | 4.7 | 3,158 | 7.03s |

Esses valores expõem trade-offs diferentes. Nenhuma métrica isolada é suficiente para ordenar as arquiteturas.

---

# Achado 1 — Bounded agency mostrou a maior contenção causal observada

O bounded tool-using agent foi o único padrão de arquitetura com:

```text
0 detected causal overclaims
```

em todas as células breadth bem-sucedidas.

A cobertura observada foi:

- OpenAI: 4/4 incidentes;
- Groq: 2/4 incidentes, com os outros dois bloqueados por rate limits do provider;
- Anthropic: 4/4 incidentes.

Isso totaliza dez células observáveis do agente com zero causal overclaims.

Inclui os dois incidentes em que contenção causal é mais importante:

- `INC-001`, em que existe correlação, mas uma causa atual não está comprovada;
- `INC-004`, em que a evidência permanece inconclusiva e abstention é esperada.

O sinal não decorre simplesmente de maximizar a pontuação de grounding.

A média de specific grounding do agente foi `95.4%`, enquanto augmented e evaluator-optimizer ficaram acima de `97%`.

A distinção observada é, portanto:

> grounding alto combinado com maior contenção causal.

Esse resultado sustenta estudo adicional de bounded tool-using agency como mecanismo de aquisição de evidência sob limites explícitos de controle.

Ele **não** estabelece que agentes sejam universalmente mais seguros, mais precisos ou melhores que workflows.

---

# Achado 2 — O sinal do agente apareceu sob comportamentos diferentes de provider

A topologia grossa do agente diferiu materialmente entre os bundles de provider.

## OpenAI

Os quatro incidentes usaram:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> search_runbook
-> get_previous_incidents
-> final-answer
```

Cada execução usou:

```text
2 model calls
5 tool calls
```

## Anthropic

Anthropic produziu a mesma trajetória grossa da OpenAI nos quatro incidentes:

```text
2 model calls
5 tool calls
```

## Groq

Os dois incidentes observáveis foram diferentes.

`INC-001`:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> get_previous_incidents
-> final-answer
```

com:

```text
5 model calls
4 tool calls
```

`INC-002`:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> final-answer
```

com:

```text
4 model calls
3 tool calls
```

Apesar dessa variação na topologia de execução, nenhuma das dez células bem-sucedidas do agente produziu causal overclaim detectado.

O resultado fortalece uma observação central do Controlled Autonomy Lab:

> Quando o modelo controla a seleção de ferramentas e o próximo passo, mudar o bundle provider/modelo pode alterar a própria topologia de execução.

A geração breadth adiciona uma observação complementar:

> Diferentes trajetórias limitadas ainda podem exibir contenção causal semelhante nos casos observados.

Nenhuma das afirmações implica que um estilo de trajetória de provider seja universalmente preferível.

---

# Achado 3 — Chaining teve o trade-off geral mais fraco

Prompt chaining produziu:

- menor specific grounding médio: `74.4%`;
- 5 causal overclaims;
- aproximadamente `4,769` tokens médios;
- três chamadas de modelo por célula bem-sucedida;
- maior latência p50 no nível de arquitetura: `26.34s`.

O resultado mais importante ocorreu em `INC-004`.

Esse incidente exige contenção explicitamente porque a evidência permanece inconclusiva.

Nas duas células observáveis de chaining:

```text
4 causal overclaims
0% zero-overclaim rate
75.7% mean grounding
```

Isso torna chaining particularmente fraco para o incidente orientado à abstention nesta geração.

O benchmark não prova diretamente o motivo.

Um mecanismo plausível é propagação de inferências entre estágios sequenciais, mas isso permanece uma hipótese e não um mecanismo causal experimentalmente estabelecido.

A conclusão suportada é mais restrita:

> Nesta geração breadth, decomposição sequencial adicional não se traduziu em melhor grounding nem melhor disciplina causal.

---

# Achado 4 — Parallelization aumentou o custo de cobertura sem garantir disciplina causal

Parallelization manteve specific grounding médio relativamente alto:

```text
94.9%
```

mas produziu o maior número de causal overclaims detectados:

```text
7
```

Também foi o padrão com maior uso de tokens:

```text
7,141 mean tokens
```

com:

```text
4 model calls
21.81s p50 latency
```

O resultado é particularmente importante porque a evidência de calibração anterior fazia parallelization parecer comparativamente disciplinado causalmente.

A geração breadth multi-incidente não preservou esse sinal.

Isso ilustra por que a primeira calibração não deveria ser tratada como conclusão final de arquitetura.

Uma topologia fan-out/fan-in pode melhorar cobertura de evidência e ainda deixar a etapa de síntese responsável por reconciliar evidência conflitante ou incompleta.

Os resultados observados sustentam, portanto, duas perguntas distintas:

1. O workflow recuperou e mencionou fatos suportados?
2. A síntese final afirmou mais autoridade causal do que esses fatos justificam?

Parallelization teve bom desempenho na primeira dimensão e menor consistência na segunda.

---

# Achado 5 — Grounding e correção causal são dimensões distintas

Várias células tiveram specific grounding perfeito e ainda assim produziram causal overclaims.

Exemplos incluem:

- OpenAI parallel em `INC-001`: `100%` de grounding com 3 overclaims;
- Anthropic augmented em `INC-001`: `100%` de grounding com 1 overclaim;
- Anthropic evaluator-optimizer em `INC-001`: `100%` de grounding com 2 overclaims;
- Anthropic augmented em `INC-003`: `100%` de grounding com 1 overclaim;
- OpenAI evaluator-optimizer em `INC-003`: `100%` de grounding com 1 overclaim;
- OpenAI evaluator-optimizer em `INC-004`: `100%` de grounding com 1 overclaim;
- Anthropic parallel em `INC-004`: `100%` de grounding com 1 overclaim.

Uma resposta pode, portanto, referenciar corretamente a evidência disponível e ainda inferir mais certeza causal do que essa evidência suporta.

Isso valida a decisão de avaliar:

```text
specific grounding
```

e:

```text
causal authority
```

como dimensões separadas.

Uma única pontuação agregada de hallucination esconderia essa diferença.

---

# Achado 6 — Incidentes ambíguos e inconclusivos concentraram falhas causais

Nas células breadth bem-sucedidas, o evaluator detectou:

```text
21 total causal overclaims
```

A distribuição por incidente foi:

| Incidente | Causal overclaims |
| --- | ---: |
| INC-001 — apenas correlação | 10 |
| INC-002 — causa por deployment confirmada | 1 |
| INC-003 — causa por dependência confirmada | 4 |
| INC-004 — inconclusivo / abstention | 6 |

Os dois incidentes que exigem maior contenção causal — `INC-001` e `INC-004` — respondem por:

```text
16 / 21
```

de todos os achados causais detectados.

Isso equivale a aproximadamente:

```text
76%
```

A geração breadth está, portanto, exercitando um modo de falha diferente de simples hallucination factual.

A pergunta difícil muitas vezes não é se um fato está presente.

É:

> Quanta autoridade a evidência disponível justifica?

---

# Achado 7 — Routing tornou visível o control flow dependente do modelo

OpenAI e Anthropic produziram as mesmas trajetórias de routing:

```text
INC-001 -> deployment
INC-002 -> deployment
INC-003 -> dependency
INC-004 -> performance
```

Groq produziu:

```text
INC-001 -> dependency
INC-002 -> deployment
```

antes de rate limits impedirem observar `INC-003` e `INC-004`.

A divergência em `INC-001` importa porque demonstra que mudar o bundle provider/modelo pode alterar mais que a redação da resposta.

Pode mudar o caminho de workflow selecionado.

Em uma arquitetura com routing controlado pelo modelo:

> comportamento do modelo faz parte do comportamento do control plane.

Um label de rota não é, por si só, uma conclusão causal, e este experimento não estabelece qual rota para `INC-001` é universalmente correta.

A observação importante é que a escolha de provider/modelo mudou o control flow sob o mesmo fixture e a mesma arquitetura de routing.

---

# Achado 8 — Evaluator-optimizer se adaptou, mas autoavaliação não garantiu correção causal

OpenAI usou a mesma topologia evaluator-optimizer para todos os incidentes:

```text
generate
-> evaluate:1
-> quality-pass
```

Groq fez o mesmo nos dois incidentes observáveis.

Anthropic mostrou comportamento adaptativo de revisão.

Para `INC-002` e `INC-003`:

```text
generate
-> evaluate:1
-> revise:1
-> evaluate:2
-> quality-pass
```

Isso exigiu quatro chamadas de modelo em vez de duas.

Para `INC-001` e `INC-004`, Anthropic passou após a primeira avaliação.

O contraexemplo importante é `INC-001`.

Anthropic evaluator-optimizer produziu:

```text
100% specific grounding
2 detected causal overclaims
```

apesar de o evaluator interno emitir quality pass sem revisão.

Isso sustenta um princípio de design importante:

> Um LLM evaluator interno faz parte da arquitetura de geração; ele não é evidência independente de que a resposta final está correta.

Avaliação externa do benchmark continua necessária.

A geração breadth não mostra que evaluator-optimizer seja ineficaz.

Ela mostra que:

- pode alterar o control flow;
- pode disparar revisões;
- mas seu quality gate interno não garante correção causal externa.

---

# Achado 9 — Evaluator-optimizer não mostrou vantagem agregada clara sobre augmented generation

Nas células bem-sucedidas:

### Augmented

```text
97.8% grounding
3 causal overclaims
1.0 model call
1,264 mean tokens
7.69s p50
```

### Evaluator-optimizer

```text
97.6% grounding
4 causal overclaims
2.4 model calls
3,427 mean tokens
9.13s p50
```

Evaluator-optimizer usou substancialmente mais computação, mas não melhorou grounding agregado nem achados causais em relação a augmented generation nesta amostra breadth.

Isso não estabelece que evaluator-optimizer seja geralmente ineficiente.

Seu valor pode aparecer em tarefas onde os alvos de revisão estejam melhor alinhados ao objetivo externo de qualidade.

O resultado sustenta um princípio de engenharia mais restrito:

> Loops iterativos de avaliação devem justificar seu custo adicional por ganhos medidos específicos da tarefa, em vez de serem presumidos como melhoria de correção por construção.

---

# Achado 10 — A métrica de linguagem de incerteza saturou

O campo do benchmark historicamente chamado:

```text
uncertainty_preserved
```

é implementado como detecção lexical de linguagem relacionada à incerteza.

Na geração breadth ele retornou true para:

```text
59 / 59
```

células bem-sucedidas.

Isso inclui:

- incidentes apenas correlacionais;
- incidentes de causa confirmada;
- incidentes inconclusivos;
- respostas com zero causal overclaims;
- respostas com múltiplos causal overclaims.

A métrica, portanto, não discriminou postura epistêmica correta neste experimento.

A interpretação final deve chamá-la de:

```text
uncertainty-language detected
```

em vez de tratá-la como prova de que a incerteza foi preservada adequadamente.

Esta geração permanece congelada.

O evaluator não é alterado retroativamente para melhorar o resultado.

Uma geração futura de evaluator pode introduzir avaliação epistêmica consciente de postura, mas seus outputs devem permanecer separados desta geração breadth congelada.

---

# Observações específicas por provider

## OpenAI

OpenAI concluiu todas as 24 células.

Resultados por padrão:

| Padrão | Grounding | Causal overclaims | Model calls | Tokens | p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Augmented | 100.0% | 1 | 1.0 | 947 | 7.38s |
| Chaining | 80.4% | 1 | 3.0 | 4,016 | 26.04s |
| Routing | 100.0% | 0 | 2.0 | 993 | 5.52s |
| Parallel | 98.2% | 3 | 4.0 | 5,172 | 20.60s |
| Evaluator-optimizer | 100.0% | 2 | 2.0 | 1,628 | 8.01s |
| Agent | 100.0% | 0 | 2.0 | 1,671 | 6.42s |

Dentro desse bundle, routing e agent combinaram specific grounding perfeito com zero causal overclaims detectados.

Agent adicionou aquisição de evidência mediada por ferramentas com aumento moderado de tokens e latência em relação a routing.

---

## Groq

Groq concluiu 12 de 24 células.

A metade ausente da matriz decorre integralmente de respostas HTTP 429 do provider em `INC-003` e `INC-004`.

Resultados observados por padrão:

| Padrão | Observado | Grounding | Causal overclaims |
| --- | ---: | ---: | ---: |
| Augmented | 2/4 | 88.7% | 0 |
| Chaining | 2/4 | 61.3% | 0 |
| Routing | 2/4 | 79.9% | 1 |
| Parallel | 2/4 | 96.2% | 1 |
| Evaluator-optimizer | 2/4 | 88.0% | 0 |
| Agent | 2/4 | 92.9% | 0 |

Essas métricas de qualidade descrevem somente `INC-001` e `INC-002`.

Não devem ser interpretadas como evidência equivalente de quatro incidentes.

Em particular, Groq não foi observada em `INC-004`, o fixture mais forte orientado à abstention.

A geração breadth Groq contribui, portanto, com:

- observações de qualidade para 12 células bem-sucedidas;
- evidência de disponibilidade do provider para 12 células com rate limit.

---

## Anthropic

Anthropic concluiu 23 de 24 células.

Resultados por padrão:

| Padrão | Observado | Grounding | Causal overclaims | Model calls | Tokens | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 4/4 | 100.0% | 2 | 1.0 | 1,631 | 11.83s |
| Chaining | 3/4 | 75.2% | 4 | 3.0 | 6,004 | 36.61s |
| Routing | 4/4 | 92.0% | 1 | 2.0 | 2,007 | 14.22s |
| Parallel | 4/4 | 90.8% | 3 | 4.0 | 9,679 | 41.07s |
| Evaluator-optimizer | 4/4 | 100.0% | 2 | 3.0 | 5,715 | 26.69s |
| Agent | 4/4 | 92.0% | 0 | 2.0 | 4,365 | 17.36s |

Anthropic ilustra com clareza por que grounding isoladamente é insuficiente.

Augmented e evaluator-optimizer atingiram `100%` de specific grounding médio e ainda produziram causal overclaims.

O agente teve grounding médio menor, `92.0%`, mas nenhum causal overclaim detectado.

---

# Custo de estrutura adicional

Os resultados breadth não mostram relação monotônica entre mais chamadas de modelo e melhor qualidade.

A ordenação aproximada por chamadas de modelo foi:

```text
augmented              1.0
routing                2.0
evaluator-optimizer    2.4
agent                  2.5
chaining               3.0
parallel               4.0
```

Grounding e disciplina causal, porém, não melhoraram monotonicamente nessa sequência.

Parallel teve mais chamadas de modelo e o maior footprint de tokens, mas também o maior número de causal overclaims.

Chaining exigiu três chamadas sequenciais de modelo e teve o menor grounding.

Agent usou mais capacidades do sistema porque podia chamar ferramentas, mas não teve maior uso médio de tokens nem maior latência.

Isso sustenta um princípio mais amplo de arquitetura:

> Estrutura adicional de orquestração é um custo que deve ser justificado por comportamento medido, não uma melhoria automática de qualidade.

---

# Implicações de design

A geração breadth sugere as seguintes hipóteses de design para este domínio de análise de incidentes.

## Use augmented generation como baseline forte de baixa complexidade

Augmented generation manteve grounding excelente com o menor número de chamadas de modelo.

Sua fraqueza não foi cobertura factual, mas overreach causal ocasional.

## Use routing quando caminhos de controle diferenciados importarem

Routing permaneceu relativamente eficiente e expôs uma propriedade arquitetural real: escolha de modelo/provider pode alterar qual caminho de execução é selecionado.

Decisões de routing, portanto, merecem observabilidade e avaliação explícitas.

## Não presuma que chaining sequencial melhora confiabilidade

Chaining foi caro, lento e comparativamente fraco em grounding.

Em tarefas sensíveis a evidência, decomposição sequencial deve ser testada para propagação de inferência em vez de presumida como segurança adicional.

## Trate fan-out paralelo e síntese final como superfícies de risco separadas

Parallelization pode oferecer ampla cobertura de evidência.

A síntese final ainda exige restrições causais fortes.

## Trate evaluator-optimizer como geração, não assurance independente

Um evaluator interno pode melhorar ou revisar outputs, mas compartilha premissas de modelo/sistema com o gerador.

Avaliação independente continua necessária.

## Estude bounded agents como sistemas controlados de aquisição de evidência

A propriedade mais forte observada do agente não foi “mais autonomia”.

Foi:

```text
bounded actions
+ explicit read-only tools
+ finite execution budget
+ external evaluation
+ causal restraint
```

Essa combinação merece investigação adicional.

---

# Ameaças à validade

## 1. Uma execução por célula

A geração breadth usa `n=1` por célula incidente/padrão/provider.

Ela expõe breadth, mas não variância dentro da célula.

Nenhuma significância estatística é reivindicada.

## 2. A disponibilidade dos providers não foi uniforme

Rate limits da Groq removeram todas as observações para `INC-003` e `INC-004`.

As médias de qualidade Groq, portanto, cobrem um subconjunto de incidentes diferente de OpenAI e Anthropic.

## 3. Os bundles de provider diferem

Modelo, transporte, infraestrutura do provider, limites de output, tokenização, configuração de reasoning e pacing diferem.

Resultados cross-provider são comparações de bundles.

## 4. Contagens de tokens não são diretamente equivalentes entre providers

Contagens brutas de tokens são úteis principalmente para comparações de arquitetura dentro de um provider.

Não são unidades normalizadas de contabilização.

## 5. Latência de serviço live

Latência inclui condições do provider e da rede no momento da execução.

Não é garantia de performance de nível de serviço.

## 6. A avaliação de grounding é limitada

Specific grounding não significa correção semântica completa.

Uma resposta pode atingir grounding perfeito e ainda fazer uma inferência causal não suportada.

## 7. A avaliação causal é específica do benchmark

Causal overclaims detectados refletem a evidência rotulada e as regras de autoridade do benchmark.

Não devem ser tratados como métrica universal de raciocínio causal.

## 8. A detecção de linguagem de incerteza saturou

A métrica lexical de incerteza retornou true para toda célula bem-sucedida.

Ela não consegue distinguir adaptação epistêmica correta nesta geração.

## 9. Persistência metadata-only

Respostas completas, prompts, corpos de evidência, argumentos de ferramentas e resultados de ferramentas não são persistidos intencionalmente nos artefatos do benchmark.

Isso melhora o limite de privacidade e reprodutibilidade, mas limita análise semântica irrestrita post-hoc.

## 10. Escopo do bounded agent

O agente é read-only e fortemente limitado.

Esses resultados não se generalizam para agentes com privilégios de mutação, acesso a shell, ferramentas irrestritas, horizontes longos ou autoridade de controle de produção.

---

# O que não é afirmado

Este experimento não estabelece que:

- agentes sejam universalmente melhores que workflows;
- agentes sejam universalmente mais seguros;
- um provider/modelo seja universalmente superior;
- Groq tenha taxa geral de disponibilidade de 50%;
- OpenAI seja sempre mais disponível;
- Anthropic seja sempre mais lenta;
- chaining seja universalmente ruim;
- parallelization inerentemente crie erros causais;
- evaluator-optimizer seja ineficaz;
- `100%` de grounding signifique resposta completamente correta;
- zero causal overclaims detectados prove correção causal universal;
- mais uso de ferramentas melhore automaticamente raciocínio;
- uma trajetória observada seja melhor que outra;
- linguagem lexical de incerteza prove postura epistêmica correta.

---

# Conclusão principal

A geração breadth não identifica um vencedor universal de arquitetura.

Ela mostra que a arquitetura muda **o que pode falhar**.

Workflows sequenciais podem propagar inferência entre estágios.

Workflows paralelos podem coletar evidência ampla enquanto colocam maior carga sobre a síntese.

Routing pode tornar o comportamento do modelo parte do controle de execução.

Loops evaluator-optimizer podem revisar outputs sem se tornar assurance independente.

Tool-using agents podem alterar sua própria topologia de execução entre bundles provider/modelo.

Dentro das células breadth observadas, o bounded agent foi o único padrão de arquitetura sem causal overclaims detectados, mantendo specific grounding alto.

Esse resultado é melhor interpretado como evidência para uma hipótese mais restrita:

> **Autonomia limitada pode ser valiosa não porque o sistema recebe permissão para fazer mais, mas porque pode adquirir evidência dinamicamente enquanto opera dentro de limites explícitos de ações, ferramentas e execução.**

O experimento sustenta testes adicionais dessa hipótese.

Não encerra a questão.

---

# Reprodutibilidade

Commit principal congelado:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Geração principal:

```text
72 attempted cells
59 successful cells
12 rate-limited cells
1 provider-error cell
```

Artefatos de análise gerados incluem:

```text
analysis-manifest.json
availability-by-provider.csv
availability-by-provider-incident.csv
availability-summary.md
cells-72.csv
incident-pattern-provider-matrix.csv
provider-pattern-summary.csv
successful-trajectories.csv
architecture-summary.csv
incident-pattern-quality.csv
architecture-findings.md
causal-by-incident-pattern.csv
adaptive-control-flow.csv
```

Gerações históricas de calibração permanecem separadas e não devem ser recombinadas com esta geração.

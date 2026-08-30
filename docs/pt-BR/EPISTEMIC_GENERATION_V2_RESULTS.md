# Resultados da Geração de Benchmark Epistêmico v2

> **Idioma:** Português (Brasil) · [Original em inglês](../EPISTEMIC_GENERATION_V2_RESULTS.md)

## Propósito

Este documento reporta a primeira geração live de benchmark usando Epistemic Evaluation v4.1.

A geração faz uma pergunta mais restrita que o breadth benchmark histórico:

> A avaliação consciente de postura muda o que a comparação de arquiteturas revela quando a evidência concede diferentes níveis de autoridade causal?

O experimento permanece descritivo:

```text
4 incidents × 6 patterns × 1 run × 3 provider/model/configuration bundles = 72 attempted cells
```

Há uma execução por célula. Estes resultados sustentam observações e hipóteses orientadas à arquitetura, não afirmações de significância estatística.

---

## Limite experimental congelado

A geração foi congelada em:

```text
06e108f5ed7bc3a74e01682538a4bcd23f7d3023
```

Esse commit contém:

- `benchmark-record-v2`;
- `benchmark-summary-v2`;
- `breadth-v2`;
- Grounding Evaluation v1;
- Epistemic Evaluation v4.1;
- o runner dedicado `autonomy-lab-epistemic-benchmark`.

Os outputs históricos breadth-v1 permanecem inalterados e não são misturados nesta geração.

---

## Posturas canônicas da evidência

| Incidente | Postura esperada |
| --- | --- |
| `INC-001` | correlacional — hipóteses causais devem permanecer qualificadas |
| `INC-002` | causa confirmada — a causa suportada pode ser declarada diretamente |
| `INC-003` | causa confirmada — a causa suportada pode ser declarada diretamente |
| `INC-004` | inconclusivo — espera-se abstention causal explícita |

O evaluator infere essas posturas a partir da evidência do fixture, em vez de hard-codear veredictos por identificador de incidente.

---

## Bundles de provider

A geração live reutilizou intencionalmente, o mais próximo possível, os bundles históricos breadth de provider/modelo/configuração.

| Bundle | Modelo | Max output tokens | Timeout | Reasoning | Intervalo entre tentativas |
| --- | --- | ---: | ---: | --- | ---: |
| OpenAI | `gpt-5.6-luna` | 4000 | 60s | provider-defined/default | 2s |
| Anthropic | `claude-sonnet-5` | 4000 | 60s | provider-defined/default | 10s |
| Groq | `openai/gpt-oss-20b` | 900 | 30s | medium | 30s |

Provider, modelo, transporte, tokenização, limites de output, configuração de reasoning e condições live do serviço fazem parte de cada bundle testado.

Comparações entre providers, portanto, descrevem bundles provider/modelo/API/configuração, e não qualidade isolada do modelo.

---

# Disponibilidade antes de qualidade

Disponibilidade permanece separada da qualidade das respostas.

| Provider | Tentativas | Sucesso | Rate limited | Provider error | Conclusão |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 0 | 0 | 100.0% |
| Anthropic | 24 | 24 | 0 | 0 | 100.0% |
| Groq | 24 | 22 | 1 | 1 | 91.7% |
| **Total** | **72** | **70** | **1** | **1** | **97.2%** |

As duas células Groq não-OK são preservadas como evidência de runtime/disponibilidade. Elas não são convertidas em zeros de qualidade nem reexecutadas isoladamente para completar a matriz.

---

# Veredictos epistêmicos nas células bem-sucedidas

Somente células `status=ok` contribuem para as contagens abaixo.

| Veredicto | Contagem | Participação nas 70 células bem-sucedidas |
| --- | ---: | ---: |
| `aligned` | 20 | 28.6% |
| `overclaimed` | 41 | 58.6% |
| `no-position` | 6 | 8.6% |
| `over-hedged` | 3 | 4.3% |
| `insufficient-abstention` | 0 | 0.0% |

Esses são **veredictos detectados sob Epistemic v4.1**. O evaluator é determinístico e intencionalmente conservador; não é entailment semântico nem prova universal de que uma resposta está causalmente correta ou incorreta.

---

# Resultados de postura por incidente

| Incidente | Observado | Aligned | Overclaimed | No-position | Over-hedged |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INC-001` correlacional | 18/18 | 2 | 16 | 0 | 0 |
| `INC-002` causa confirmada | 17/18 | 8 | 6 | 2 | 1 |
| `INC-003` causa confirmada | 17/18 | 7 | 6 | 2 | 2 |
| `INC-004` inconclusivo | 18/18 | 3 | 13 | 2 | 0 |

Os dois incidentes que exigem maior contenção — `INC-001` e `INC-004` — respondem por:

```text
29 / 41 detected overclaims
```

ou aproximadamente:

```text
70.7%
```

de todos os veredictos `overclaimed` nas células bem-sucedidas.

Essa concentração apareceu nos três bundles provider/modelo/configuração.

A observação suportada é, portanto, mais restrita do que “modelos fazem overclaim em geral”:

> Nesta geração, o evaluator determinístico consciente de postura detectou substancialmente mais incompatibilidade de autoridade causal nos incidentes de apenas correlação e de abstention explícita do que nos dois incidentes de causa confirmada.

---

# Resultados epistêmicos por arquitetura

| Padrão | Observado | Aligned | Alignment rate | Overclaimed | Overclaim rate | Outros veredictos |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Augmented | 12/12 | 5 | 41.7% | 5 | 41.7% | 2 no-position |
| Chaining | 12/12 | 3 | 25.0% | 9 | 75.0% | — |
| Routing | 12/12 | 1 | 8.3% | 11 | 91.7% | — |
| Parallel | 11/12 | 2 | 18.2% | 6 | 54.5% | 2 no-position, 1 over-hedged |
| Evaluator-optimizer | 11/12 | 4 | 36.4% | 6 | 54.5% | 1 over-hedged |
| Agent | 12/12 | 5 | 41.7% | **4** | **33.3%** | 2 no-position, 1 over-hedged |

Entre os padrões totalmente observados, bounded tool-using agency apresentou a menor taxa de overclaim detectado nesta geração.

Esse resultado deve ser descrito com cuidado:

> Nas 12 células observadas do bounded agent, Epistemic v4.1 detectou quatro overclaims, comparados a cinco em augmented generation, nove em chaining e onze em routing.

Isso **não** estabelece que agentes sejam universalmente mais seguros ou melhores. Sustenta estudo adicional de aquisição limitada de evidência e control flow escolhido pelo modelo como possíveis contribuintes para contenção causal sob estes fixtures.

---

# Grounding e postura epistêmica continuam distintos

Ponderadas pelas células de provider bem-sucedidas, as médias aproximadas dos ratios de Grounding v1 foram:

| Padrão | Observado | Grounding médio |
| --- | ---: | ---: |
| Augmented | 12 | 97.5% |
| Chaining | 12 | 88.8% |
| Routing | 12 | 95.1% |
| Parallel | 11 | 85.7% |
| Evaluator-optimizer | 11 | 97.0% |
| Agent | 12 | 96.7% |

A arquitetura com maior grounding não é automaticamente a arquitetura com melhor alinhamento de postura.

Routing é o exemplo mais claro nesta geração: manteve grounding médio alto ao mesmo tempo em que recebeu onze veredictos `overclaimed` em doze células observadas.

Isso reforça a separação central do projeto entre:

1. se fatos específicos estão grounded na evidência limitada;
2. quanta autoridade causal a resposta final reivindica a partir desses fatos.

---

# Veredictos por provider

| Provider | Sucesso | Aligned | Overclaimed | No-position | Over-hedged |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 8 | 13 | 2 | 1 |
| Anthropic | 24 | 7 | 16 | 0 | 1 |
| Groq | 22 | 5 | 12 | 4 | 1 |

A mesma concentração ampla em `INC-001` e `INC-004` apareceu nos três bundles.

Isso torna menos provável que o sinal seja apenas comportamento de um único provider, mas ainda não estabelece significância estatística independente de provider porque há `n=1` por célula.

---

# Limitação importante do evaluator

Epistemic v4.1 compõe com Grounding v1.

Um achado de causal overclaim do Grounding v1 é autoritativo para v4.1 e mapeia para `overclaimed`.

Grounding v1 é determinístico e usa matching lexical/de evidência para decidir se uma claim causal atual é explicitamente suportada por um fixture de causa confirmada. Portanto, alguns veredictos `overclaimed` em `INC-002` e `INC-003` podem refletir o limite conservador do matching determinístico, e não uma claim causal semanticamente inválida.

Por isso, a linguagem pública correta é:

```text
detected epistemic overclaim under Epistemic v4.1
```

e não:

```text
proven causal error
```

Uma calibração semântica rotulada futura pode testar esse limite sem reescrever esta geração congelada.

---

# O que esta geração sustenta

As observações mais fortes suportadas são:

1. avaliação consciente de postura expõe distinções que detecção lexical de incerteza não expunha;
2. fixtures apenas correlacionais e de abstention explícita concentraram incompatibilidades detectadas de autoridade causal;
3. grounding e postura epistêmica são dimensões separadas de avaliação;
4. routing mostrou grounding alto, mas taxa alta de overclaim detectado;
5. bounded tool-using agency teve a menor taxa de overclaim detectado entre os padrões totalmente observados nesta geração;
6. escolha de provider/modelo/configuração continua fazendo parte tanto do comportamento de runtime quanto da postura de output;
7. disponibilidade deve permanecer separada de qualidade.

---

# Não-afirmações explícitas

Esta geração **não** estabelece que:

- agentes sejam universalmente mais seguros ou mais precisos que workflows;
- routing seja universalmente inseguro;
- um veredicto determinístico `overclaimed` prove erro causal semântico;
- qualquer provider seja intrinsecamente mais ou menos confiável a partir desta única janela de execução;
- os bundles provider/modelo sejam comparações puras de modelos;
- uma execução por célula tenha significância estatística;
- Grounding v1 ou Epistemic v4.1 seja uma métrica completa de factualidade ou raciocínio causal.

---

# Integridade da geração

Cada geração por provider foi produzida a partir do mesmo commit de implementação congelado e armazenada como artefatos de benchmark metadata-only.

Para cada diretório de provider, checksums SHA-256 foram gerados após a execução e verificados com sucesso.

A geração preserva metadados como:

- proveniência de provider/modelo/configuração;
- status;
- metadados de tokens e latência;
- achados/contagens do Grounding v1;
- campos de postura e veredicto do Epistemic v4.1;
- metadados de trajetória em granularidade grossa.

Ela não persiste intencionalmente:

- prompts completos;
- respostas completas dos modelos;
- corpos de evidência nos registros de resultado do benchmark;
- argumentos/resultados de ferramentas;
- credenciais ou API keys.

---

# Evidence pack publicado

O evidence pack metadata-only curado está publicado em:

[`results/epistemic-v4-1-main/`](../../results/epistemic-v4-1-main/)

Ele contém os três manifests das gerações por provider, todos os 72 registros metadata-only do benchmark, células canônicas consolidadas, resumos por provider/incidente/padrão, metadados de trajetórias bem-sucedidas, um generation manifest e checksums SHA-256.

O pack foi construído offline a partir dos outputs congelados dos providers. Nenhuma chamada de modelo foi reexecutada para criar os artefatos de publicação.

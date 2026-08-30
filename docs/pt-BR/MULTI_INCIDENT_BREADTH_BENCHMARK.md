# Multi-Incident Breadth Benchmark

> **Idioma:** Português (Brasil) · [Original em inglês](../MULTI_INCIDENT_BREADTH_BENCHMARK.md)

A Phase 3D adiciona um modo de benchmark breadth-first sobre o runner de benchmark reproduzível já existente.

O experimento já foi executado e reportado como uma geração congelada distinta.

## Formato do experimento

A geração breadth principal usa intencionalmente uma execução por combinação incidente/padrão/provider:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

O experimento pergunta se o comportamento no nível de arquitetura observado em `INC-001` persiste quando a postura da evidência muda.

Ele não substitui o benchmark repetido congelado de 90 execuções. Os dois experimentos respondem perguntas diferentes:

- o **benchmark repetido de 90 execuções** expõe comportamento repetido e variação de trajetória dentro de um fixture;
- o **breadth benchmark de 72 células** expõe comportamento sob diferentes posturas causais e de evidência.

## Incidentes canônicos

- `INC-001`: correlação sem causa atual comprovada;
- `INC-002`: causa por deployment explicitamente confirmada;
- `INC-003`: causa por dependência explicitamente confirmada;
- `INC-004`: incidente inconclusivo que exige abstention.

## Geração congelada

Freeze da implementação breadth principal:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

A geração contém:

```text
72 attempted cells
59 successful cells
12 rate-limited cells
1 provider-error cell
```

Disponibilidade por provider:

| Provider | Sucesso | Tentativas | Conclusão |
| --- | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 100.0% |
| Groq | 12 | 24 | 50.0% |
| Anthropic | 23 | 24 | 95.8% |

Os rate limits da Groq afetaram todos os padrões em `INC-003` e `INC-004`. Essas células são evidência de disponibilidade, não zeros de qualidade.

A célula Anthropic `INC-003/chaining` terminou em provider error e, da mesma forma, é excluída dos agregados de qualidade.

## Resultados observados no nível de arquitetura

Métricas de qualidade são calculadas somente sobre células bem-sucedidas (`status=ok`).

| Padrão | Observado | Grounding médio | Causal overclaims |
| --- | ---: | ---: | ---: |
| Augmented | 10/12 | 97.8% | 3 |
| Chaining | 9/12 | 74.4% | 5 |
| Routing | 10/12 | 92.8% | 2 |
| Parallel | 10/12 | 94.9% | 7 |
| Evaluator-optimizer | 10/12 | 97.6% | 4 |
| Agent | 10/12 | 95.4% | **0** |

Esses resultados são descritivos porque o experimento usa `n=1` por célula. Eles não estabelecem significância estatística nem rankings universais de arquitetura.

## Observações mais fortes

- bounded tool-using agency foi o único padrão com zero causal overclaims detectados em todas as células breadth observáveis;
- chaining mostrou o grounding agregado mais fraco e trade-off ruim de custo/latência;
- parallelization preservou grounding relativamente alto, mas produziu o maior número de causal overclaims;
- evaluator-optimizer exibiu comportamento adaptativo de revisão, mas quality passes internos não garantiram correção causal externa;
- routing expôs seleção de control flow dependente de provider/modelo;
- grounding e autoridade causal permaneceram dimensões distintas de avaliação;
- detecção lexical de linguagem de incerteza saturou nas células bem-sucedidas e não é interpretada como correção epistêmica.

O resultado não deve ser resumido como “agentes são melhores”.

A hipótese suportada, mais restrita, é que uso limitado de ferramentas pode ajudar na aquisição de evidência e contenção causal quando o agente opera dentro de limites explícitos de ferramentas read-only, ações e execução.

## Execução

Use o comando de benchmark existente com `--all-incidents`:

```bash
uv run autonomy-lab benchmark \
  --all-incidents \
  --runs 1 \
  --output results/breadth-<provider> \
  --run-interval-seconds <provider-appropriate-interval>
```

O runner faz preflight de cada output de incidente antes de qualquer execução de padrão. A ordem dos padrões é rotacionada deterministicamente entre incidentes para que a mesma arquitetura não ocupe sempre a primeira ou a última posição de tentativa.

Chamadas internas de cada padrão permanecem inalteradas: o fan-out de parallel continua concorrente e workflows com múltiplas chamadas preservam sua topologia original. Não existem retries ocultos.

## Artefatos

Cada incidente recebe o conjunto de artefatos de benchmark inalterado:

```text
INC-xxx/runs.jsonl
INC-xxx/summary.csv
INC-xxx/summary.md
```

A raiz do experimento também recebe `breadth-manifest.json`, contendo metadados de reprodutibilidade e métricas agregadas por padrão.

Nenhum prompt, resposta de modelo, corpo de evidência, argumento/resultado de ferramenta ou credencial é persistido.

Gerações históricas de calibração são mantidas separadas e não são recombinadas com a geração breadth principal.

## Limite experimental

O benchmark repetido histórico permanece congelado em:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

e usa `INC-001`.

A geração breadth é congelada separadamente em:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Resultados cross-provider continuam sendo comparações de bundles provider/modelo/API/configuração em vez de um leaderboard puro de modelos.

## Resultados

A análise breadth completa — incluindo disponibilidade antes de qualidade, observações por provider, distribuição de causal overclaims, trajetórias de routing, revisões do evaluator-optimizer, trajetórias do bounded agent, trade-offs de eficiência, saturação da métrica de incerteza, ameaças à validade e não-afirmações explícitas — está documentada em:

[`MULTI_INCIDENT_BREADTH_RESULTS.md`](MULTI_INCIDENT_BREADTH_RESULTS.md)

# Geração de Benchmark Epistêmico v2

> **Idioma:** Português (Brasil) · [Original em inglês](../EPISTEMIC_BENCHMARK_GENERATION_V2.md)

## Status

Este documento define o protocolo da próxima geração de benchmark após o Epistemic Evaluation v4.1.

O PR de implementação que introduz esse runner não deve, por si só, ser tratado como uma geração live de benchmark. Chamadas a providers começam somente depois que a implementação estiver mergeada, o quality gate estiver verde e um novo commit de freeze for selecionado explicitamente.

Os outputs históricos de benchmark permanecem inalterados.

---

## Propósito

A geração histórica breadth registrava metadados do Grounding Evaluation v1, incluindo o campo lexical `uncertainty_preserved`.

Epistemic Benchmark v2 adiciona metadados conscientes de postura sem reter as respostas completas dos modelos.

Cada célula v2 bem-sucedida pode registrar:

- postura de evidência esperada;
- veredicto epistêmico;
- flag alinhado/não alinhado;
- detecção de afirmação causal direta;
- detecção de linguagem causal qualificada;
- detecção de abstention explícita;
- detecção de linguagem de incerteza;
- a contagem de causal overclaims já existente no Grounding v1.

A resposta em si continua não sendo persistida nos artefatos do benchmark.

---

## Proveniência de schema

Novos artefatos declaram sua proveniência explicitamente:

```text
record schema:        benchmark-record-v2
summary schema:       benchmark-summary-v2
breadth manifest:     breadth-v2
grounding evaluator:  grounding-v1
epistemic evaluator:  epistemic-v4.1
```

Um registro `benchmark-record-v2` pode ter `epistemic_evaluation_version = null` quando produzido pelo runner histórico de benchmark sem o novo evaluator.

O runner dedicado da geração v2 sempre configura:

```text
epistemic_evaluation_version = epistemic-v4.1
```

e recusa combinações incompatíveis de callback/versão antes das chamadas ao provider.

---

## Runner dedicado

A nova geração usa um entrypoint de console separado:

```bash
uv run autonomy-lab-epistemic-benchmark
```

Isso é intencionalmente separado do comando histórico `autonomy-lab benchmark` para que um novo evaluator não seja introduzido silenciosamente em um protocolo experimental antigo.

Incidente único:

```bash
uv run autonomy-lab-epistemic-benchmark \
  --incident INC-004 \
  --runs 1 \
  --output results/epistemic-v4-1-inc004
```

Suíte breadth canônica:

```bash
uv run autonomy-lab-epistemic-benchmark \
  --all-incidents \
  --runs 1 \
  --output results/epistemic-v4-1-breadth
```

A suíte breadth preserva os quatro incidentes canônicos e rotaciona o primeiro padrão por incidente.

---

## Procedimento de freeze

Antes de qualquer execução paga/com provider:

```bash
git status --short
git rev-parse HEAD
```

A worktree deve estar limpa e o commit selecionado deve ser registrado como freeze da geração.

Para proveniência explícita, o runner também suporta o override de ambiente já usado pela coleta de metadados do benchmark:

```bash
export AUTONOMY_LAB_GIT_COMMIT="$(git rev-parse HEAD)"
```

Configurações de provider/modelo/tokens/timeout/intervalo devem ser congeladas por geração. API keys permanecem locais e nunca devem ser commitadas.

---

## Disponibilidade não é qualidade

O manifest v2 contabiliza estes resultados separadamente:

- `ok`;
- `rate_limited`;
- `provider_error`;
- `bound_exceeded`.

Somente células `status=ok` podem carregar veredictos de qualidade de grounding ou epistemic.

Rate limits, provider errors e esgotamento de limites do bounded agent são evidência de disponibilidade/runtime. Eles não recebem zeros imputados de qualidade.

Uma célula com falha preserva a proveniência da versão do evaluator, mas não possui veredicto epistêmico.

---

## Agregados epistêmicos

Resumos por padrão incluem:

- `epistemic_evaluated`;
- `epistemic_aligned`;
- `epistemic_alignment_rate`;
- `epistemic_overclaimed`;
- `epistemic_over_hedged`;
- `epistemic_insufficient_abstention`;
- `epistemic_no_position`.

O denominador de alignment rate usa somente células que realmente possuem um veredicto epistêmico.

Não inclua falhas de provider ou bound exhaustion nesse denominador.

---

## Limite da geração

Não acrescente veredictos v2 às linhas congeladas breadth-v1 como se o evaluator já existisse no momento daquela geração.

Não combine gerações anteriores e posteriores a uma correção.

Não reexecute somente células com falha e depois apresente o conjunto misturado como uma única geração homogênea.

Se um defeito real do runner ou evaluator for descoberto durante uma geração live:

1. preserve o output observado;
2. interrompa a interpretação;
3. corrija o defeito em branch/PR separado com cobertura de regressão;
4. faça merge somente após revisão;
5. selecione um novo commit de freeze;
6. reexecute todo o experimento pretendido como uma nova geração.

---

## Recomendação para a primeira execução live

O primeiro experimento v2 com provider deve permanecer descritivo e pequeno:

```text
4 incidents × 6 patterns × 1 run × provider bundles
```

O objetivo não é reproduzir um leaderboard de modelos. É testar se uma avaliação consciente de postura muda o que a comparação de arquiteturas revela, especialmente para:

- correlação sem causalidade confirmada (`INC-001`);
- causas confirmadas (`INC-002`, `INC-003`);
- abstention obrigatória (`INC-004`).

Com `n=1` por célula, os achados permanecem evidência descritiva, não afirmações de significância estatística.

# Matriz de Claim Judge rotulada por humanos

> **Idioma:** Português (Brasil) · [Original em inglês](../CLAIM_JUDGE_MATRIX.md)

## Propósito

A claim judge matrix avalia a política atual de avaliação de claims contra um pequeno conjunto estático de casos rotulados por humanos.

Isso é deliberadamente diferente do benchmark de arquitetura com seis padrões:

- o benchmark de arquitetura mede comportamento de execução live;
- a claim matrix mede o comportamento do evaluator sobre claims fixas;
- o label humano é a referência de cada linha da matriz;
- um LLM judge é uma fonte opcional de predição, **não** ground truth.

Nenhum padrão de arquitetura é reexecutado e nenhum artefato histórico de benchmark é reclassificado.

## Dataset v1

O conjunto empacotado é:

```text
name:        inc-001-claim-calibration
version:     v1
incident:    INC-001
cases:       18
```

Distribuição de labels:

| Label humano | Casos |
| --- | ---: |
| `SUPPORTED_FACT` | 5 |
| `SUPPORTED_INFERENCE` | 2 |
| `PROPOSED_ACTION` | 3 |
| `UNSUPPORTED_CLAIM` | 8 |

Os casos cobrem:

- medições exatas suportadas e fatos de deployment;
- polaridade de negação;
- paráfrases históricas;
- inferência qualificada;
- incerteza causal explícita;
- contexto de proposta/ação;
- novos parâmetros propostos;
- rejeição causal explícita;
- versões, timestamps e medições inventadas;
- associações falsas entre horário e medição;
- afirmações causais não suportadas;
- hipóteses sem âncora;
- inversões de polaridade;
- armadilhas de contexto histórico.

O dataset está em `src/autonomy_lab/evals/labelled_claims_v1.json` e é validado no carregamento. IDs de caso devem ser únicos e todo label esperado deve mapear para a taxonomia limitada `ClaimKind`.

## Baseline determinístico

O Claim Evaluation v2 determinístico atual produz:

```text
exact-label matches:       15 / 18
exact-label accuracy:      83.3%
false rejections:           1
false upgrades:             2
authority false positives:  2
```

As três divergências são mantidas intencionalmente porque expõem limitações diferentes do evaluator.

### 1. Paráfrase histórica — falsa rejeição conservadora

Label humano:

```text
SUPPORTED_FACT
```

Claim:

```text
A prior incident had similar symptoms from an upstream timeout mismatch,
but that is only historical context.
```

Resultado determinístico:

```text
UNSUPPORTED_CLAIM
```

Essa é a limitação esperada de um evaluator lexical conservador. A claim é semanticamente suportada por `previous-incidents`, mas o baseline determinístico não finge realizar entailment geral.

Essa linha **é elegível** para avaliação semântica seletiva.

### 2. Associação falsa entre horário e medição — falso positivo de autoridade

Label humano:

```text
UNSUPPORTED_CLAIM
```

Claim:

```text
At 14:05, p95 latency was 2,840 ms.
```

Resultado determinístico:

```text
SUPPORTED_FACT
```

Tanto `14:05` quanto `2,840 ms` existem em algum lugar do fixture, mas a associação entre eles é falsa. Grounding v1 verifica atualmente esse erro relacional em estruturas limitadas de tabelas Markdown, não em qualquer construção em prosa.

Como o resultado determinístico já é suportado, a política atual de autoridade unidirecional **não envia essa linha ao semantic judge**.

### 3. Contexto histórico usado como causa atual — falso positivo de autoridade

Label humano:

```text
UNSUPPORTED_CLAIM
```

Claim:

```text
INC-884 proves the current incident was caused by an upstream timeout mismatch.
```

Resultado determinístico:

```text
SUPPORTED_INFERENCE
```

A claim contém vocabulário de evidência histórica e contexto semelhante a inferência, o que é suficiente para o caminho atual de ancoragem lexical, embora a afirmação promova indevidamente contexto histórico a causalidade do incidente presente.

Novamente, o resultado determinístico já é suportado, portanto o semantic judge não pode contestá-lo sob a política atual.

## Por que `authority_false_positives` importa

O invariante de autoridade v2.1/v2.2 protege falhas determinísticas rígidas:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

Essa assimetria é útil porque um LLM judge não pode justificar uma versão inventada ou uma medição não suportada.

O conjunto rotulado mostra o outro lado do mesmo design:

```text
deterministic supported result
        ↓
semantic evaluation skipped
        ↓
false positive cannot be corrected downstream
```

A matriz, portanto, acompanha `authority_false_positives` explicitamente em vez de reportar apenas acurácia agregada.

Esse é um sinal de design mais forte do que simplesmente perguntar se um semantic judge aumenta uma pontuação. Ele identifica onde a autoridade determinística é confiável e onde o próprio limite rígido pode precisar de uma regra determinística mais precisa.

## Teste de regressão semântico

A suíte de unit tests inclui um semantic test double determinístico. Ele **não é um benchmark de modelo**.

O test double:

- promove a paráfrase histórica para `SUPPORTED_FACT` usando `previous-incidents`;
- rejeita outras claims não suportadas elegíveis;
- não pode tocar em falhas determinísticas rígidas nem em resultados determinísticos já suportados.

Nesse teste controlado:

```text
deterministic:              15 / 18 = 83.3%
final after semantic merge: 16 / 18 = 88.9%
corrected by semantic:       1
regressed by semantic:       0
remaining false upgrades:    2
```

Os dois erros restantes são os falsos positivos de autoridade acima. O teste demonstra o comportamento da política de merge, não a qualidade de um modelo semântico.

## Calibração live com Anthropic

Uma matriz live limitada foi executada com Anthropic como semantic judge independente:

```text
provider:     anthropic
model:        claude-sonnet-5
max tokens:   1000
cases:        18
```

Resultado observado:

```text
deterministic:              15 / 18 = 83.3%
final after semantic merge: 16 / 18 = 88.9%
semantic evaluated:          3
semantic disagreements:      1
corrected by semantic:       1
regressed by semantic:       0
false upgrades:              2
false rejections:            0
authority false positives:   2
semantic model calls:        3
semantic input tokens:       1928
semantic output tokens:      254
```

Claude promoveu apenas a paráfrase histórica de `UNSUPPORTED_CLAIM` para `SUPPORTED_FACT`, citando `previous-incidents`. Manteve como não suportadas a hipótese sem âncora de memory leak e a inversão de polaridade sobre outage.

Os dois erros finais permaneceram porque ambos são falsos positivos de autoridade já suportados pela camada determinística e, por isso, nunca chegaram ao judge. Esse resultado live reproduz o teste controlado da política de merge sem transformar o veredicto do modelo em ground truth.

### Regressão descoberta no live smoke durante a calibração com Anthropic

O smoke do bounded agent com Anthropic também expôs um falso positivo do Grounding v1 em linguagem procedural:

```text
... confirm whether reverting resolves the issue before declaring root cause.
```

A frase foi sinalizada incorretamente porque o matcher lexical de causalidade identificou `root cause`, mesmo a sentença explicitamente adiando qualquer declaração de causa raiz até depois da validação.

O evaluator agora trata construções restritas `before declaring|claiming|concluding` como linguagem de guardrail causal não assertiva. Um teste de regressão preserva os dois lados do limite:

```text
before declaring root cause
→ not an overclaim

The deployment is the root cause of the incident.
→ remains fail-closed
```

O smoke original da Anthropic é anterior a essa correção determinística, então sua contagem global de causalidade registrada não deve ser interpretada como o resultado do evaluator corrigido.

## Nota sobre a execução Anthropic 5×6

Uma execução completa de arquitetura Anthropic 5×6 também concluiu com sucesso usando `claude-sonnet-5`:

| Padrão | Sucesso | Latência p50 | Grounding |
| --- | ---: | ---: | ---: |
| augmented | 5/5 | 15,219.1 ms | 93.3% |
| chaining | 5/5 | 39,367.7 ms | 87.7% |
| routing | 5/5 | 13,766.0 ms | 84.6% |
| parallel | 5/5 | 36,756.8 ms | 93.4% |
| evaluator-optimizer | 5/5 | 16,560.5 ms | 100.0% |
| agent | 5/5 | 16,829.7 ms | 92.2% |

As 30 execuções concluíram sem rate limits ou provider errors.

Essa execução foi feita no commit `521dd029a93b866a0955a29f32c2744fcfe57874`, não no commit histórico congelado usado na comparação OpenAI/Groq de 60 execuções. Portanto, é preservada como evidência Anthropic para aquela revisão, **não** mesclada em uma tabela comparativa apples-to-apples entre três providers. Uma nova execução Anthropic no commit congelado é necessária antes de fazer afirmações comparativas diretas contra os resultados históricos de OpenAI/Groq.

## Métricas

Cada execução da matriz expõe:

- matches exatos de label e acurácia determinística;
- matches exatos de label e acurácia final;
- número de linhas realmente enviadas ao semantic judge;
- divergências determinístico-versus-semântico;
- perdas determinísticas corrigidas por avaliação semântica;
- resultados determinísticos corretos regredidos pela avaliação semântica;
- false upgrades;
- false rejections;
- authority false positives;
- chamadas do modelo semântico;
- tokens semânticos de entrada/saída.

Cada linha também preserva:

- label humano;
- kind determinístico, rationale e fontes de evidência candidatas;
- kind semântico opcional, rationale e fontes de evidência;
- kind final;
- divergência e resolução.

Isso torna as métricas agregadas auditáveis no nível individual de claim.

## Execução determinística

Nenhuma chave de provider ou chamada live de modelo é necessária:

```bash
uv run python -m autonomy_lab.claim_matrix_cli --json
```

Saída legível por humanos:

```bash
uv run python -m autonomy_lab.claim_matrix_cli
```

## Semantic judge opcional

A avaliação semântica é opt-in e reutiliza a configuração `SEMANTIC_*` existente.

Exemplo com Groq:

```bash
export SEMANTIC_LLM_PROVIDER=groq
export SEMANTIC_GROQ_MODEL=openai/gpt-oss-20b
export SEMANTIC_LLM_MAX_TOKENS=600
export SEMANTIC_LLM_TIMEOUT_SECONDS=30

uv run python -m autonomy_lab.claim_matrix_cli \
  --semantic \
  --json
```

Exemplo com Anthropic:

```bash
export SEMANTIC_LLM_PROVIDER=anthropic
export SEMANTIC_CLAUDE_MODEL=claude-sonnet-5
export SEMANTIC_LLM_MAX_TOKENS=1000
export SEMANTIC_LLM_TIMEOUT_SECONDS=60

uv run python -m autonomy_lab.claim_matrix_cli \
  --semantic \
  --json
```

Se a API key específica do provider já estiver disponível, a credencial semântica namespaced é opcional porque a configuração semântica faz fallback para a chave daquele provider.

Uma falha de configuração/provider/schema do judge retorna exit code `2`, preservando o baseline determinístico na saída.

## Regras de interpretação

Não interprete uma acurácia merged maior como prova de que um judge é confiável.

Uma calibração semântica útil deve inspecionar ao menos:

1. quais linhas eram elegíveis para avaliação semântica;
2. se as divergências foram correções ou regressões em relação ao label humano;
3. se linhas não suportadas foram falsamente promovidas;
4. se linhas suportadas foram falsamente rejeitadas;
5. se os erros restantes são, na prática, inalcançáveis por causa da política de autoridade determinística.

Uma matriz de judge cross-provider pode comparar comportamento de evaluator, mas não é um leaderboard de modelos. Provider/modelo, configuração de reasoning, transporte, orçamento de output e comportamento de seguimento de prompt continuam fazendo parte do bundle avaliado.

## Principal achado atual

O conjunto rotulado v1 muda a pergunta de avaliação de:

> Um semantic judge consegue corrigir perdas determinísticas conservadoras?

para a pergunta mais útil:

> Quais decisões determinísticas devem ser autoritativas, e quais decisões precisam de um caminho de contestação?

A política atual lida bem com detalhes rígidos não suportados, mas o conjunto rotulado demonstra que **falsos positivos determinísticos são mais perigosos do que falsos negativos determinísticos sob escalonamento semântico unidirecional**, porque falsos negativos podem ser revisados seletivamente enquanto falsos positivos são aceitos como finais.

A calibração live com Anthropic reforça o mesmo achado: um judge independente capaz corrigiu a única perda conservadora elegível sem regressões, mas não pôde tocar nos dois falsos positivos já suportados deterministicamente porque a política de autoridade nunca expôs essas linhas à revisão semântica.

Esse achado deve orientar a próxima mudança do evaluator antes de ampliar a complexidade do semantic judge.

## Próxima calibração

A próxima calibração específica do benchmark é uma nova execução Anthropic no mesmo commit congelado usado pelo benchmark histórico OpenAI/Groq. Essa execução deve permanecer separada do trabalho da claim matrix e usar semântica de benchmark idêntica antes de qualquer comparação entre três providers ser publicada.

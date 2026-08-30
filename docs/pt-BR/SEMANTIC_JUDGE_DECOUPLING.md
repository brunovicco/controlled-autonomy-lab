# Desacoplamento do Semantic Judge v2.2

> **Idioma:** Português (Brasil) · [Original em inglês](../SEMANTIC_JUDGE_DECOUPLING.md)

Semantic Judge Decoupling v2.2 separa geração de resposta do julgamento semântico de claims sem alterar o modelo de autoridade determinística introduzido no v2.1.

O objetivo não é criar uma nova pontuação de benchmark. É tornar observável a divergência entre gerador e judge, preservando falhas rígidas do Grounding v1 e mantendo a pós-análise semântica fora dos artefatos metadata-only do benchmark.

## Por que desacoplar o judge

v2.1 provou que semantic escalation seletivo consegue resolver perdas determinísticas conservadoras, mas sua calibração live usou o mesmo modelo OpenAI para gerar e julgar a resposta. Isso cria viés de self-judge: o modelo pode ser mais propenso a aceitar sua própria redação ou raciocínio.

v2.2 permite que um provider/modelo diferente julgue a resposta gerada, para que o sistema observe:

```text
generator result
      ↓
deterministic evaluation
      ↓
eligible conservative miss
      ↓
independent semantic judge
      ↓
merged result + disagreement
```

Isso continua sendo calibração, não ground truth. Um segundo modelo pode divergir por boas ou más razões.

## Invariante de autoridade

O modelo de autoridade v2.1 não muda:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

O semantic judge pode avaliar apenas perdas determinísticas conservadoras já elegíveis sob v2.1. Ele não pode:

- sobrescrever medições, versões, associações não suportadas ou falhas causais rígidas;
- rebaixar suporte determinístico;
- reclassificar ações propostas;
- adicionar claims ou texto semântico aos artefatos metadata-only do benchmark.

## Configuração de provider

As configurações do gerador continuam usando as variáveis existentes:

```text
LLM_PROVIDER
LLM_MAX_TOKENS
LLM_TIMEOUT_SECONDS
<provider model/key variables>
```

O semantic judge pode sobrescrevê-las no namespace `SEMANTIC_`:

```text
SEMANTIC_LLM_PROVIDER
SEMANTIC_LLM_MAX_TOKENS
SEMANTIC_LLM_TIMEOUT_SECONDS
SEMANTIC_OPENAI_MODEL
SEMANTIC_GROQ_MODEL
SEMANTIC_CLAUDE_MODEL
SEMANTIC_OPENROUTER_MODEL
```

Credenciais de provider também podem ser namespaced, por exemplo `SEMANTIC_GROQ_API_KEY`. A credencial namespaced é opcional: se omitida, o judge faz fallback para a chave já existente do provider, como `GROQ_API_KEY`.

Se nenhum override `SEMANTIC_*` for fornecido, v2.2 preserva o comportamento do v2.1 e reutiliza o provider/modelo do gerador. O output de calibração marca isso explicitamente como `self_judge: true`.

Nenhuma API key é incluída em `ProviderSelection`, output de calibração ou traces de metadados.

## Comando de calibração cross-model

A superfície de calibração desacoplada é intencionalmente separada de `autonomy-lab benchmark`:

```bash
uv run python -m autonomy_lab.semantic_judge_cli agent \
  --incident INC-001 \
  --json
```

O comando executa um padrão com o gerador e depois roda Grounding v1, Claim Evaluation v2 determinístico e o merge semântico v2.1 usando o judge configurado separadamente.

O output JSON inclui identidades não secretas:

```json
{
  "generator": {
    "provider": "openai",
    "model": "gpt-5.6-luna",
    "max_tokens": 4000,
    "timeout_seconds": 60.0
  },
  "judge": {
    "provider": "groq",
    "model": "openai/gpt-oss-20b",
    "max_tokens": 600,
    "timeout_seconds": 30.0
  },
  "self_judge": false
}
```

`model_calls`, uso de tokens, latência e trajetória do padrão continuam sendo métricas de execução do gerador. Chamadas e tokens semânticos permanecem em `semantic_claim_evaluation` e não são somados aos totais de execução do padrão.

## Comportamento em falhas

Falhas do gerador preservam o comportamento já existente para provider/rate limit.

Falhas do judge são falhas de análise pós-execução. A resposta bem-sucedida do gerador é preservada e o comando retorna exit code `2` quando o judge apresenta:

- configuração inválida/ausente;
- provider error;
- rate limit;
- JSON semântico malformado ou sem limites.

Uma falha do judge não é convertida em veredicto de claim.

## Smoke cross-model

A primeira calibração live cross-model usou:

- gerador: OpenAI `gpt-5.6-luna`;
- judge: Groq `openai/gpt-oss-20b`;
- max output tokens do gerador: `4000`;
- max output tokens do judge: `600`;
- `self_judge: false`.

O bounded agent concluiu com sucesso usando a trajetória esperada de seis passos, cinco chamadas de ferramentas e duas chamadas do modelo gerador. Grounding v1 reportou 100% de specific grounding, zero detalhes não suportados, zero detalhes propostos, zero causal overclaims e incerteza preservada.

O evaluator determinístico deixou a paráfrase do incidente histórico como a única candidata semântica conservadora comum. GPT-OSS julgou essa claim como `SUPPORTED_FACT` usando `previous-incidents`, produzindo uma divergência semântica e um semantic upgrade. O uso semântico permaneceu separado da geração:

- semantic model calls: `1`;
- semantic input tokens: `458`;
- semantic output tokens: `254`.

Isso confirma o principal objetivo de infraestrutura do v2.2: geração e julgamento semântico podem usar providers/modelos diferentes, a identidade do judge é explícita, self-judging está desabilitado e o custo semântico permanece observável de forma independente.

### Bug de calibração exposto pelo primeiro smoke

A mesma execução também expôs uma inconsistência do evaluator não relacionada ao judge Groq. A resposta dizia que a evidência disponível **não prova** que o deployment causou o incidente. Grounding v1 sobre a resposta inteira reportou corretamente zero causal overclaims, mas Claim Evaluation em nível de sentença inicialmente reexecutou Grounding v1 sobre essa sentença e a marcou como `grounding-v1-causality-overclaim:1`.

A causa era uma detecção de incerteza sensível à granularidade: Grounding sobre a resposta inteira via o qualificador `leading hypothesis` na mesma linha de parágrafo, enquanto o claim evaluator dividia o parágrafo em sentenças. O vocabulário de incerteza reconhecia `not proven`, mas não a forma igualmente explícita `does not prove`.

O claim evaluator determinístico agora inclui uma regra restrita de incerteza causal explícita para formas como `not prove`, `not proved`, `not proven`, `cannot prove` e `can't prove`. Essas formas:

- impedem falso hard failure causal no nível da sentença;
- qualificam a claim como inferência quando existem âncoras de evidência;
- **não** enfraquecem o comportamento fail-closed existente para linguagem não qualificada como `The deployment caused the incident.`

Um teste de regressão congela exatamente a sentença causal observada no primeiro smoke cross-model. A classificação determinística corrigida é `SUPPORTED_INFERENCE` com âncoras de evidência de deployment/dependency, enquanto o teste original de causal overclaim não qualificado continua fail-closed.

## Segundo smoke cross-model

Uma segunda execução live repetiu o mesmo split de providers após a correção da incerteza causal em nível de sentença:

- gerador: OpenAI `gpt-5.6-luna`;
- judge: Groq `openai/gpt-oss-20b`;
- `self_judge: false`;
- generator model calls: `2`;
- tool calls: `5`;
- semantic model calls: `1`;
- semantic input tokens: `458`;
- semantic output tokens: `306`;
- semantic disagreements: `1`;
- final semantic support ratio: `1.0`.

A paráfrase do incidente histórico novamente permaneceu como a única candidata semântica conservadora comum e GPT-OSS novamente a promoveu para `SUPPORTED_FACT` usando `previous-incidents`. Isso é evidência repetida útil de calibração do caminho desacoplado, mas ainda não é estimativa de acurácia do judge.

### Falso positivo de rejeição causal exposto pelo segundo smoke

A segunda resposta continha a recomendação:

```text
Avoid treating the historical incident as confirmation of the current root cause.
```

Grounding v1 inicialmente encontrou `root cause` e reportou causal overclaim, embora a sentença explicitamente rejeitasse essa conclusão. Claim Evaluation tratou corretamente a sentença como ação proposta, tornando a divergência visível.

Grounding v1 agora reconhece um conjunto deliberadamente restrito de formas explícitas de rejeição causal, incluindo `avoid treating`, `avoid assuming`, `do not treat`, `do not assume`, `never claim` e variantes limitadas relacionadas. Isso impede que linguagem consultiva que rejeita uma conclusão causal seja contabilizada como a própria conclusão.

A correção **não** desabilita verificações de causalidade apenas porque o texto aparece sob um heading de recomendação. Uma afirmação não qualificada como:

```text
The deployment is the root cause of the incident.
```

continua produzindo causal overclaim. Tanto a sentença observada de rejeição quanto o controle não qualificado estão congelados como testes de regressão.

O quality gate do projeto após essa correção passa com 122 testes, além de Ruff lint/format, validação de arquitetura, MyPy strict, Bandit e pip-audit.

Nenhuma chamada adicional a provider é necessária para validar essa segunda correção determinística: os dois smokes live OpenAI→Groq já validaram o comportamento desacoplado de transporte/routing, enquanto a correção em si é determinística e coberta por regressão.

## Reprodução

```bash
set -a
source .env
set +a

export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-5.6-luna
export LLM_MAX_TOKENS=4000
export LLM_TIMEOUT_SECONDS=60

export SEMANTIC_LLM_PROVIDER=groq
export SEMANTIC_GROQ_MODEL=openai/gpt-oss-20b
export SEMANTIC_LLM_MAX_TOKENS=600
export SEMANTIC_LLM_TIMEOUT_SECONDS=30

uv run python -m autonomy_lab.semantic_judge_cli agent \
  --incident INC-001 \
  --json

echo $?
```

Se `GROQ_API_KEY` já estiver carregada, uma `SEMANTIC_GROQ_API_KEY` separada não é necessária.

O veredicto semântico deliberadamente não é predeterminado para respostas futuras. Concordância ou divergência entre avaliação determinística do lado do gerador e um judge independente é evidência de calibração, e não critério de sucesso por si só.

## Limite de interpretação

Um único par gerador/judge em um incidente não consegue estabelecer acurácia do evaluator. Em particular:

- nenhum dos modelos é ground truth;
- uma única classe semântica é insuficiente para estimar precision ou recall do judge;
- tamanho do modelo judge, transporte, comportamento de reasoning e orçamento de output diferem;
- concordância cross-model ainda pode estar conjuntamente errada;
- divergência exige inspeção contra fixtures estáticos rotulados por humanos.

O propósito mais forte do v2.2 é, portanto, arquitetural e metodológico: tornar explícita a identidade do judge, separar seu custo da geração, remover self-judging implícito e expor divergência para calibração posterior.

## Fora do escopo de v2.2

Esta fase deliberadamente não adiciona:

- métricas semânticas aos benchmarks repetidos de arquitetura;
- leaderboard de model-as-judge;
- consenso automático entre múltiplos judges;
- retries para falhas do judge;
- texto semântico de claims aos traces metadata-only;
- qualquer mecanismo que sobrescreva falhas rígidas genuínas do Grounding v1.

Uma fase futura pode adicionar um conjunto estático rotulado de claims e executar uma matriz gerador × judge para medir agreement, false upgrades, false rejections e viés cross-model sem consumir novas execuções de arquitetura.

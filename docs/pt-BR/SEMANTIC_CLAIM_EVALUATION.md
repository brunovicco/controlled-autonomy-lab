# Semantic Claim Evaluation v2.1

> **Idioma:** Português (Brasil) · [Original em inglês](../SEMANTIC_CLAIM_EVALUATION.md)

Semantic Claim Evaluation v2.1 é uma camada secundária e opt-in de análise para claims que o baseline determinístico v2 deixa deliberadamente como não suportadas porque não consegue realizar entailment semântico.

Ela não substitui Grounding v1 nem Claim Evaluation v2 determinístico.

## Por que esta camada existe

A primeira calibração live do Claim Evaluation v2 produziu um falso negativo útil:

> Um incidente anterior teve sintomas semelhantes por causa de um upstream timeout mismatch, mas isso é contexto histórico — não prova da causa atual.

O fixture limitado declara que `INC-884` teve sintomas semelhantes causados por um upstream timeout mismatch e diz explicitamente que esse contexto histórico não é evidência da causa raiz atual.

Um humano consegue perceber que a resposta do modelo é uma paráfrase fiel. O evaluator determinístico intencionalmente não consegue estabelecer essa equivalência semântica, portanto classifica a claim como `UNSUPPORTED_CLAIM`.

v2.1 adiciona um julgamento semântico limitado para essa classe de perda conservadora.

## Modelo de autoridade

A avaliação semântica é assimétrica. Ela pode melhorar cobertura, mas não pode enfraquecer sinais determinísticos rígidos.

| Resultado determinístico | Avaliação semântica | Autoridade final |
| --- | --- | --- |
| `SUPPORTED_FACT` | ignorada | determinística |
| `SUPPORTED_INFERENCE` | ignorada | determinística |
| `PROPOSED_ACTION` | ignorada | determinística |
| `UNSUPPORTED_CLAIM` com rationale `grounding-v1-*` | ignorada | falha determinística rígida |
| outro `UNSUPPORTED_CLAIM` | elegível | resultado semântico merged |

O invariante central é:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

Um modelo semântico não pode “explicar” ou anular uma versão, medição, associação não suportada ou causal overclaim detectado pelo Grounding v1.

## Contrato semântico limitado

Claims elegíveis são avaliadas uma por vez. O modelo recebe somente:

- o texto da claim;
- os ids das fontes de evidência limitadas;
- os resumos de evidência limitados já disponíveis para o incidente.

O evaluator é instruído a não usar conhecimento externo.

Ele deve retornar exatamente um objeto JSON com estes campos:

```json
{
  "verdict": "supported-fact | supported-inference | unsupported-claim",
  "rationale": "short reason",
  "evidence_sources": ["source-id"]
}
```

O adapter valida:

- JSON exato, e não output envolvido por Markdown;
- nomes exatos de campos;
- conjunto permitido de veredictos;
- rationale não vazio e limitado;
- `evidence_sources` como lista de strings;
- cada source id retornado contra o conjunto limitado fornecido;
- ao menos uma fonte de evidência para um veredicto semântico suportado.

Output semântico malformado ou sem limites é falha de avaliação, não permissão para inferir.

## Pré-filtragem determinística

A calibração live mostrou que nem toda perda determinística precisa de um LLM. Duas claims inicialmente não suportadas eram fatos quase verbatim já presentes na evidência limitada de `deployments` ou `dependencies`:

- o deployment incluiu uma nova configuração de timeout do payment-provider;
- nenhum outage confirmado do payment-provider foi reportado.

O baseline determinístico, portanto, inclui um matcher quase verbatim deliberadamente restrito para paráfrases de alta confiança de deployment/dependency antes do semantic escalation.

Esse matcher preserva polaridade de negação, de modo que uma claim como `confirmed outage` não pode ser aceita a partir de evidência que diz `no confirmed outage`. Ele intencionalmente não cobre `previous-incidents`; evidência histórica permanece conservadora porque confundir uma causa anterior com o incidente atual é um modo de falha materialmente diferente.

A camada semântica fica, portanto, reservada para perdas conservadoras genuinamente ambíguas, em vez de atuar como segunda passagem geral sobre toda claim.

## Output de merge

O resultado v2.1 mantém três camadas visíveis para cada claim:

```text
deterministic result
semantic result (when eligible)
final merged result
```

Também registra:

- `disagreement`;
- `resolution`;
- chamadas do modelo semântico;
- tokens semânticos de entrada;
- tokens semânticos de saída.

Chamadas e tokens semânticos são mantidos separados dos próprios `model_calls` e da contabilidade de tokens do padrão de arquitetura. A avaliação pós-execução, portanto, não reescreve o custo de execução do padrão em estudo.

## Calibração via CLI

Avaliação semântica está disponível apenas em um único `run` e é explicitamente opt-in:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --semantic-claims \
  --json
```

`--semantic-claims` implica `--claims` determinístico; tanto os resultados determinísticos quanto os semânticos merged são retornados.

Uma falha de provider, rate limit ou validação de schema na etapa semântica retorna exit code `2` preservando a execução original bem-sucedida do padrão no output imediato.

## Limite de privacidade e artefatos

A camada semântica processa texto de claims e resumos de evidência, portanto permanece fora dos artefatos metadata-only.

Ela **não** modifica:

- traces de execução metadata-only;
- registros `runs.jsonl` do benchmark;
- `summary.csv`;
- `summary.md`;
- o dataset histórico de 60 execuções.

O trace é registrado a partir de `PatternRun` antes da análise de claims/semântica e continua excluindo respostas de modelos, texto de claims, corpos de evidência, argumentos/resultados de ferramentas e credenciais.

## Modo de calibração e viés de self-judge

A CLI atual reutiliza o provider/modelo já selecionado como `TextModel` semântico. Isso é intencional para uma pequena fatia de calibração v2.1, mas **não é um judge independente** quando o mesmo modelo gerou a resposta.

Isso cria um risco metodológico: um modelo pode ser mais propenso a aceitar sua própria redação ou raciocínio. Portanto:

- resultados semânticos v2.1 são evidência de calibração, não ground truth;
- suporte semântico não deve ser apresentado como score independente de qualidade;
- métricas semânticas não são habilitadas em benchmarks repetidos;
- falhas determinísticas rígidas continuam autoritativas;
- divergências permanecem observáveis.

Uma fase posterior mais forte deve desacoplar geração e avaliação, por exemplo com um provider/modelo evaluator configurado separadamente e calibração cross-model contra fixtures estáticos.

## Resultados de calibração live

Duas execuções live do bounded agent com OpenAI `gpt-5.6-luna` foram usadas para calibrar o contrato v2.1. Ambas preservaram 100% de specific grounding do Grounding v1, não tiveram detalhes não suportados nem causal overclaims, respeitaram o contrato JSON semântico estrito e terminaram com sucesso.

### Primeiro smoke — antes do refinamento determinístico

A resposta gerada produziu três perdas determinísticas conservadoras. A camada semântica promoveu corretamente as três:

1. deployment incluía nova configuração de timeout do payment-provider;
2. não havia outage confirmado do payment-provider;
3. incidente anterior envolvia upstream timeout mismatch e era contexto histórico.

Uso semântico observado:

- semantic model calls: `3`;
- semantic input tokens: `1161`;
- semantic output tokens: `174`;
- disagreements: `3`;
- merged support ratio: `1.0`.

As duas primeiras promoções eram trabalho desnecessário de LLM porque esses fatos já estavam quase verbatim na evidência limitada do incidente atual. Essa observação motivou o refinamento da pré-filtragem determinística acima.

### Segundo smoke — depois do refinamento determinístico

Uma nova resposta foi avaliada após o refinamento. Como o texto da resposta mudou entre as execuções, contagens brutas de claims não são tratadas como comparação pareada antes/depois de qualidade. O segundo smoke é usado apenas para validar routing/seletividade das camadas de avaliação.

O v2 determinístico classificou:

- 4 fatos suportados;
- 3 inferências suportadas;
- 4 ações propostas;
- 1 claim não suportada;
- support ratio `7/8` (`87.5%`).

A única claim não suportada era a paráfrase histórica:

> Um incidente anterior teve sintomas semelhantes envolvendo um upstream timeout mismatch, mas isso é apenas contexto histórico.

O semantic evaluator recebeu somente essa claim, retornou `SUPPORTED_FACT` usando `previous-incidents` e produziu:

- semantic model calls: `1`;
- semantic input tokens: `394`;
- semantic output tokens: `93`;
- disagreements: `1`;
- final supported facts: `5`;
- final supported inferences: `3`;
- final proposed actions: `4`;
- final unsupported claims: `0`;
- merged support ratio: `1.0`.

Isso valida a política de execução pretendida para v2.1: verificações determinísticas resolvem fatos exatos e limitados de alta confiança, falhas rígidas do Grounding v1 permanecem fail-closed e avaliação semântica é invocada apenas para perdas conservadoras que exigem entailment real.

## Limite de interpretação

Os resultados live validam comportamento da implementação, não acurácia geral do semantic evaluator. Em particular:

- o mesmo modelo gerou e julgou a resposta;
- o fixture contém um incidente e uma classe de calibração semântica;
- duas execuções live são insuficientes para conclusões estatísticas;
- `1.0` de merged support ratio não prova que a resposta completa seja universalmente correta;
- semantic upgrades não fazem parte do dataset repetido cross-provider.

A conclusão mais forte suportada é arquitetural: o evaluator pode preservar autoridade determinística enquanto escalona seletivamente claims ambíguas e mantém o custo extra de modelo observável separadamente.

## Fora do escopo de v2.1

Esta fase deliberadamente não adiciona:

- configuração independente de provider/modelo evaluator;
- métricas semânticas aos benchmarks repetidos;
- texto semântico de claims aos artefatos metadata-only;
- dependências NLI ou de embeddings;
- APIs de structured output específicas de provider;
- retries para output malformado do evaluator;
- mecanismo para julgamento semântico sobrescrever falhas rígidas do Grounding v1.

Essas são decisões de design separadas. O próximo passo significativo de avaliação é desacoplar geração do julgamento semântico e calibrar divergência cross-model contra fixtures estáticos.

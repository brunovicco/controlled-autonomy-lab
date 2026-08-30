# Claim Evaluation v2

> **Idioma:** Português (Brasil) · [Original em inglês](../CLAIM_EVALUATION.md)

Claim Evaluation v2 adiciona uma visão em nível de claim sobre as verificações determinísticas já existentes do Grounding v1.

Ele **não** substitui o Grounding v1. As duas camadas respondem perguntas diferentes:

- **Grounding v1:** os detalhes factuais exatos, associações e afirmações causais fortes são suportados pelo fixture limitado?
- **Claim Evaluation v2:** qual é o papel de cada afirmação avaliável: fato suportado, inferência qualificada, ação proposta ou claim não suportada?

A primeira implementação v2 é intencionalmente conservadora e determinística. Ela não chama outro modelo e não afirma fornecer entailment semântico geral.

## Taxonomia

| Tipo | Significado |
| --- | --- |
| `SUPPORTED_FACT` | Uma claim declarativa possui suporte determinístico do fixture e nenhuma falha rígida do Grounding v1. |
| `SUPPORTED_INFERENCE` | Uma inferência/hipótese qualificada está ancorada em evidência limitada e não possui falha rígida do Grounding v1. |
| `PROPOSED_ACTION` | A afirmação é uma recomendação, verificação, mitigação ou outra ação futura, e não um fato observado. |
| `UNSUPPORTED_CLAIM` | O baseline determinístico não consegue suportar a claim, ou o Grounding v1 reporta um detalhe não suportado ou causal overclaim. |

Cada claim extraída recebe exatamente uma dessas classificações.

## Precedência

A classificação é deliberadamente assimétrica:

1. Detectar contexto de proposta/ação. Sob um heading de recomendação/ação, itens de lista são tratados como ações da seção; afirmações imperativas também podem ser ações fora de uma lista.
2. Executar as verificações rígidas do Grounding v1 para não-propostas.
3. Se Grounding v1 reportar um detalhe não suportado, classificar como `UNSUPPORTED_CLAIM`.
4. Se Grounding v1 reportar um causal overclaim, classificar como `UNSUPPORTED_CLAIM`.
5. Reconhecer suporte textual exato no fixture como `SUPPORTED_FACT`, incluindo fatos observados explicitamente negativos como `No confirmed outage.`.
6. Reconhecer uma inferência qualificada somente quando houver uma âncora em fonte de evidência limitada.
7. Reconhecer um fato quando houver suporte determinístico a detalhes exatos.
8. Caso contrário, operar em fail-closed para `UNSUPPORTED_CLAIM`.

Essa ordem importa. Uma recomendação como `Monitor for 15 minutes` pode introduzir legitimamente um novo parâmetro; ela não deve ser tratada como um fato observado de 15 minutos. Por outro lado, um evaluator semântico adicionado posteriormente não pode apagar uma versão, medição ou achado de causalidade determinístico não suportado.

A regra de heading de ação é intencionalmente limitada. Uma conclusão declarativa isolada após uma lista numerada de recomendações não herda `PROPOSED_ACTION` apenas porque o heading mais recente era de recomendação.

## Extração de claims

O baseline extrai afirmações não vazias semelhantes a sentenças preservando o heading atual da seção Markdown. Headings Markdown e headings apenas em negrito não são tratados como claims. Prefixos de bullets e listas numeradas são removidos antes da avaliação, enquanto o extractor preserva se a afirmação original era um item de lista.

O contexto da seção é usado para distinguir áreas como:

- fatos observados;
- hipóteses / assessment;
- recomendações / próximos passos / ações / mitigação.

O extractor é intencionalmente pequeno e determinístico. Não é um parser de discurso de uso geral.

## Âncoras de evidência

No baseline determinístico, uma inferência suportada deve:

- conter linguagem explícita de inferência/incerteza ou aparecer em uma seção de hipótese/assessment; e
- ter sobreposição com ao menos uma fonte de evidência limitada.

Essa âncora de evidência é uma heurística de calibração, não entailment semântico. Ela impede que uma afirmação não relacionada como `A memory leak might explain the incident` seja promovida apenas por usar linguagem cautelosa.

`evidence_sources` deve ser interpretado como **âncoras lexicais candidatas**, não proveniência exata. A heurística atual de overlap pode atribuir excessivamente uma claim a várias fontes quando o vocabulário é compartilhado no fixture. Refinar proveniência é um problema de calibração separado, porque as mesmas âncoras participam do suporte a inferências; um filtro ad hoc de fontes poderia transformar inferências qualificadas válidas em falsos negativos.

## Incerteza explícita e linguagem causal

Grounding v1 trata negação epistêmica explícita como `no confirmed`, `not confirmed`, `unconfirmed` e `no evidence` como sinais de incerteza. Portanto, uma frase como `No confirmed root cause is currently available` não é um causal overclaim apenas por conter lexicalmente `root cause`.

Isso é diferente de uma afirmação causal forte e não qualificada como `The deployment caused the incident`, que continua sendo uma falha rígida do Grounding v1.

Para classificação de claims, evidência negativa exata ainda vence antes da classificação como inferência. `No confirmed outage.` é um fato suportado pelo fixture. Uma conclusão mais ampla como `No confirmed root cause ... is currently available`, que não é texto exato do fixture, mas é epistemicamente qualificada e ancorada em evidência, é classificada como `SUPPORTED_INFERENCE`.

## Support ratio

`support_ratio` é:

```text
supported facts + supported inferences
--------------------------------------
     evaluable non-action claims
```

Ações propostas ficam visíveis, mas são excluídas do denominador.

Se uma resposta contiver somente ações propostas, o ratio é `1.0` por convenção, espelhando o comportamento de denominador vazio já existente no Grounding v1. Os campos de contagem continuam sendo contexto necessário; o ratio nunca deve ser interpretado isoladamente.

## Relação com Grounding v1

O evaluator determinístico v2 compõe o `DeterministicGroundingEvaluator` existente em vez de duplicar sua lógica de detalhes exatos.

Invariante de sinal rígido:

```text
Grounding v1 unsupported specific
            OR
Grounding v1 causality overclaim
            ↓
Claim v2 = UNSUPPORTED_CLAIM
```

Um evaluator semântico futuro pode melhorar cobertura para paráfrases e inferências mais sutis, mas não pode sobrescrever esse invariante.

## Calibração via CLI

Claim Evaluation v2 é inicialmente exposto apenas para execuções individuais:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims
```

Saída JSON:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims \
  --json
```

A resposta JSON inclui um objeto `claim_evaluation` com classificações por claim, contagens agregadas e `support_ratio`.

A flag `--claims` é opt-in. Schemas de benchmark e artefatos experimentais históricos permanecem inalterados nesta fase.

## Fixture de regressão de execução observada

O repositório inclui uma resposta estática capturada de uma execução bem-sucedida do bounded agent com OpenAI `gpt-5.6-luna` para `INC-001`, em `tests/fixtures/observed/`.

Somente o texto da resposta é preservado. O fixture exclui prompts, credenciais, latência, contabilidade de tokens, argumentos/resultados de ferramentas e payloads request/response do provider.

A regressão atualmente congela estas expectativas determinísticas:

- Grounding v1: nenhum detalhe não suportado, nenhum causal overclaim e 100% de specific grounding;
- Claim v2: 4 fatos suportados, 4 inferências suportadas, 4 ações propostas e 1 paráfrase conservadora não suportada;
- 9 claims não-ação avaliáveis, 8 suportadas, produzindo support ratio de `8/9` (aproximadamente `88.9%`);
- a paráfrase sobre incidente histórico permanece não suportada na camada determinística por design, até que um evaluator semântico seja calibrado;
- a conclusão isolada após a lista de recomendações é uma inferência epistemicamente qualificada, não uma ação proposta.

Esse fixture permite que a semântica das claims evolua sem consumir quota de provider em unit tests.

## Limite de metadados e privacidade

A saída por claim contém fragmentos do texto da resposta, portanto **não** é gravada em traces metadata-only nem em artefatos de benchmark.

O limite de metadados existente permanece inalterado:

- sem prompts;
- sem respostas dos modelos;
- sem texto de claims;
- sem corpos de evidência;
- sem argumentos/resultados de ferramentas;
- sem credenciais.

A avaliação de claims é exibida apenas na resposta imediata da CLI quando solicitada explicitamente.

## Limitações conhecidas

O baseline determinístico é deliberadamente conservador:

- overlap lexical de evidência não é NLI;
- âncoras de fontes de evidência podem superatribuir proveniência quando vocabulário é compartilhado entre fontes;
- paráfrases sem suporte exato/específico podem permanecer `UNSUPPORTED_CLAIM`;
- a segmentação de sentenças é intencionalmente limitada;
- o contexto discursivo entre múltiplas sentenças é limitado;
- overlap com fonte de evidência não prova que uma inferência seja logicamente válida;
- um único fixture de incidente não é suficiente para calibrar semântica geral de claims;
- `support_ratio` não é uma pontuação universal de qualidade de resposta.

Essas limitações são preferíveis a apresentar silenciosamente julgamentos semânticos heurísticos como ground truth.

## Camada semântica planejada

Um evaluator semântico posterior deve ser um sinal **secundário**. A política de merge pretendida é:

1. falha determinística rígida sempre vence;
2. ações propostas permanecem separadas de suporte factual;
3. avaliação semântica pode distinguir paráfrases suportadas de claims declarativas não suportadas;
4. avaliação semântica pode refinar suporte a inferências qualificadas;
5. divergências entre evaluators determinístico e semântico permanecem observáveis em vez de serem silenciosamente colapsadas.

Antes de habilitar métricas semânticas de claims em benchmarks repetidos, calibre o evaluator contra fixtures estáticos de execuções observadas para que quota de provider não seja necessária em unit tests.

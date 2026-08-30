# Grounding Evaluation v1

> **Idioma:** Português (Brasil) · [Original em inglês](../GROUNDING.md)

Grounding Evaluation v1 adiciona um sinal determinístico de qualidade à comparação de arquiteturas.

Seu propósito é restrito: identificar detalhes factuais exatos não suportados, distinguir parâmetros de ação propostos, detectar uma classe limitada de associações não suportadas entre timestamp e medição e sinalizar claims causais não qualificadas comparando a resposta do modelo com o fixture limitado de incidente já usado por todos os padrões.

Ele **não** chama outro LLM. O fixture permanece a fonte de verdade.

## Por que começar pelo determinístico

O padrão evaluator-optimizer já demonstra que um LLM evaluator pode aceitar uma resposta que ainda contém detalhes não suportados. Por isso, Grounding Evaluation v1 não usa LLM-as-a-judge como oracle principal.

A primeira versão favorece intencionalmente verificações explicáveis e reproduzíveis:

- versões semânticas como `v2.18.4`;
- timestamps como `14:10`;
- medições e durações como `2840ms`, `2.84 s`, `8.7%`, `3 s` ou `30-60 min`;
- equivalência exata de segundos para milissegundos em medições escalares de tempo;
- aproximações arredondadas explicitamente marcadas quando o valor do fixture arredonda exatamente para a precisão exibida;
- deltas em pontos percentuais deriváveis exatamente das porcentagens do fixture;
- linguagem causal forte sem qualificadores locais ou de seção sobre incerteza;
- afirmações causais sobre incidentes históricos somente quando o mesmo incidente histórico e o detalhe causal são suportados pela evidência do fixture;
- se a resposta preserva linguagem explícita de incerteza;
- associações timestamp-medição em linhas de tabelas Markdown quando o fixture codifica um par exato;
- se um tempo/medição de outro modo não suportado aparece em seção de recomendação/ação em vez de como fato observado.

Spans de timestamp são excluídos do parsing de medições. Isso impede que texto como `13:55 % 5xx = 0.2 %` produza incorretamente uma medição inventada de `55%`.

## Tipos de finding

| Finding | Significado |
| --- | --- |
| `unsupported-version` | uma versão concreta aparece na resposta, mas não no fixture de incidente/evidência |
| `unsupported-time` | um timestamp é apresentado fora de seção de proposta, mas não existe no fixture |
| `unsupported-measurement` | uma medição factual, porcentagem ou duração não está presente nem é explicitamente derivável do fixture |
| `unsupported-association` | valores individualmente suportados são combinados em uma linha de tabela Markdown de uma forma que o fixture não suporta |
| `proposed-parameter` | um timestamp/medição de outro modo não suportado ocorre sob heading de recomendação/ação e é acompanhado separadamente do grounding factual |
| `causality-overclaim` | linguagem causal forte aparece sem qualificador local ou de seção sobre incerteza e sem evidência histórica de suporte |

Exemplos:

```text
v2.18.4       -> supported
v2.18.3       -> unsupported-version
2840ms        -> supported
2 840 ms      -> supported after Unicode normalization
2.84 s        -> supported because it is exactly 2840 ms
~2.8 s        -> supported because 2.84 s rounds to 2.8 s and approximation is explicit
2.8 s         -> unsupported-measurement when presented as an exact observation
1250ms        -> unsupported-measurement
"p95 was 1 s" -> unsupported-measurement
"alert if p95 > 1 s" under Recommended next steps -> proposed-parameter
8.5 pp        -> supported because 8.7% - 0.2% = 8.5 percentage points
```

A normalização de unidades é deliberadamente restrita no v1: segundos escalares são canonicalizados para milissegundos para permitir comparação exata de representações equivalentes. Não é um mecanismo geral de conversão de unidades.

A aproximação também é intencionalmente restrita. Valores são aceitos como representações arredondadas somente quando a resposta os marca explicitamente com token como `~`, `about`, `around`, `roughly`, `approx.` ou `approximately`, e o valor exato do fixture arredonda para a precisão numérica apresentada. Nenhuma tolerância percentual arbitrária é usada.

Versões semânticas concretas continuam verificáveis mesmo dentro de recomendações. Por exemplo, `roll back to v2.18.3` ainda é reportado quando o fixture nunca identifica `v2.18.3` como release anterior disponível.

Da mesma forma, um endpoint inventado de janela de observação continua sendo finding factual. Se o fixture diz apenas que a latência da dependência aumentou pouco depois de `14:00`, uma resposta que apresenta `14:00-14:15` como intervalo observado introduz o endpoint não suportado `14:15`.

O evaluator deduplica detalhes não suportados repetidos para que um valor inventado repetido várias vezes não infle artificialmente a pontuação.

### Valores suportados ainda podem formar uma associação não suportada

Grounding não é apenas um problema de conjunto de valores. Uma execução live com Groq expôs uma linha que colocou o valor suportado `2840ms` no timestamp suportado `14:05`, embora o fixture associe `2840ms` somente a `14:10`. Grounding Evaluation v1 detecta esse caso relacional restrito em tabelas Markdown cuja primeira coluna contém o timestamp da linha.

```text
| 14:10 | p95 latency 2840ms | -> supported association
| 14:05 | p95 latency 2840ms | -> unsupported-association
```

Essa verificação é intencionalmente estrutural. Ela não afirma resolver sentenças temporais ou relacionais arbitrárias em prosa livre. Células que contêm seu próprio timestamp são ignoradas em vez de serem forçadas ao timestamp da linha, e seções de proposta permanecem fora do scoring de associações factuais.

## Parâmetros propostos versus fatos não suportados

Um benchmark não deve tratar todo número novo como fato alucinado. Um modelo pode propor legitimamente uma janela reversível de monitoramento ou um threshold de alerta que não faz parte da evidência do incidente.

Grounding Evaluation v1, portanto, usa estrutura de seção como sinal determinístico. Ele reconhece headings Markdown normais como `## Recommended next steps` e labels de seção apenas em negrito como `**Recommended next steps (all reversible)**`. Sob headings como `Recommended next steps`, `Actions`, `Plan`, `Checks`, `Mitigation` ou `Remediation`, novos horários e medições são classificados como `proposed-parameter`.

Por exemplo:

```text
**Recommended next steps (all reversible)**
Monitor for 15-30 minutes.
Alert if error rate exceeds 5%.
```

Os valores `15-30 minutes` e `5%` ficam visíveis no relatório, mas não reduzem o ratio factual de specific grounding.

Isso é intencionalmente estrutural, não semântico. Uma recomendação em prosa livre fora de uma seção reconhecível ainda pode ser classificada como não suportada no v1.

## Causalidade e incerteza

O fixture do incidente contém deliberadamente correlação sem causalidade comprovada. Grounding Evaluation v1 distingue, portanto, estas formas:

```text
The deployment caused the incident.
```

Isso é reportado como `causality-overclaim`.

```text
## Hypotheses (not proven)
The new timeout is too low, causing downstream timeouts.
```

O heading qualifica explicitamente a seção como hipotética, então a frase causal não é reportada como overclaim.

Da mesma forma:

```text
Hypothesis: the deployment may have caused the increase, but the timing is only correlation.
```

preserva incerteza.

Evidência histórica é tratada separadamente. O fixture para `INC-001` declara que `INC-884` teve sintomas semelhantes causados por um upstream timeout mismatch. Portanto, esta resposta é contexto histórico suportado, e não causal overclaim sobre o incidente atual:

```text
Incident INC-884 had a similar pattern; root cause was an upstream timeout mismatch.
```

A exceção não se baseia apenas no identificador do incidente histórico. O incidente histórico precisa existir no fixture de referência e o detalhe causal após o predicado causal precisa ser suportado pela linha de evidência daquele incidente. Por exemplo, `INC-884 root cause was database corruption` continua sendo `causality-overclaim`, pois essa causa está ausente do fixture.

A verificação causal é intencionalmente conservadora e lexical. Não é um mecanismo geral de inferência em linguagem natural.

## CLI

Avaliar uma única execução live:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding
```

A saída JSON inclui um relatório estruturado de grounding:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding --json
```

Uma falha de provider em um único `run` é retornada sem traceback Python. Um run JSON com rate limit retorna exit code `2` e resultado estruturado como:

```json
{
  "pattern": "agent",
  "incident_id": "INC-001",
  "status": "rate_limited",
  "error": "Groq API returned HTTP 429"
}
```

Se o provider fornecer um header seguro `Retry-After`, o JSON também inclui `retry_after`. Execuções legíveis por humanos reportam a mesma falha de forma concisa em stderr.

`compare` avalia grounding automaticamente para cada arquitetura:

```bash
uv run autonomy-lab compare --incident INC-001
```

A tabela adiciona:

- `unsupported`: número de detalhes factuais ou associações únicas não suportadas;
- `proposed`: número de novos parâmetros de ação acompanhados separadamente;
- `causality`: número de causal overclaims não qualificados;
- `uncertainty`: se linguagem explícita de incerteza foi preservada;
- `status`: `ok`, `rate_limited` ou `provider_error`.

## Comportamento parcial do benchmark

Uma falha de provider em uma arquitetura não deve apagar resultados concluídos das demais. `compare` opera, portanto, em fail-soft no limite do padrão.

Se um provider retornar rate limit, a linha afetada é emitida como:

```text
chaining | - | - | - | - | - | - | - | - | - | rate_limited
```

e o loop continua pelos padrões restantes. Outras falhas de provider aparecem como `provider_error`.

O comando retorna exit code `2` quando ao menos um padrão não pôde concluir. Isso torna um benchmark incompleto observável para scripts/CI enquanto preserva a tabela parcial para análise. Grounding Evaluation v1 deliberadamente não oculta rate limiting com retries automáticos porque atrasos de retry mudariam a semântica de latência do benchmark.

## Ratio de specific grounding

Para relatórios de execução única, o evaluator expõe:

```text
supported factual specifics / (supported factual specifics + unsupported factual specifics or associations)
```

Findings `proposed-parameter` são deliberadamente excluídos desse denominador.

Um valor de `1.0` significa que todo detalhe factual exato e associação estrutural verificados pelo v1 foi suportado ou explicitamente derivável. Isso **não** significa que a resposta inteira esteja factualmente correta.

Esse ratio intencionalmente não é tratado como pontuação universal de qualidade: uma resposta vaga pode conter poucos detalhes verificáveis e ainda obter ratio alto.

## O que v1 não detecta

Grounding Evaluation v1 não é um detector completo de hallucination. Ele não tenta provar:

- correção semântica de toda claim em prosa;
- correção temporal ou relacional arbitrária em prosa livre;
- se uma ação recomendada ou parâmetro proposto é operacionalmente adequado;
- se um componente, ferramenta ou arquitetura recém-proposto é uma boa ideia;
- se uma inferência é logicamente válida quando não contém detalhe exato verificável;
- se uma resposta omitiu evidência importante;
- se um LLM evaluator fez um bom julgamento.

Por exemplo, propor um circuit breaker é uma recomendação, não automaticamente um fato não suportado. Em contraste, declarar `the previous timeout was 3 s` como fato observado é verificável e é reportado quando o fixture não contém esse valor.

## Limite do trace

Findings de grounding são derivados do conteúdo da resposta e mostrados somente no resultado CLI/JSON quando solicitados. Eles não são adicionados ao arquivo de trace metadata-only, que continua excluindo prompts, respostas, corpos de evidência, argumentos/resultados de ferramentas e credenciais.

## Trabalho futuro

Fases futuras podem adicionar classificação semântica de claims, métricas de omission/coverage ou um LLM judge opcional como sinal secundário. Qualquer evaluator baseado em modelo deve permanecer separado das verificações determinísticas do fixture para que divergências entre os dois sejam observáveis, e não escondidas.

# Benchmark Reprodutível v1

> **Idioma:** Português (Brasil) · [Original em inglês](../BENCHMARKING.md)

O Reproducible Benchmark v1 transforma os seis padrões de arquitetura em um experimento repetível sobre o mesmo fixture de incidente.

O benchmark foi criado para responder perguntas práticas como:

- quantas chamadas de modelo/ferramentas cada arquitetura exige;
- como uso de tokens e latência mudam à medida que o controle se desloca para o modelo;
- se maior autonomia melhora ou degrada o grounding determinístico;
- com que frequência rate limits ou outras falhas de provider impedem a conclusão;
- se as trajetórias do agente variam entre execuções repetidas.

Ele não afirma que o resultado de um provider/modelo se generaliza para todos os modelos ou workloads de produção.

## Executar um benchmark

```bash
uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --output results/groq-gpt-oss-20b \
  --run-interval-seconds 30
```

O comando executa os seis padrões uma vez por ciclo. O padrão inicial gira deterministicamente a cada ciclo, para que a mesma arquitetura não seja sempre a primeira ou a última:

```text
cycle 1: augmented -> chaining -> routing -> parallel -> evaluator-optimizer -> agent
cycle 2: chaining -> routing -> parallel -> evaluator-optimizer -> agent -> augmented
cycle 3: routing -> parallel -> evaluator-optimizer -> agent -> augmented -> chaining
...
```

Isso reduz a exposição fixa a drift de quota mantendo o experimento determinístico e reproduzível.

## Semântica de pacing

`--run-interval-seconds` insere uma pausa **entre tentativas do benchmark**.

Ele deliberadamente não limita chamadas dentro de um padrão de arquitetura. Portanto:

- `parallel` mantém seu fan-out concorrente;
- `chaining` mantém suas chamadas internas sequenciais;
- evaluator-optimizer mantém seu loop limitado de revisão;
- o agente mantém seu loop dinâmico de ferramentas/modelo.

Isso preserva o comportamento que está sendo medido. Um `429` do provider que ocorre dentro de um padrão continua sendo evidência do benchmark em vez de ser ocultado por retry implícito ou por uma camada de serialização específica do benchmark.

Não existem retries automáticos no Benchmark v1.

### Calibração do Groq Free Plan

Dois smoke benchmarks live foram executados em 2026-08-26 com `openai/gpt-oss-20b` e `LLM_MAX_TOKENS=900`:

| Intervalo | Padrões concluídos | Resultado |
| --- | ---: | --- |
| `2s` | `2/6` | `augmented` e `chaining` concluíram; os quatro padrões restantes sofreram rate limit |
| `30s` | `6/6` | todos os seis padrões concluíram; exit code do benchmark `0` |

O smoke de 30 segundos concluiu com estes ratios de grounding em execução única: augmented `78.6%`, chaining `20.0%`, routing `84.6%`, parallel `85.7%`, evaluator-optimizer `91.7%` e agent `78.6%`. São observações de calibração com `n=1`, não conclusões comparativas. O resultado baixo de chaining é um sinal para investigação em execuções repetidas, não evidência de que chaining seja intrinsecamente menos grounded.

O mesmo smoke também ilustra por que latência e uso de tokens devem ser interpretados juntos: parallelization usou mais tokens agregados naquela execução e, ainda assim, teve menor tempo de parede que chaining e agent porque seu fan-out é concorrente. Novamente, são necessários ciclos repetidos antes de tratar isso como resultado de arquitetura.

Em 2026-08-26, a tabela pública do Groq Free Plan listava `openai/gpt-oss-20b` com 30 RPM, 1K RPD, 8K TPM e 200K TPD. A Groq também informa que os rate limits se aplicam no nível da organização, que qualquer limite configurado pode ser atingido primeiro e que a página Limits da conta é a fonte de verdade para valores exatos específicos da organização.

Para o workload de seis padrões deste repositório, **30 segundos entre tentativas do benchmark é o ponto de partida conservador recomendado para experimentos no Groq Free Plan**. É uma configuração de benchmark, não um retry automático nem uma garantia. Se o limite específico da organização for diferente ou ainda ocorrer `429`, preserve essa execução como evidência e execute um experimento separado com intervalo maior.

Não reexecute apenas os padrões que falharam para depois inseri-los no benchmark original. Isso mudaria as condições experimentais e distorceria as métricas de confiabilidade.

Referência oficial:

- Groq rate limits: https://console.groq.com/docs/rate-limits

## Proteção da saída

O benchmark grava três arquivos canônicos no diretório de saída selecionado:

```text
results/groq-gpt-oss-20b/
├── runs.jsonl
├── summary.csv
└── summary.md
```

Arquivos canônicos existentes não são sobrescritos por padrão. Use `--overwrite` apenas quando a substituição for intencional:

```bash
uv run autonomy-lab benchmark \
  --runs 5 \
  --output results/groq-gpt-oss-20b \
  --overwrite
```

A verificação de existência acontece antes da execução live dos padrões, de modo que um overwrite acidental não consuma quota do provider primeiro.

## Schema do registro bruto

`runs.jsonl` contém um registro metadata-only para cada tentativa de execução de padrão.

Registros bem-sucedidos incluem:

```text
timestamp_utc
git_commit
provider
model
max_tokens
timeout_seconds
reasoning_effort
run_interval_seconds
incident_id
pattern
run_number
status
model_calls
tool_calls
input_tokens
output_tokens
latency_ms
unsupported_count
proposed_count
causality_overclaims
grounding_ratio
uncertainty_preserved
trajectory
```

Registros de falha preservam a posição no experimento e o resultado do provider. Uma linha com rate limit também pode conter um valor seguro de `retry_after` quando fornecido pelo provider.

O campo `error` contém o erro do provider já redigido conforme imposto pelo limite do adapter; corpos de resposta do provider não são copiados para os artefatos do benchmark.

## Limite metadata-only

Os artefatos do benchmark **não** persistem:

- prompts;
- respostas dos modelos;
- corpos de evidência;
- argumentos ou resultados de ferramentas;
- credenciais.

O grounding é avaliado enquanto a resposta existe em memória de processo, mas somente métricas determinísticas agregadas de grounding são persistidas.

A opção global existente `--trace-file` continua compatível com execuções bem-sucedidas do benchmark e preserva seu contrato metadata-only original.

## Métricas de resumo

`summary.csv` e `summary.md` agregam cada arquitetura de forma independente.

Métricas de confiabilidade usam **todas as tentativas**:

- `completion_rate`;
- `rate_limit_rate`;
- `provider_error_rate`.

Médias de execução e grounding usam **somente execuções concluídas**. Tentativas com falha não recebem artificialmente zero chamadas, zero tokens, zero latência ou zero grounding, pois isso fabricaria medições.

Os agregados atuais incluem:

- média de chamadas de modelo;
- média de chamadas de ferramentas;
- média de tokens de entrada/saída/totais;
- latência p50;
- média de achados factuais não suportados;
- média de parâmetros propostos;
- média de causal overclaims;
- média do ratio de specific grounding;
- taxa de preservação de incerteza;
- trajetórias bem-sucedidas únicas.

Quando ao menos uma tentativa sofre rate limit, `summary.md` declara explicitamente que o rate limit é evidência do benchmark e recomenda intervalo maior apenas em um **experimento separado**.

## Exit codes

Um benchmark completo retorna:

```text
0
```

Se ao menos um padrão tentado for `rate_limited` ou tiver outra falha de provider, todas as tentativas restantes continuam e o benchmark retorna:

```text
2
```

Isso corresponde ao comportamento fail-soft de `compare`.

## Metadados de reprodutibilidade

O Git commit é descoberto sem invocar shell. A ordem de resolução é:

1. `AUTONOMY_LAB_GIT_COMMIT`;
2. `GITHUB_SHA`;
3. a referência local `.git/HEAD`, incluindo packed refs;
4. `unknown` quando nenhum metadado do repositório está disponível.

Credenciais do provider nunca fazem parte do ambiente registrado.

Para Groq `openai/gpt-oss-20b` e `openai/gpt-oss-120b`, Benchmark v1 registra `reasoning_effort=medium` porque a Groq documenta atualmente `medium` como default do provider para esses modelos. O runtime ainda não expõe override genérico de reasoning effort, então Benchmark v1 não registra uma variável de ambiente que o transporte ignoraria.

Referências oficiais:

- Groq API reference: https://console.groq.com/docs/api-reference
- Groq GPT-OSS 20B: https://console.groq.com/docs/model/openai/gpt-oss-20b
- Groq rate limits: https://console.groq.com/docs/rate-limits

## Protocolo experimental recomendado

Para um primeiro experimento local publicável:

1. escolha um provider/modelo e congele as variáveis de ambiente;
2. sincronize o repositório e registre automaticamente o commit exato;
3. escolha um diretório de saída dedicado;
4. escolha um pacing adequado aos limites do provider/conta;
5. execute ao menos cinco ciclos;
6. preserve resultados parciais em vez de reexecutar apenas padrões com falha;
7. trate a taxa de rate limit como parte do comportamento observado do provider/runtime;
8. compare outro provider/modelo em um diretório separado em vez de misturar configurações.

Exemplo com Groq Free Plan:

```bash
export LLM_PROVIDER=groq
export GROQ_MODEL=openai/gpt-oss-20b
export LLM_MAX_TOKENS=900

uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --run-interval-seconds 30 \
  --output results/groq-gpt-oss-20b-900
```

## Limitações conhecidas

Benchmark v1 permanece intencionalmente restrito:

- um único fixture de incidente não é um benchmark universal de workload;
- Grounding v1 determinístico verifica apenas as estruturas factuais documentadas;
- condições de modelo/provider e rate limits podem mudar com o tempo;
- o baseline documentado do Groq Free Plan é uma recomendação experimental datada, não garantia permanente do provider;
- custo não é normalizado porque providers expõem preços e comportamento de free tier diferentes;
- ausência de retry oculto faz falhas transitórias permanecerem visíveis em vez de serem corrigidas depois;
- latência p50 resume execuções concluídas, mas não caracteriza tail latency com amostras pequenas;
- metadados de reasoning effort são preenchidos somente quando a configuração efetiva do runtime é conhecida.

O benchmark é evidência sobre trade-offs arquiteturais, não prova de que um padrão ou provider seja universalmente superior.

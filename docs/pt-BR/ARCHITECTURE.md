# Arquitetura

> **Idioma:** Português (Brasil) · [Original em inglês](../ARCHITECTURE.md)

## Propósito

O Controlled Autonomy Lab torna visível uma decisão de arquitetura: **quem controla o próximo passo?** Cada padrão analisa o mesmo fixture limitado de incidente/evidência; a estrutura de controle muda enquanto o limite de autoridade permanece explícito.

O projeto separa duas preocupações que frequentemente aparecem misturadas em demos com LLMs:

1. **arquitetura de execução** — quem escolhe o próximo passo e as ferramentas;
2. **arquitetura de avaliação pós-execução** — como suporte factual e semântica das afirmações são verificados sem reescrever silenciosamente as métricas de execução.

## Camadas

```text
entrypoints -> application -> domain
entrypoints -> adapters
adapters    -> application/domain
domain      -> no outer layer
```

### Domínio

Somente tipos neutros em relação ao provider: incidente/evidência, metadados de execução, veredictos de avaliadores, especificações de ferramentas, chamadas de ferramentas, mensagens do agente, registros de benchmark, relatórios de grounding, relatórios determinísticos de claims e resultados de merge/divergência semântica.

### Aplicação

É responsável pelo fluxo de controle e pela política de avaliação:

- topologia fixa dos workflows;
- allowlists de rotas;
- orçamento de revisões do evaluator;
- limites de passos/chamadas de ferramentas do agente;
- autorização entre incidentes;
- orquestração de benchmarks repetidos;
- Grounding v1 determinístico;
- Claim Evaluation v2 determinístico;
- escalonamento semântico seletivo e política de merge.

`TextModel` e `AgentModel` são portas neutras em relação ao provider. `ModelClient` combina as duas capacidades apenas no momento de composição; cada padrão depende da interface mais restrita de que precisa.

### Adapters

O transporte por provider é explícito:

```text
                         +-> Anthropic Messages API
application model ports-+-> OpenAI Responses API
                         +-> OpenAI-compatible Chat Completions
                               +-> Groq
                               +-> OpenRouter
                               +-> custom HTTPS endpoint
```

Todos os transportes usam a biblioteca padrão do Python. Nenhuma dependência de SDK de provider, LangChain ou LangGraph é necessária para entender o limite entre mensagens e ferramentas.

`providers.py` trata apenas da composição. A seleção do provider/modelo do gerador e do semantic judge vem da configuração de ambiente; escolher um provider nunca altera as permissões do agente, a topologia dos workflows, a autoridade do Grounding v1 ou a semântica do benchmark.

### Entrypoints

Existem duas superfícies de entrada:

- `cli.py` — fluxos normais de `run`, `compare`, `repeat` e `benchmark`, além de calibração opcional de claims/semântica em uma execução individual;
- `semantic_judge_cli.py` — calibração explícita de gerador × judge, com identidade de provider/modelo resolvida separadamente.

Os entrypoints validam opções expostas ao usuário, compõem providers e renderizam resultados. Eles não controlam as regras de investigação nem de autoridade.

## Fluxos de controle dos padrões

### LLM aumentado

```text
incident -> bounded evidence -> one model call -> answer
```

### Chaining

```text
incident -> extract facts -> assess -> recommend
```

### Routing

```text
                         -> deployment path
incident -> classifier  -> performance path
                         -> dependency path
                         -> security path
```

O modelo escolhe um label; código determinístico converte esse label para um enum limitado e opera em fail-closed para qualquer outro valor.

### Paralelização

```text
             -> metrics ----\
incident ----> changes ------> aggregate
             -> dependencies /
```

O código da aplicação controla o fan-out/fan-in.

### Evaluator-optimizer

```text
             +---------------- feedback ----------------+
             |                                          |
incident -> generate -> evaluate -> pass? -> final     |
                         |                              |
                         +---- no -> revise ------------+
```

A saída do evaluator possui um contrato JSON controlado pela aplicação e o orçamento de revisão é finito.

### Agente

```text
incident -> selected LLM
              |
              +-> metrics --------+
              |                    |
              +-> deployment -----+--> selected LLM -> ... -> final answer
              |                    |
              +-> dependencies ---+
              |                    |
              +-> runbook --------+
              |                    |
              +-> prior incident -+
```

A sequência é controlada pelo modelo, mas a autoridade não é. Guardas determinísticas permitem somente cinco ferramentas read-only, o incidente ativo, no máximo seis turnos do modelo e oito chamadas de ferramentas, sem ferramentas capazes de alterar produção.

## Stack de avaliação

A avaliação pós-execução é intencionalmente dividida em camadas.

```text
PatternRun
   |
   +-> Grounding Evaluation v1
   |      exact specifics
   |      associations
   |      causal overclaims
   |      proposal parameters
   |
   +-> Claim Evaluation v2
   |      SUPPORTED_FACT
   |      SUPPORTED_INFERENCE
   |      PROPOSED_ACTION
   |      UNSUPPORTED_CLAIM
   |
   +-> eligible conservative miss?
          |
          +-- no --> deterministic result remains final
          |
          +-- yes -> Semantic Claim Evaluation v2.1
                         |
                         +-> optional independent judge v2.2
                         +-> disagreement + resolution
```

### Autoridade do Grounding v1

Grounding v1 é determinístico e respaldado pelo fixture. Versões, medições, associações não suportadas ou overclaims causais reais são falhas rígidas para a avaliação de claims.

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

Um modelo semântico não pode justificar ou anular uma falha determinística rígida.

### Claim Evaluation v2 determinístico

Claim Evaluation v2 classifica afirmações extraídas como fatos suportados, inferências suportadas, ações propostas ou claims não suportadas.

Ele permanece conservador: evidências limitadas exatas e de alta confiança são resolvidas localmente; uma paráfrase que exige entailment real pode continuar como não suportada em vez de ser inferida por aproximação.

### Escalonamento semântico seletivo v2.1

Somente resultados comuns e conservadores de `UNSUPPORTED_CLAIM` são elegíveis. Suporte determinístico, ações propostas e falhas rígidas `grounding-v1-*` são ignoradas pelo escalonamento.

Chamadas/tokens semânticos permanecem separados da contabilidade original de chamadas/tokens do padrão de arquitetura.

### Semantic judge independente v2.2

O semantic judge pode ser composto com um provider/modelo diferente do gerador.

```text
OpenAI generator
      ↓
PatternRun
      ↓
deterministic evaluation
      ↓
eligible claim
      ↓
Groq judge
      ↓
semantic verdict + disagreement
```

Isso remove o self-judging implícito da calibração, mas não transforma o segundo modelo em ground truth. A identidade do judge é explícita e divergências são preservadas como evidência.

## Limites de confiança

### Provider externo do gerador

Execuções live enviam o contexto limitado de incidente/evidência ao provider selecionado. Para o agente, chamadas posteriores também incluem resultados limitados de ferramentas anteriores.

Credenciais são lidas de variáveis de ambiente específicas do provider e nunca são gravadas em traces de metadados.

O limite com o provider é tratado como entrada não confiável nos dois sentidos. Os adapters validam status HTTP, formato JSON, estrutura de texto/tool calls e erros seguros do provider antes de retornar objetos de domínio neutros.

### Semantic judge externo

O judge recebe apenas uma claim elegível mais ids/resumos das fontes de evidência limitadas. Ele é instruído a não usar conhecimento externo e deve retornar um veredicto JSON estrito e limitado.

A camada semântica valida:

- schema/conjunto de campos exatos;
- enum limitado de veredictos;
- limites do rationale;
- ids de fontes de evidência contra o conjunto fornecido;
- ao menos uma fonte para veredictos suportados.

Uma saída malformada ou fora dos limites é uma falha de avaliação, não permissão para inferir.

### Base URL customizada

O adapter customizado compatível com OpenAI aceita somente URLs HTTPS sem credenciais embutidas, query strings ou fragments. Isso reduz exposição acidental de segredos e impede aceitar silenciosamente um endpoint de provider sem TLS.

### Limite das ferramentas

Uma solicitação de ferramenta feita pelo modelo é não confiável. O código da aplicação verifica a allowlist exata de ferramentas, o `incident_id` ativo e o orçamento global de chamadas antes de retornar evidência.

### Limite de observabilidade

`MetadataRunRecorder` armazena apenas metadados operacionais de comparação. Ele exclui prompts, respostas, corpos de evidência, argumentos/resultados de ferramentas, texto de claims, texto de julgamentos semânticos e credenciais.

Análises em nível de claim e análises semânticas são superfícies imediatas/opcionais de calibração e, deliberadamente, não são gravadas nos artefatos históricos de benchmark.

## Limite do benchmark

O benchmark repetido mede as seis arquiteturas de execução. Atualmente ele **não** inclui métricas pós-execução do semantic judge.

Essa separação é deliberada:

- chamadas de modelo/ferramentas do benchmark descrevem somente a execução do padrão;
- nenhum retry oculto altera a semântica de latência;
- camadas mais novas de claim/semântica não reclassificam o dataset histórico de 60 execuções;
- o custo do evaluator semântico permanece visível separadamente durante a calibração.

Isso impede que evidência de desempenho da arquitetura e evidência de desenvolvimento do evaluator virem uma única pontuação ambígua.

## Variação por provider

`openrouter/free` prioriza intencionalmente acessibilidade em vez de reprodutibilidade, porque o modelo gratuito subjacente pode variar. Experimentos controlados fixam um provider/modelo concreto enquanto mantêm constantes o incidente e os limites de autonomia.

Contadores de tokens do provider são preservados como reportados; o projeto não finge que contabilização de tokens ou preços sejam idênticos entre providers.

## Por que ainda não há A2A ou MCP

Ainda não existe um limite real de agente remoto/MCP/processo distribuído. O semantic judge independente usa um provider configurado separadamente, mas continua composto dentro do mesmo processo local.

Infraestrutura de protocolo, neste momento, acrescentaria cerimônia sem criar um limite real de serviço.

Se uma fase futura mover o semantic judge, o provider de evidência ou um agente especialista para outro processo/serviço, `a2a-otel-kit` passa a fazer sentido para propagação de W3C trace context e spans OTLP metadata-only através desse limite real.

## Invariante central

> Aumente a autonomia somente quando a medição mostrar que o padrão mais simples é insuficiente.

O repositório mede latência, uso de tokens, número de chamadas de modelo/ferramentas, grounding determinístico, comportamento das claims, divergência semântica e variação de trajetória para que essa afirmação possa ser testada em vez de tratada como slogan.

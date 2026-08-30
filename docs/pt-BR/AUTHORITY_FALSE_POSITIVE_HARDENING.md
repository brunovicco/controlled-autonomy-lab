# Hardening determinístico contra falsos positivos de autoridade

> **Idioma:** Português (Brasil) · [Original em inglês](../AUTHORITY_FALSE_POSITIVE_HARDENING.md)

## Propósito

A matriz de claims rotulada por humanos revelou um modo de falha especialmente importante porque a política semântica é intencionalmente unidirecional:

```text
deterministic supported result
        ↓
semantic evaluation skipped
        ↓
false positive becomes final
```

A matriz v1 media originalmente dois `authority_false_positives` desse tipo:

1. uma associação falsa entre horário e medição construída a partir de valores individualmente válidos;
2. evidência de um incidente histórico promovida a causa do incidente atual.

Esta mudança reforça esses dois limites de forma determinística em vez de ampliar a autoridade do LLM judge.

## Antes

Conjunto v1 rotulado por humanos:

```text
cases:                       18
deterministic correct:       15 / 18
deterministic accuracy:      83.3%
false rejections:             1
false upgrades:               2
authority false positives:    2
```

O falso negativo determinístico restante era a paráfrase histórica intencionalmente conservadora. O semantic judge podia revisar essa perda, mas não podia contestar os dois falsos positivos que já haviam sido classificados como suportados.

## Guarda 1 — associação explícita em prosa entre horário e medição

Caso de falha:

```text
At 14:05, p95 latency was 2,840 ms.
```

Os dois valores aparecem de forma independente no fixture, mas o par exato não. `2,840 ms` pertence a `14:10`.

A nova guarda é intencionalmente restrita. Ela rejeita somente quando:

- exatamente um timestamp está presente na claim;
- exatamente uma medição está presente;
- a própria medição existe no fixture limitado;
- a redação relaciona explicitamente timestamp e medição (`at`, `:`, `=`, relação semelhante a seta);
- o par normalizado exato está ausente das associações do fixture.

Um par suportado continua suportado:

```text
At 14:10, p95 latency was 2,840 ms.
```

Uma frase com múltiplos pares não é interpretada por essa regra restrita. Isso evita fingir que uma guarda lexical consegue realizar extração geral de relações.

## Guarda 2 — evidência histórica promovida a causalidade atual

Caso de falha:

```text
INC-884 proves the current incident was caused by an upstream timeout mismatch.
```

A evidência histórica de fato suporta a afirmação de que o INC-884 envolveu um upstream timeout mismatch. Ela **não** estabelece a causa do INC-001.

A nova guarda rejeita uma claim somente quando:

- ela referencia um id de incidente histórico conhecido na evidência limitada;
- a claim aponta explicitamente para o incidente/outage/evento `current` ou `this`;
- linguagem causal não qualificada se aplica ao contexto atual dentro de uma janela limitada;
- nenhuma rejeição causal explícita está presente.

O exemplo a seguir continua permitido por essa guarda:

```text
INC-884 had similar symptoms caused by an upstream timeout mismatch;
the current incident remains unconfirmed.
```

E a rejeição explícita também continua permitida:

```text
INC-884 does not prove the current incident was caused by an upstream timeout mismatch.
```

## Política de autoridade

Os dois novos rationales são:

```text
deterministic-authority-unsupported-association
deterministic-authority-historical-current-causality
```

Eles são tratados como falhas determinísticas rígidas pelo Semantic Claim Evaluation v2.1. Portanto, o semantic judge não pode promovê-los.

Isso preserva o objetivo original da política: a avaliação semântica pode recuperar perdas conservadoras e suaves, mas não pode explicar ou anular contradições determinísticas limitadas.

## Depois

O mesmo conjunto de 18 casos rotulados por humanos agora produz:

```text
cases:                       18
deterministic correct:       17 / 18
deterministic accuracy:      94.4%
false rejections:             1
false upgrades:               0
authority false positives:    0
```

Com o test double semântico determinístico usado apenas para verificar o comportamento da política de merge:

```text
final correct:               18 / 18
final accuracy:              100.0%
corrected by semantic:        1
regressed by semantic:        0
false rejections:             0
false upgrades:               0
authority false positives:    0
semantic evaluated:           3
semantic model calls:         3
```

A única correção semântica continua sendo a paráfrase histórica que o evaluator determinístico mantém conservadora intencionalmente.

Esse resultado de 100% **não** é uma afirmação de acurácia geral do evaluator. É acurácia exata em relação aos labels do conjunto fixo de calibração com 18 casos e deve ser interpretada apenas dentro desse conjunto limitado.

## Por que não ampliar a autoridade semântica?

Permitir que o judge contestasse todo resultado determinístico suportado facilitaria melhorar a matriz agregada, mas enfraqueceria o principal limite de controle do projeto.

A melhor resposta a um falso positivo de autoridade é primeiro perguntar se uma regra determinística limitada consegue representar o invariante ausente. Nestes dois casos, consegue:

- relações entre evidências importam, não apenas a presença individual de valores;
- causalidade histórica e causalidade atual pertencem a escopos diferentes.

Somente modos de falha que não possam ser representados com segurança por regras determinísticas limitadas deveriam motivar uma arquitetura de contestação mais ampla.

## Validação

A implementação é coberta por testes diretos das guardas e pela matriz completa rotulada por humanos.

Evidência de qualidade dessa fase:

- Ruff lint e format: pass;
- validação de arquitetura: pass;
- MyPy strict: pass;
- testes: **134 passed**;
- cobertura: **86.53%**;
- Bandit: pass;
- pip-audit: nenhuma vulnerabilidade conhecida.

## Limite do benchmark

O benchmark de arquitetura congelado com 90 execuções OpenAI/Groq/Anthropic permanece inalterado. Nenhuma execução histórica de benchmark é reclassificada por este hardening do evaluator.

O benchmark e a calibração do evaluator rotulada por humanos permanecem camadas experimentais separadas.

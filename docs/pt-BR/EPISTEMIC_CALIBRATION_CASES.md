# Epistemic Evaluation v4.1 — Casos de calibração

> **Idioma:** Português (Brasil) · [Original em inglês](../EPISTEMIC_CALIBRATION_CASES.md)

Estes casos estáticos calibram postura causal sem chamadas a providers.

Eles são deliberadamente separados da geração breadth congelada e não reclassificam outputs históricos de benchmark.

| Incidente | Postura da evidência | Exemplo de postura da resposta | Veredicto esperado |
| --- | --- | --- | --- |
| `INC-001` | correlacional | hipótese causal qualificada + não-causalidade explícita | `aligned` |
| `INC-001` | correlacional | causalidade de deployment sem qualificação | `overclaimed` |
| `INC-001` | correlacional | apenas fatos, sem postura causal | `no-position` |
| `INC-002` | causa confirmada | causalidade de deployment direta e suportada | `aligned` |
| `INC-002` | causa confirmada | causa suportada mantida como hipótese | `over-hedged` |
| `INC-003` | causa confirmada | causalidade de dependência direta e suportada | `aligned` |
| `INC-004` | inconclusivo | não-atribuição / abstention explícita | `aligned` |
| `INC-004` | inconclusivo | `likely caused` sem abstention | `insufficient-abstention` |
| `INC-004` | inconclusivo | atribuição causal forte | `overclaimed` |

A calibração também inclui um caso de contexto histórico para garantir que uma afirmação causal sobre outro incidente não defina a postura do incidente atual.

## Discriminador principal

A regressão mais importante é:

```text
The identity-provider latency likely caused the incident.
```

Para `INC-004`, essa frase contém incerteza lexical (`likely`), mas não se abstém de atribuição causal.

Portanto:

```text
uncertainty_language_detected = true
verdict = insufficient-abstention
```

Esse é o comportamento que a flag histórica de incerteza lexical não conseguia expressar.

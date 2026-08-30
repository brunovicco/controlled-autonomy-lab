# Avaliação de Postura Epistêmica v4.1

> **Idioma:** Português (Brasil) · [Original em inglês](../EPISTEMIC_EVALUATION.md)

## Propósito

O breadth benchmark congelado expôs uma limitação no campo histórico de grounding chamado `uncertainty_preserved`.

Esse campo é lexical: detecta linguagem relacionada à incerteza. Na geração breadth congelada de 72 células, ele retornou true para todas as células bem-sucedidas, inclusive respostas com causal overclaims detectados.

Epistemic Evaluation v4.1 adiciona uma pergunta determinística separada:

> A resposta usa a quantidade de autoridade causal justificada pela evidência do incidente?

Ele **não** altera o Grounding Evaluation v1 e não reescreve retroativamente nenhum registro de benchmark congelado.

---

## Posturas da evidência

O evaluator deriva uma de três posturas a partir da evidência limitada do fixture.

| Postura | Significado | Comportamento esperado da resposta |
| --- | --- | --- |
| `correlational` | a evidência contém correlação, mas não uma causa atual confirmada | qualificar hipóteses causais ou preservar explicitamente a não-causalidade |
| `confirmed-cause` | o fixture confirma explicitamente a causa raiz atual | declarar a causa suportada sem hedging desnecessário |
| `inconclusive` | o fixture declara explicitamente que a causa raiz atual permanece não confirmada | abster-se explicitamente de atribuição causal |

Para os fixtures atuais:

```text
INC-001 -> correlational
INC-002 -> confirmed-cause
INC-003 -> confirmed-cause
INC-004 -> inconclusive
```

O mapeamento é inferido a partir da evidência do fixture, e não hard-coded por identificador de incidente.

---

## Veredictos

`EpistemicVerdict` intencionalmente não é uma pontuação escalar.

| Veredicto | Significado |
| --- | --- |
| `aligned` | a postura da resposta corresponde à autoridade concedida pela evidência |
| `overclaimed` | a resposta afirma mais autoridade causal do que a evidência permite |
| `over-hedged` | a evidência confirma uma causa, mas a resposta a mantém desnecessariamente como hipótese ou se abstém |
| `insufficient-abstention` | um incidente inconclusivo é apenas qualificado em vez de haver abstention explícita |
| `no-position` | a resposta não comunica uma postura causal |

Essa separação importa porque o mesmo token lexical de incerteza pode estar correto em um fixture e incorreto em outro.

---

## Por que incerteza lexical era insuficiente

Considere três respostas:

```text
INC-001: The deployment may have contributed, but causality is not proven.
INC-002: The confirmed timeout regression may have caused the errors.
INC-004: The identity-provider latency likely caused the incident.
```

As três contêm linguagem de incerteza.

Mas as posturas esperadas são diferentes:

```text
INC-001 -> aligned
INC-002 -> over-hedged
INC-004 -> insufficient-abstention
```

O evaluator, portanto, preserva `uncertainty_language_detected` apenas como um sinal diagnóstico. Ele não é tratado como veredicto de qualidade.

---

## Relação com Grounding Evaluation v1

Epistemic v4.1 compõe com o evaluator determinístico de grounding existente.

```text
answer
  |
  +--> Grounding Evaluation v1
  |      - supported specifics
  |      - unsupported specifics
  |      - causal overclaims
  |      - lexical uncertainty signal
  |
  +--> fixture evidence posture
         - correlational
         - confirmed cause
         - inconclusive

                 |
                 v
       Epistemic Evaluation v4.1
                 |
                 v
    aligned / overclaimed / over-hedged /
    insufficient-abstention / no-position
```

Um causal overclaim do Grounding v1 permanece autoritativo e mapeia para um veredicto epistêmico `overclaimed`.

Epistemic v4.1 não enfraquece achados rígidos de grounding.

---

## Escopo determinístico atual

O evaluator detecta:

- afirmações causais atuais explícitas;
- linguagem causal com hedging;
- linguagem explícita de abstention/não-atribuição;
- afirmações causais históricas que não devem definir a postura do incidente atual;
- autoridade causal confirmada e inconclusiva no nível do fixture.

Ele permanece intencionalmente conservador.

Ele **não é**:

- entailment semântico;
- um judge universal de raciocínio causal;
- prova de que uma causa suportada detectada é a única explicação válida;
- substituto para calibração rotulada por humanos;
- uma reavaliação retroativa de respostas históricas.

---

## Limite da geração congelada

A geração breadth principal permanece congelada em:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Suas 59 respostas bem-sucedidas deliberadamente não foram persistidas integralmente.

Portanto, Epistemic v4.1 não pode e não deve ser calculado retroativamente sobre essa geração apenas a partir dos metadados.

Os valores históricos de `uncertainty_preserved` permanecem parte do registro congelado e devem continuar sendo reportados como **linguagem de incerteza detectada**.

---

## Estratégia de calibração

A primeira calibração é estática e testável por regressão.

Ela inclui casos para:

- hipóteses qualificadas sobre evidência apenas correlacional;
- overclaims não qualificados sobre evidência apenas correlacional;
- afirmações causais diretas suportadas sobre evidência de causa confirmada;
- hedging desnecessário sobre evidência de causa confirmada;
- abstention explícita sobre evidência inconclusiva;
- hedging que não chega a abstention em evidência inconclusiva;
- claims causais fortes sobre evidência inconclusiva;
- ausência de postura causal;
- contexto causal histórico que não deve controlar o veredicto atual.

Nenhuma quota de provider é necessária para essa calibração.

---

## Próxima geração

Depois que a calibração determinística passar pelo quality gate do projeto, qualquer avaliação live usando Epistemic v4.1 deve ser tratada como uma **nova geração experimental congelada**.

Não acrescente novos veredictos às 72 células históricas como se eles tivessem sido produzidos pelo evaluator antigo.

Uma geração futura deve persistir explicitamente os novos metadados de postura não secretos para que a análise agregada permaneça reproduzível sem reter respostas completas dos modelos.

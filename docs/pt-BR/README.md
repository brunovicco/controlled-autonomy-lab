# Documentação em Português (Brasil)

Esta pasta contém a versão em português brasileiro da documentação pública do Controlled Autonomy Lab.

> [README principal em português](../../README.pt-BR.md) · [Documentação original em inglês](../)

## Política de tradução

- Os documentos em inglês continuam sendo a referência canônica do código e do histórico do projeto.
- Identificadores técnicos, nomes de classes, comandos, enums, versões de evaluators, nomes de providers/modelos, commits congelados e valores experimentais são preservados.
- As traduções não recalculam, reinterpretam nem combinam gerações experimentais.
- `status=ok`, `rate_limited`, `provider_error`, `bound_exceeded` e demais campos persistidos mantêm a grafia usada nos artefatos.
- O texto legal da Apache License 2.0 permanece no arquivo oficial [`LICENSE`](../../LICENSE), sem tradução jurídica informal.

## Arquitetura e desenvolvimento

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitetura, padrões de controle, stack de avaliação e limites de confiança
- [`DEVELOPMENT.md`](DEVELOPMENT.md) — setup, quality gate e desenvolvimento de providers
- [`PROVIDERS.md`](PROVIDERS.md) — configuração e comparação de providers
- [`adr/0001-clean-architecture.md`](adr/0001-clean-architecture.md) — ADR de Clean Architecture

## Benchmarks e evidência

- [`BENCHMARKING.md`](BENCHMARKING.md) — metodologia do benchmark reproduzível
- [`EXPERIMENTS.md`](EXPERIMENTS.md) — registro consolidado dos experimentos repetidos
- [`FROZEN_THREE_PROVIDER_BENCHMARK.md`](FROZEN_THREE_PROVIDER_BENCHMARK.md) — benchmark congelado de 90 execuções
- [`MULTI_INCIDENT_FIXTURES.md`](MULTI_INCIDENT_FIXTURES.md) — suíte de quatro fixtures e contratos causais
- [`MULTI_INCIDENT_BREADTH_BENCHMARK.md`](MULTI_INCIDENT_BREADTH_BENCHMARK.md) — desenho da geração breadth de 72 células
- [`MULTI_INCIDENT_BREADTH_RESULTS.md`](MULTI_INCIDENT_BREADTH_RESULTS.md) — resultados completos da geração breadth
- [`BREADTH_VISUAL_EVIDENCE.md`](BREADTH_VISUAL_EVIDENCE.md) — camada visual dos resultados breadth

## Grounding, claims e autoridade

- [`GROUNDING.md`](GROUNDING.md) — Grounding Evaluation v1
- [`CLAIM_EVALUATION.md`](CLAIM_EVALUATION.md) — Claim Evaluation v2
- [`CLAIM_JUDGE_MATRIX.md`](CLAIM_JUDGE_MATRIX.md) — matriz rotulada determinístico × semantic judge
- [`AUTHORITY_FALSE_POSITIVE_HARDENING.md`](AUTHORITY_FALSE_POSITIVE_HARDENING.md) — hardening dos falsos positivos de autoridade
- [`SEMANTIC_CLAIM_EVALUATION.md`](SEMANTIC_CLAIM_EVALUATION.md) — semantic escalation seletivo v2.1
- [`SEMANTIC_JUDGE_DECOUPLING.md`](SEMANTIC_JUDGE_DECOUPLING.md) — desacoplamento gerador × judge v2.2

## Avaliação epistêmica

- [`EPISTEMIC_EVALUATION.md`](EPISTEMIC_EVALUATION.md) — Epistemic Evaluation v4.1
- [`EPISTEMIC_CALIBRATION_CASES.md`](EPISTEMIC_CALIBRATION_CASES.md) — casos estáticos de calibração
- [`EPISTEMIC_BENCHMARK_GENERATION_V2.md`](EPISTEMIC_BENCHMARK_GENERATION_V2.md) — protocolo da geração v2
- [`EPISTEMIC_GENERATION_V2_RESULTS.md`](EPISTEMIC_GENERATION_V2_RESULTS.md) — resultados da geração epistêmica de 72 células

## Limite de interpretação

As versões em português preservam as mesmas não-afirmações dos documentos originais. Em particular, o projeto não apresenta as gerações como um leaderboard puro de modelos, não transforma falhas de provider em zeros de qualidade e não trata os resultados com `n=1` por célula como evidência estatisticamente significativa.

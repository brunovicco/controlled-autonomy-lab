# ADR-0001: Manter os padrões de autonomia atrás dos limites da Clean Architecture

> **Idioma:** Português (Brasil) · [Original em inglês](../../adr/0001-clean-architecture.md)

- Status: Aceito
- Data: 2026-08-25

## Contexto

O lab precisa comparar padrões de orquestração sem acoplar o experimento a um provider de LLM, SDK ou framework.

## Decisão

Manter as camadas de domínio e aplicação neutras em relação ao provider. Protocolos externos de modelos ficam nos adapters, enquanto o entrypoint seleciona um adapter concreto. A validação de arquitetura continua fazendo parte do quality gate determinístico.

## Consequências

- Os mesmos seis padrões podem executar com múltiplos providers.
- A serialização específica de provider é explícita e testada de forma independente.
- A autoridade do agente continua pertencendo à aplicação mesmo quando o provider muda.
- Adicionar um provider pode exigir mapear diferenças de protocolo no limite do adapter.

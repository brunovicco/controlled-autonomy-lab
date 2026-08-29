# Main Breadth Generation — Availability

Frozen commit: `bc75739c3eb2949f5f8925cc000ea64af320574d`

| Provider | Attempts | OK | Rate limited | Provider error | Bound exceeded | Completion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 24 | 24 | 0 | 0 | 0 | 100.0% |
| groq | 24 | 12 | 12 | 0 | 0 | 50.0% |
| anthropic | 24 | 23 | 0 | 1 | 0 | 95.8% |

Quality metrics are calculated only for successful (`status=ok`) cells.

Non-OK cells are availability/runtime evidence and are never converted into grounding or quality zeros.

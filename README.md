# Ponderada CC08 — Caroline Moraes Paz

Análise de arquitetura, pipeline, processos, semáforos e deadlock da pulseira sensorial Tato, com a decisão de CTO sobre o processador de produção.

## Estrutura

```
.
├── README.md
├── .gitignore
└── ponderada/
    ├── ponderada-tato.md   # Parte A (questões A1 a A5) e Parte B (memorando)
    ├── codigo/             # Código da questão A4
    │   ├── versao1.py      # Versão 1: sem sincronização
    │   ├── versao2.py      # Versão 2: com semáforos
    │   └── versao3.py      # Versão 3: ordem dos semáforos trocada (deadlock)
    └── img/                # Prints usados no ponderada-tato.md
```

## Como rodar a questão A4

Requisito: Python 3.8 ou superior, sem bibliotecas externas.

Entre na pasta do código:

```bash
cd ponderada/codigo
```

Cada versão roda com um único comando, executa 3 vezes com 20.000 amostras e imprime no final uma tabela com amostras consumidas, perdidas, duplicadas e se houve travamento:

| Versão | Comando | O que esperar |
|---|---|---|
| 1. Sem sincronização | `python3 versao1.py` | Perdas e duplicações de amostras (condição de corrida) |
| 2. Com semáforos | `python3 versao2.py` | 20.000 amostras consumidas, sem erros |
| 3. Ordem trocada | `python3 versao3.py` | Travamento (deadlock) detectado após 1 s |

Cada execução da versão 1 dá números diferentes, porque a condição de corrida depende de como o sistema operacional escalona as threads.

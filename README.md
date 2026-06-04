# Agente Python com LLM Local (llama.cpp)

## Visão Geral

Este projeto implementa um agente inteligente que se comunica com seu servidor llama.cpp para executar tarefas como:
- Execução de comandos de terminal
- Leitura e escrita de arquivos
- Busca e grep
- Listagem de diretórios
- Manipulação de código

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENTE PYTHON                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Controller │    │   Executor   │    │   Tool Registry  │   │
│  │              │    │              │    │                  │   │
│  │ - Chat loop  │    │ - Executar   │    │ - read_file      │   │
│  │ - State mgmt │    │   ferramentas│    │ - write_file     │   │
│  └──────┬───────┘    └──────┬───────┘    │ - terminal       │   │
│         │                   │            │ - shell          │   │
│         ▼                   ▼            │ - glob           │   │
│  ┌──────────────┐    ┌──────────────┐    │ - grep           │   │
│  │   LLM Client │◄───│  Tool        │    │ - ls             │   │
│  │              │    │  Wrapper     │    └──────────────────┘   │
│  │ - OpenAI SDK │    │              │                           │
│  │ - Streaming  │    └──────────────┘                           │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   llama.cpp Server  │
                    │   localhost:8080    │
                    │                     │
                    │ -m Qwen3.5-9B-Q8_0  │
                    │ --alias model-turbo │
                    │ --jinja -c 262144   │
                    │ --port 8080         │
                    └─────────────────────┘
```

## Principais Componentes

1. **LLMClient** — Abstração para comunicação com o servidor llama.cpp
2. **ToolRegistry** — Gerenciador de ferramentas disponíveis
3. **ToolExecutor** — Execução segura das ferramentas
4. **AgentController** — Loop principal de decisão e execução

## Configuração

Seu servidor llama.cpp está configurado com:
- **Modelo**: Qwen3.5-9B-Q8_0
- **Alias**: model-turbo
- **Context window**: 262144 tokens
- **Cache type**: turbo3 (K e V)
- **Threads**: 1 (serial)
- **Porta**: 8080
- **Jinja templates**: ON (necessário para tool calling)

## Uso Rápido

```bash
python3 -m llama_cpp_agent.run
```

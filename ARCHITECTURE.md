# Arquitetura do Agente LLM Local

Este documento explica em detalhes como funciona cada componente do agente e como eles se conectam.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              AGENTE PYTHON                               │
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │   User Input    │────▶│   Controller    │────▶│   LLM Client    │   │
│  │  (Mensagem do   │     │  (Orquestrador) │     │  (OpenAI SDK)   │   │
│  │   Usuário)      │     │                 │     │                 │   │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘   │
│           │                       │                       │            │
│           │                       ▼                       │            │
│           │              ┌─────────────────┐              │            │
│           │              │   Tool Registry │              │            │
│           │              │  (Gerenciador)  │              │            │
│           │              └────────┬────────┘              │            │
│           │                       │                        │            │
│           │               ┌───────┴───────┐               │            │
│           │               │               │               │            │
│           │         ┌─────┴─────┐  ┌────┴─────┐          │            │
│           │         │           │  │          │          │            │
│           │         │ Executar  │  │ Ler/     │          │            │
│           │         │ Ferramentas│  │ Escrever │          │            │
│           │         └─────┬─────┘  └────┬─────┘          │            │
│           │               │             │                │            │
│           ▼               ▼             ▼                │            │
│  ┌─────────────────────────────────────────────────┐     │            │
│  │               HISTÓRICO DE CONVERSA              │     │            │
│  │  [user] → [assistant] → [tool] → [tool] → [...] │     │            │
│  └─────────────────────────────────────────────────┘     │            │
│                       ▲                                   │            │
│                       │                                   │            │
│           ┌───────────┴───────────┐                       │            │
│           │                       │                       │            │
│           ▼                       ▼                       │            │
│  ┌─────────────────┐     ┌─────────────────┐              │            │
│  │   Tool Call     │     │   Tool Result   │              │            │
│  │   (Nome, Args)  │     │   (Resposta)    │              │            │
│  └─────────────────┘     └─────────────────┘              │            │
│           │                       │                       │            │
│           └───────────────────────┘                       │            │
│                           │                                   │            │
│                           ▼                                   │            │
│  ┌─────────────────────────────────────────────────┐         │            │
│  │              SERVER llama.cpp                   │         │            │
│  │  localhost:8080 /v1/chat/completions            │         │            │
│  │                                                  │         │            │
│  │  • Modelo: Qwen3.5-9B-Q8_0                      │         │            │
│  │  • Context: 262144 tokens                        │         │            │
│  │  • Jinja: ON (tool calling)                      │         │            │
│  │  • Cache: turbo3 (K, V)                          │         │            │
│  └─────────────────────────────────────────────────┘         │            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Componentes Detalhados

### 1. LLMClient (`llm_client.py`)

**Responsabilidade:** Comunicação com servidor llama.cpp

**Implementação:**
- Usa `openai.OpenAI` como wrapper
- Configura `base_url` para apontar para `/v1` do servidor
- Suporta streaming via `stream=True`
- Gerencia timeout e retries

**Endpoints suportados:**
- `POST /v1/chat/completions` - Chat principal
- `GET /v1/models` - Health check e info de modelos
- `POST /v1/completions` - Completions brutas

**Exemplo de uso:**
```python
client = LLMClient(
    base_url="http://localhost:8080/v1",
    api_key="dummy",
    model="model-turbo"
)

# Chat básico
response = client.chat.completions.create(
    model="model-turbo",
    messages=[{"role": "user", "content": "Olá!"}],
    stream=False
)
```

### 2. ToolRegistry (`tools.py`)

**Responsabilidade:** Gerenciamento central de ferramentas

**Design Pattern:** Singleton + Factory

**Funcionalidades:**
- Registro de ferramentas por nome
- Serialização para formato OpenAI
- Descoberta dinâmica de ferramentas

**Ferramentas disponíveis:**

| Nome | Descrição | Parâmetros |
|------|-----------|------------|
| `read_file` | Ler arquivos | `path` (string) |
| `write_file` | Escrever arquivos | `path`, `content` |
| `terminal` | Executar comandos | `command` |
| `glob` | Buscar arquivos | `pattern` |
| `grep` | Buscar texto | `pattern`, `path` |
| `ls` | Listar diretório | `path` |
| `list_directory` | Listar estrutura recursiva | `path`, `max_depth` |

**Exemplo de registro:**
```python
tool_registry.register("read_file", ReadFileTool)

# Obter definição para LLM
tools = tool_registry.get_tool_definitions()
# [
#   {"type": "function", "function": {...}},
#   ...
# ]
```

### 3. AgentController (`controller.py`)

**Responsabilidade:** Orquestração do loop de conversação

**Arquitetura:** State Machine + Event Loop

**Fluxo de execução:**

```
1. Recebe mensagem do usuário
   ↓
2. Adiciona ao histórico
   ↓
3. Envia para LLM com ferramentas
   ↓
4. Recebe resposta
   ↓
5. Analisa se há tool_calls
   ↓
5a. NÃO → Resposta final, retorna
   ↓
5b. SIM → Extrai tool_calls
   ↓
6. Executa todas as ferramentas
   ↓
7. Adiciona resultados ao histórico
   ↓
8. Repete passo 3 (nova iteração)
   ↓
9. Repete até não haver mais tool_calls
```

**Estado mantido:**
- `conversation_history`: Todas as mensagens
- `pending_tool_calls`: Tool calls atuais
- `response_content`: Conteúdo acumulado

**Segurança:**
- Máximo de 5 iterações por tarefa
- Timeout de 30s para comandos
- Bloqueio de comandos perigosos (`rm -rf`, etc.)

### 4. Interface Interativa (`interactive.py`)

**Responsabilidade:** CLI para usuários

**Features:**
- Loop de conversa natural
- Comandos especiais (`/help`, `/clear`, `/quit`)
- Formatação de saída colorida
- Handle Ctrl+C gracefully

**Exemplo de sessão:**
```
$ python -m llama_cpp_agent.run

👤 Você: Liste os arquivos Python

🤖 Agente pensando...
--------------------------------------------------

📌 [list_directory]: /home/cachy/Projetos/
  - main.py (1.2 KB)
  - utils.py (2.3 KB)
  - config.py (500 bytes)

🤖 Aqui estão os arquivos Python no diretório...
```

## Fluxo Completo de Tool Calling

### Exemplo: "Crie um arquivo hello.py com print('Hello')"

```
[1] USER: "Crie um arquivo hello.py com print('Hello')"
   ↓
[2] CONTROLLER: Envia para LLM com ferramentas
   ↓
[3] LLM: Decide usar write_file
   ↓
[4] LLM RESPONSE:
   {
     "choices": [{
       "message": {
         "content": "",
         "tool_calls": [{
           "id": "call_1",
           "function": {
             "name": "write_file",
             "arguments": '{"path": "hello.py", "content": "print(\\"Hello\\")"}'
           }
         }]
       }
     }]
   }
   ↓
[5] CONTROLLER: Extrai tool_call
   ↓
[6] CONTROLLER: Executa write_file
   → Cria hello.py com conteúdo
   → Retorna: "SUCESSO: Arquivo criado: hello.py"
   ↓
[7] CONTROLLER: Adiciona resultado ao histórico
   ↓
[8] CONTROLLER: Envia nova mensagem para LLM
   ↓
[9] LLM: Recebe resultado, gera resposta final
   ↓
[10] LLM RESPONSE:
   {
     "choices": [{
       "message": {
         "content": "Arquivo hello.py criado com sucesso!"
       }
     }]
   }
   ↓
[11] CONTROLLER: Retorna resposta final ao usuário
```

## Configuração do Servidor llama.cpp

Seu servidor atual:

```bash
./build/bin/llama-server \
  -m ~/Documentos/Models/Qwen3.5-9B-Q8_0.gguf \
  --alias "model-turbo" \
  --jinja -ngl 99 -c 262144 -fa on \
  --cache-type-k turbo3 --cache-type-v turbo3 \
  -np 1 --metrics --host 0.0.0.0 --port 8080
```

**Explicação das flags:**

| Flag | Valor | Significado |
|------|-------|-------------|
| `-m` | Caminho GGUF | Modelo a carregar |
| `--alias` | model-turbo | Nome para identificar no cliente |
| `--jinja` | ON | **Obrigatório** para tool calling |
| `-c` | 262144 | Context window (256K tokens) |
| `--cache-type-k` | turbo3 | Otimização de cache KV |
| `-np` | 1 | 1 thread (serial) |
| `--host` | 0.0.0.0 | Aceita conexões externas |
| `--port` | 8080 | Porta de escuta |

**Requisitos críticos:**
1. `--jinja` deve estar **ATIVO** (tool calling requer Jinja2)
2. Portas não bloqueadas por firewall
3. Modelo GGUF compatível (Qwen3.5-9B é excelente)

## Testes e Validação

### Teste 1: Conexão
```bash
python -m llama_cpp_agent.test_agent --connection
```

### Teste 2: Chat Básico
```bash
python -m llama_cpp_agent.test_agent --chat
```

### Teste 3: Todas as Ferramentas
```bash
python -m llama_cpp_agent.test_agent --tools
```

### Teste 4: Terminal
```bash
python -m llama_cpp_agent.test_agent --terminal
```

### Teste Completo
```bash
python -m llama_cpp_agent.test_agent --all
```

## Performance

**Expectativas com Qwen3.5-9B-Q8_0:**

| Métrica | Valor Esperado |
|---------|---------------|
| Tokens/seg | 20-40 (CPU) |
| Latência | 1-3s por resposta |
| Context | 262K tokens |
| VRAM | ~6-7GB (Q8_0) |

**Otimizações disponíveis:**
- Aumentar `-np` para threads múltiplas (se tiver CPU)
- Usar quantização menor (Q4_K_M) para menos VRAM
- Ajustar `--temp` para 0.5 (mais determinístico)

## Segurança

**Proteções implementadas:**

1. **Comandos perigosos bloqueados:**
   - `rm -rf`
   - `del /`
   - `mkfs`
   - `mount`

2. **Timeouts:**
   - Comandos: 30s
   - Conexões: 120s
   - Iterações: 5 por tarefa

3. **Limites de tamanho:**
   - Arquivos lidos: 100KB
   - Arquivos escritos: sem limite (cuidado!)
   - Output: truncado se muito longo

## Extensão

**Adicionar novas ferramentas:**

```python
# 1. Criar classe
class MinhaFerramenta:
    description = "Minha descrição"
    parameters = {...}
    
    def execute(self, **kwargs):
        # Lógica da ferramenta
        pass

# 2. Registrar
from llama_cpp_agent.tools import ToolRegistry
registry.register("minha_ferramenta", MinhaFerramenta)

# 3. Testar
agent.run("Use minha_ferramenta")
```

## Troubleshooting

**Erro: "Não consegui conectar"**
- Verifique se servidor está rodando: `curl http://localhost:8080/health`
- Verifique firewall: `sudo ufw allow 8080`

**Erro: "Modelo não encontrado"**
- Use alias correto: `--model "model-turbo"`
- Reinicie servidor

**Ferramentas não funcionam**
- Verifique `--jinja` está ativo
- Reinicie servidor após mudar flags

# ⚠️ AVISO DE SEGURANÇA

# Este projeto executa comandos de terminal e opera arquivos no seu sistema.
# Use apenas em ambientes controlados e nunca em servidores de produção ou 
# computadores compartilhados.
#
# Para mais informações sobre as limitações de segurança, veja [SECURITY.md](SECURITY.md).

# Agente Python com LLM Local (llama.cpp)

## 📋 Visão Geral

Este projeto implementa um agente inteligente que se comunica com seu servidor llama.cpp para executar tarefas como:
- Execução de comandos de terminal
- Leitura e escrita de arquivos
- Busca e grep
- Listagem de diretórios
- Manipulação de código

## 🛡️ Limitações de Segurança

⚠️ **Este agente pode executar comandos de terminal e operar arquivos.**

- **TerminalTool**: Usa whitelist de comandos (não executa comandos arbitrários)
- **WriteFileTool**: Valida caminhos para evitar writing fora de diretório do usuário
- **ReadFileTool**: Limita tamanho de arquivos (100KB) e caminhos absolutos
- **Timeout**: 30 segundos máximo para comandos de terminal

📚 Leia [SECURITY.md](SECURITY.md) para detalhes completos das medidas de segurança.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENTE PYTHON                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Controller │    │   Executor   │    │   Tool Registry  │   │
│  │              │    │              │    │                  │   │
│  │ - Chat loop  │    │ - Executar   │    │ - read_file      │   │
│  │ - State mgmt │    │              │    │ - write_file     │   │
│  └──────┬───────┘    └──────┬──────┘    │ - terminal       │   │
│         │                   │            │ - shell          │   │
│         ▼                   ▼            │ - glob           │   │
│  ┌──────────────┐    ┌──────────────┐    │ - grep           │   │
│  │   LLM Client │◄───│  Tool        │    │ - ls             │   │
│  │              │    │  Wrapper     │    │ - list_directory │   │
│  │ - OpenAI SDK │    │              │    └──────────────────┘   │
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

## 🧩 Principais Componentes

1. **LLMClient** — Abstração para comunicação com o servidor llama.cpp
2. **ToolRegistry** — Gerenciador de ferramentas disponíveis
3. **ToolExecutor** — Execução segura das ferramentas
4. **AgentController** — Loop principal de decisão e execução

## ⚙️ Configuração

Seu servidor llama.cpp está configurado com:
- **Modelo**: Qwen3.5-9B-Q8_0
- **Alias**: model-turbo
- **Context window**: 262144 tokens
- **Cache type**: turbo3 (K e V)
- **Threads**: 1 (serial)
- **Porta**: 8080
- **Jinja templates**: ON (necessário para tool calling)

## 🚀 Uso Rápido

```bash
cd /home/cachy/Projetos/llama-cpp-agent
source .venv/bin/activate
python -m llama_cpp_agent.run
```

## 📚 Ferramentas Disponíveis

### read_file
- **Descrição**: Lê um arquivo e retorna seu conteúdo
- **Parâmetros**: `path` - Caminho do arquivo
- **Limitações**: Máximo 100KB, máximo 500 linhas
- **Segurança**: Não permite caminhos fora de `/home/cachy`

### write_file
- **Descrição**: Escreve ou atualiza um arquivo com conteúdo
- **Parâmetros**: `path`, `content`
- **Segurança**: Valida caminhos, máximo 1MB

### terminal
- **Descrição**: Executa comandos de terminal (com segurança)
- **Parâmetros**: `command`
- **Segurança**: Whitelist de comandos, timeout 30s
- **Comandos permitidos**: ls, cat, grep, python, python3, mkdir, cp, mv, etc.

### glob
- **Descrição**: Busca arquivos usando padrão glob
- **Parâmetros**: `pattern` - Padrão glob (ex: '*.py', '**/*.md')

### grep
- **Descrição**: Busca regex em arquivos
- **Parâmetros**: `pattern`, `path` (opcional)

### ls
- **Descrição**: Lista arquivos e subdiretórios no diretório atual
- **Parâmetros**: `path` (opcional, padrão: ".")

### list_directory
- **Descrição**: Lista estrutura de diretório recursiva
- **Parâmetros**: `path`, `max_depth` (opcional, padrão: 3)

## 🔧 Configuração Avançada

### Servidor llama.cpp

Para rodar o servidor:
```bash
./build/bin/llama-server -m ~/Documentos/Models/Qwen3.5-9B-Q8_0.gguf \
  --alias model-turbo \
  --cache-type-k turbo3 \
  --cache-type-v turbo3 \
  --c 262144 \
  --port 8080 \
  --jinja
```

### Ambiente Python

Recomendado usar virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📚 Documentação

- [ARCHITECTURE.md](ARCHITECTURE.md) - Documentação detalhada da arquitetura
- [SECURITY.md](SECURITY.md) - Informações de segurança e limitações
- [README.md](README.md) - Visão geral deste documento

## 📦 Dependências

- Python 3.8+
- llama.cpp servidor rodando em localhost:8080
- httpx (para comunicação HTTP)
- pydantic (para validação de dados)

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor:
1. Crie uma issue explicando o problema ou funcionalidade
2. Fork o repositório
3. Crie uma branch para sua feature
4. Commit suas mudanças
5. Push para a branch
6. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo LICENSE para detalhes.

## 📞 Contato

- GitHub Issues: [Issues do projeto](#)
- Email: (adicionar email se necessário)

## ⚠️ Disclaimer

Este software é fornecido "AS IS" sem garantias de qualquer tipo. O autor não é responsável por quaisquer danos diretos, indiretos, incidentais, especiais ou consecutivos resultantes do uso deste software.

**Use com responsabilidade!**

---

**Última atualização:** 04/06/2026  
**Versão:** 1.0.0  
**Licença:** MIT

# Segurança - Agente LLM Local com llama.cpp

## 🛡️ Visão Geral

Este projeto executa um agente de linguagem que pode interagir com o sistema de arquivos e terminal do usuário. Para garantir segurança, foram implementadas várias medidas de proteção.

## ✅ Limitações de Segurança Implementadas

### 1. **TerminalTool - Whitelist de Comandos**

O módulo `TerminalTool` utiliza uma whitelist de comandos permitidos:

**Comandos Permitidos:**
- `ls`, `ls -la`, `ls -lh`, `ls -R`
- `cat`, `head`, `tail`, `grep`, `find`, `tree`
- `pwd`, `whoami`, `date`, `clear`, `history`
- `python`, `python3`, `pip`, `pip3`
- `mkdir`, `cp`, `mv`
- `tar`, `zip`, `unzip`, `git`
- `echo`, `printf`
- `sort`, `uniq`, `wc`, `cut`, `awk`, `sed`
- `rm -rf` (com cuidado)
- `bash`, `zsh`

**Comandos BLOQUEADOS:**
- Qualquer comando não na whitelist
- Operações de shell perigosas (mkfs, mount, etc.)
- Comandos com redirecionamentos maliciosos

### 2. **WriteFileTool - Validação de Caminho**

**Proteções Implementadas:**
- Não permite caminhos absolutos fora de `/home/cachy`
- Remove `..` para evitar path traversal
- Valida permissões antes de escrever
- Limite de tamanho de arquivo (1MB máximo)

**Exemplo de proteção:**
```python
# Tenta escrever em /etc/malicious.txt
path = Path("/etc/malicious.txt")

# O código verifica se começa com '/home/cachy'
# Se não, retorna erro de segurança
```

### 3. **ReadFileTool - Validação de Caminho**

**Proteções Implementadas:**
- Não permite ler arquivos fora de `/home/cachy`
- Limite de tamanho (100KB)
- Limite de linhas lidas (500 linhas)

### 4. **Timeout e Controle de Recursos**

- Timeout máximo de 30 segundos para comandos
- Limites de tamanho para arquivos
- Limites de número de linhas
- Máximo de iterações no controller

## ⚠️ Práticas Recomendadas

### Para Uso Pessoal (Seguro)

1. **Use em ambiente controlado** - Seu próprio computador
2. **Monitore o que o agente executa** - Leia os logs
3. **Evite comandos desconhecidos** - Não digite comandos não testados

### Para Produção (Adicionais)

1. **Run em container Docker** - Isolation completa
2. **Use um usuário não-root** - Minimize danos potenciais
3. **Implemente logging de auditoria** - Monitore ações
4. **Restrinja acesso de rede** - Firewall para localhost apenas

## 🔍 Monitoramento de Segurança

### Logs de Segurança

O agente gera logs para:
- Conexões com o servidor LLM
- Execução de ferramentas
- Erros de segurança

**Verifique os logs em:**
```bash
# Logs do sistema
tail -f /var/log/syslog | grep llama

# Ou no próprio terminal do agente
python -m llama_cpp_agent.run
```

### Comandos para Verificação

```bash
# Verifica se o servidor está rodando
curl http://localhost:8080/v1/models

# Verifica logs de segurança
grep "llama-cpp-agent" /var/log/syslog
```

## 🚨 Incidentes de Segurança

### Se suspeitar de um ataque:

1. **Interrompa imediatamente:**
   ```bash
   # Ctrl+C no terminal do agente
   # ou mate o processo
   killall llama-cpp-agent
   ```

2. **Verifique o sistema:**
   ```bash
   # Verifica arquivos modificados
   find /home/cachy -mmin -5 -type f
   
   # Verifica processos suspeitos
   ps aux | grep python
   ```

3. **Restaura do backup** (se disponível)

## 📝 Histórico de Mudanças de Segurança

### v1.0.0 (Atual)
- ✅ Implementada whitelist de comandos no TerminalTool
- ✅ Validação de caminhos no WriteFileTool
- ✅ Validação de caminhos no ReadFileTool
- ✅ Timeout e limites de recursos
- ✅ Documentação de segurança

### v0.9.0 (Anterior)
- ⚠️ Vulnerabilidade: Command injection no TerminalTool
- ⚠️ Vulnerabilidade: Path traversal no WriteFileTool

## 🛠️ Contribuição de Segurança

Se você encontrar uma vulnerabilidade ou tem uma sugestão de segurança:

1. **Não suba o exploit** - Só envie o código
2. **Crie uma issue no GitHub**
3. **Forneça exemplos de ataque**
4. **Sugira correções**

## 📞 Contato de Segurança

Para reportar vulnerabilidades:
- GitHub Issues
- Email direto (se disponível no repositório)

## ⚖️ Licença de Uso

Este código é fornecido "AS IS". O usuário é responsável por:
- Não usar em ambientes não controlados
- Não executar comandos maliciosos
- Usar em conformidade com as leis locais

---

**Última atualização:** 04/06/2026  
**Versão:** 1.0.0

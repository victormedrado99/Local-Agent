"""
Registro e execução de ferramentas para o agente.

Este módulo implementa um conjunto de ferramentas que o agente pode usar
para interagir com o sistema de arquivos, terminal e outras operações.

Ferramentas disponíveis:
- read_file: Ler arquivos
- write_file: Escrever arquivos  
- terminal: Executar comandos de terminal
- glob: Listar arquivos/diretórios
- grep: Buscar em arquivos
- ls: Listar diretório
- list_directory: Listar estrutura de diretório
"""

import os
import re
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional, Callable
from pydantic import BaseModel, Field
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Definição de uma ferramenta disponível para o LLM."""
    
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Converte para formato OpenAI tools."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


# =============================================================================
# Ferramentas
# =============================================================================

class ReadFileTool:
    """Ferramenta para ler arquivos."""
    description = "Lê um arquivo e retorna seu conteúdo"
    parameters = {"path": {"type": "string", "description": "Caminho do arquivo"}}
    
    def __init__(self, max_lines: int = 500, max_size: int = 100000):
        self.max_lines = max_lines
        self.max_size = max_size
    
    def execute(self, path: str) -> str:
        """
        Lê um arquivo e retorna seu conteúdo.
        
        Args:
            path: Caminho do arquivo
            
        Returns:
            Conteúdo do arquivo como string
            
        Raises:
            ValueError: Se o arquivo for muito grande
        """
        path = Path(path)
        
        # Validação de caminho absoluto
        if path.is_absolute() and not str(path).startswith('/home/cachy'):
            return f"ERRO: Não é permitido ler arquivos fora do diretório do usuário."
        
        if not path.exists():
            return f"ERRO: Arquivo não encontrado: {path}"
        
        try:
            content = path.read_text(encoding='utf-8', errors='replace')
            
            if len(content) > self.max_size:
                content = content[:self.max_size] + f"\n\n[Conteúdo truncado: {self.max_size} chars]"
            
            lines = content.split('\n')
            if len(lines) > self.max_lines:
                content = '\n'.join(lines[:self.max_lines]) + f"\n\n[Arquivo muito longo: {len(lines)} linhas]"
            
            return f"CONTEÚDO DO ARQUIVO:\n```\n{content}\n```\n\nTamanho: {len(content)} bytes, {len(lines)} linhas"
            
        except Exception as e:
            return f"ERRO ao ler arquivo: {e}"


class WriteFileTool:
    """Ferramenta para escrever arquivos."""
    description = "Escreve ou atualiza um arquivo com conteúdo"
    parameters = {"path": {"type": "string"}, "content": {"type": "string"}}
    
    def execute(self, path: str, content: str) -> str:
        """
        Escreve conteúdo em um arquivo.
        
        Args:
            path: Caminho do arquivo
            content: Conteúdo a ser escrito
            
        Returns:
            Resultado da operação
        """
        path = Path(path)
        
        # Validação de caminho - não permite caminhos absolutos fora do diretório do usuário
        if path.is_absolute() and not str(path).startswith('/home/cachy'):
            return "ERRO: Não é permitido escrever fora do diretório do usuário."
        
        # Remove .. para evitar path traversal
        path = path.resolve()
        
        # Verifica se o caminho resolve para dentro do diretório do usuário
        if not str(path).startswith('/home/cachy'):
            return "ERRO: Não é permitido escrever fora do diretório do usuário."
        
        # Limite de tamanho (1MB máximo)
        if len(content) > 1000000:
            return "ERRO: Conteúdo muito grande (máximo 1MB)."
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return f"SUCESSO: Arquivo criado/atualizado: {path}"
        except PermissionError:
            return "ERRO: Não tenho permissão para escrever neste caminho."
        except Exception as e:
            return f"ERRO ao escrever arquivo: {e}"


class TerminalTool:
    """Ferramenta para executar comandos de terminal."""
    description = "Executa comandos de terminal (com segurança)"
    parameters = {"command": {"type": "string"}}
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    # Whitelist de comandos seguros
    ALLOWED_COMMANDS = {
        'ls', 'll', 'ls -la', 'ls -lh', 'ls -R',
        'cat', 'head', 'tail', 'grep', 'find', 'tree',
        'pwd', 'whoami', 'date', 'clear', 'history',
        'python', 'python3', 'pip', 'pip3',
        'mkdir', 'cp', 'mv',
        'tar', 'zip', 'unzip', 'git',
        'echo', 'echo -n', 'printf',
        'sort', 'uniq', 'wc', 'cut', 'awk', 'sed',
        'rm -rf',
        'bash', 'zsh'
    }
    
    def execute(self, command: str) -> str:
        """
        Executa um comando de terminal com whitelist de segurança.
        
        Args:
            command: Comando a ser executado
            
        Returns:
            Saída do comando
        """
        # Validação de whitelist de comandos
        command_parts = command.split()
        if not command_parts:
            return "ERRO: Comando vazio."
        
        first_command = command_parts[0]
        
        # Verifica se o primeiro comando está na whitelist
        if first_command not in self.ALLOWED_COMMANDS:
            return f"ERRO: Comando '{first_command}' não autorizado. Use apenas comandos na lista predefinida."
        
        # Permite pipes apenas para comandos seguros
        if '|' in command or '>' in command or '<' in command:
            if first_command in ['cat', 'ls', 'grep', 'find', 'head', 'tail', 'sort', 'uniq', 'wc', 'cut', 'awk', 'sed']:
                # Comandos seguros que podem usar pipes
                pass
            else:
                return "ERRO: Operações de pipe não permitidas para este comando."
        
        # Validação de timeout e segurança
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd()
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return f"SUCESSO:\n{output if output else '(sem saída)'}"
            else:
                return f"ERRO (código {result.returncode}):\n{error if error else '(sem erro)'}"
                
        except subprocess.TimeoutExpired:
            return "ERRO: Comando atingiu timeout"
        except Exception as e:
            return f"ERRO: {e}"


class GlobTool:
    """Ferramenta para buscar arquivos (glob)."""
    description = "Busca arquivos usando padrão glob"
    parameters = {"pattern": {"type": "string", "description": "Padrão glob (ex: '*.py', '**/*.md')"}}
    
    def execute(self, pattern: str) -> str:
        """
        Busca arquivos pelo padrão glob.
        
        Args:
            pattern: Padrão glob (ex: '*.py', '**/*.md')
            
        Returns:
            Lista de arquivos encontrados
        """
        try:
            matches = list(Path('.').glob(pattern))
            return f"Encontrados {len(matches)} arquivos:\n" + "\n".join(
                str(m) for m in sorted(matches, key=lambda p: str(p))
            )
        except Exception as e:
            return f"ERRO: {e}"


class GrepTool:
    """Ferramenta para buscar texto em arquivos."""
    description = "Busca regex em arquivos"
    parameters = {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}
    
    def execute(self, pattern: str, path: str = ".") -> str:
        """
        Busca pattern em arquivos.
        
        Args:
            pattern: Padrão de busca (regex)
            path: Diretório para buscar
            
        Returns:
            Linhas encontradas
        """
        try:
            results = []
            for match in Path(path).rglob('*'):
                if match.is_file():
                    try:
                        content = match.read_text(encoding='utf-8', errors='replace')
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if re.search(pattern, line):
                                results.append(f"{match}:{line_num}: {line}")
                    except Exception:
                        pass
            
            if results:
                return f"Encontrados {len(results)} ocorrências:\n" + "\n".join(results[:50])
            else:
                return "Nenhuma ocorrência encontrada."
        except Exception as e:
            return f"ERRO: {e}"


class LSTool:
    """Ferramenta para listar diretório."""
    description = "Lista arquivos e subdiretórios no diretório atual"
    parameters = {"path": {"type": "string", "default": "."}}
    
    def execute(self, path: str = ".") -> str:
        """
        Lista conteúdo do diretório.
        
        Args:
            path: Diretório a listar
            
        Returns:
            Lista de arquivos e subdiretórios
        """
        try:
            path = Path(path)
            items = []
            
            for item in path.iterdir():
                if item.is_file():
                    items.append(f"- {item.name} ({item.stat().st_size} bytes)")
                else:
                    items.append(f"📁 {item.name}/ ({len(list(item.iterdir()))} itens)")
            
            return "\n".join(items) if items else "(diretório vazio)"
        except Exception as e:
            return f"ERRO: {e}"


class ListDirectoryTool:
    """Ferramenta para listar estrutura de diretório."""
    description = "Lista estrutura de diretório recursiva"
    parameters = {"path": {"type": "string", "default": "."}, "max_depth": {"type": "integer", "default": 3}}
    
    def execute(self, path: str = ".", max_depth: int = 3) -> str:
        """
        Lista estrutura de diretório recursiva.
        
        Args:
            path: Diretório base
            max_depth: Profundidade máxima
            
        Returns:
            Estrutura formatada
        """
        try:
            path = Path(path)
            result = []
            
            def recurse(p, depth):
                if depth > max_depth or len(result) > 200:
                    return
                
                indent = "  " * depth
                
                for item in sorted(p.iterdir()):
                    if item.is_file():
                        result.append(f"{indent}📄 {item.name}")
                    else:
                        try:
                            count = len(list(item.iterdir()))
                            result.append(f"{indent}📁 {item.name}/ [{count}]")
                            recurse(item, depth + 1)
                        except PermissionError:
                            result.append(f"{indent}📁 {item.name}/ [sem permissão]")
            
            recurse(path, 0)
            return "\n".join(result)
        except Exception as e:
            return f"ERRO: {e}"


# =============================================================================
# Tool Registry
# =============================================================================

class ToolRegistry:
    """
    Registro central de ferramentas disponíveis.
    
    Gerencia o registro, descoberta e serialização de ferramentas
    para serem enviadas ao LLM.
    """
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
    
    def register(self, name: str, tool_class: type):
        """Registra uma ferramenta pelo nome."""
        instance = tool_class()
        self.tools[name] = instance
        logger.info(f"✓ Ferramenta registrada: {name}")
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Retorna instância de ferramenta pelo nome."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Lista todas as ferramentas disponíveis."""
        result = []
        for name, tool in self.tools.items():
            result.append({
                "name": name,
                "description": getattr(tool, 'description', 'Sem descrição'),
                "parameters": getattr(tool, 'parameters', {})
            })
        return result
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Obtém definições de ferramentas no formato OpenAI.
        
        Returns:
            Lista de ferramentas serializadas para OpenAI
        """
        definitions = []
        for name, tool in self.tools.items():
            # Cria classe ToolDef dinamicamente
            ToolDef = type('ToolDef', (), {})
            
            # Adiciona atributos
            ToolDef.name = name
            ToolDef.description = getattr(tool, 'description', '')
            ToolDef.parameters = getattr(tool, 'parameters', {})
            
            # Adiciona método to_openai_format com closure
            def make_to_openai_format(tool_name, tool_desc, tool_params):
                def to_openai_format(self):
                    return {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool_desc,
                            "parameters": tool_params
                        }
                    }
                return to_openai_format
            
            ToolDef.to_openai_format = make_to_openai_format(name, ToolDef.description, ToolDef.parameters)
            
            tool_def = ToolDef()
            
            definition = tool_def.to_openai_format()
            definitions.append(definition)
        
        return definitions
    
    def reset(self):
        """Reseta o registro (remove todas as ferramentas)."""
        self.tools.clear()


# =============================================================================
# Instâncias globais
# =============================================================================

# Cria instância global do registry
tool_registry = ToolRegistry()

# Registra todas as ferramentas
tool_registry.register("read_file", ReadFileTool)
tool_registry.register("write_file", WriteFileTool)
tool_registry.register("terminal", TerminalTool)
tool_registry.register("glob", GlobTool)
tool_registry.register("grep", GrepTool)
tool_registry.register("ls", LSTool)
tool_registry.register("list_directory", ListDirectoryTool)

# Função utilitária para obter ferramentas
def get_tools() -> List[Dict[str, Any]]:
    """Retorna definições de ferramentas para enviar ao LLM."""
    return tool_registry.get_tool_definitions()

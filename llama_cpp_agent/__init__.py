"""
LLM Agent Package

Um agente inteligente que se comunica com servidor llama.cpp
para executar tarefas de terminal, manipulação de arquivos e mais.

Estrutura:
├── llm_client.py      # Cliente OpenAI-compatible
├── tools.py           # Ferramentas (read, write, terminal, etc.)
├── controller.py      # Controller principal do agente
└── interactive.py     # Interface de linha de comando

Uso:
    from llama_cpp_agent import AgentController, LLMClient
    
    # Inicializa cliente
    client = LLMClient(
        base_url="http://localhost:8080/v1",
        model="model-turbo"
    )
    
    # Cria controller
    agent = AgentController(client)
    
    # Executa conversa
    response = agent.run("Execute um hello world em Python")
    print(response)
"""

from .llm_client import LLMClient, ChatMessage
from .tools import (
    tool_registry,
    get_tools,
    ReadFileTool,
    WriteFileTool,
    TerminalTool,
    GlobTool,
    GrepTool,
    LSTool,
    ListDirectoryTool
)
from .controller import AgentController, AgentState

__version__ = "0.1.0"
__all__ = [
    "LLMClient",
    "ChatMessage", 
    "tool_registry",
    "get_tools",
    "AgentController",
    "AgentState",
    "ReadFileTool",
    "WriteFileTool",
    "TerminalTool",
    "GlobTool",
    "GrepTool",
    "LSTool",
    "ListDirectoryTool"
]

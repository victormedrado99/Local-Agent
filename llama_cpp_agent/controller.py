"""
Controller do agente LLM.

Este módulo implementa o loop principal do agente, gerenciando:
- Estado da conversa (context window)
- Decisões de tool calling
- Execução e feedback de ferramentas
- Streaming de respostas
"""

import json
import logging
from typing import Dict, List, Any, Optional, Iterator, Union
from datetime import datetime

from .llm_client import LLMClient
from .tools import tool_registry

logger = logging.getLogger(__name__)


class AgentState:
    """Estado do agente durante a execução."""
    
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_tool_calls: List[Dict[str, Any]] = []
        self.current_message: Optional[Dict[str, Any]] = None
        self.response_content: str = ""
    
    def add_message(self, role: str, content: str, tool_calls: List = None):
        """Adiciona mensagem ao histórico."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'tool_calls': tool_calls or []
        }
        self.conversation_history.append(message)
        logger.info(f"✓ {role}: {content[:50]}...")
    
    def get_context_window(self, max_tokens: int = 16384) -> List[Dict[str, Any]]:
        """Retorna histórico com limite de tokens."""
        # Simplificação: limite por mensagens (não tokens reais)
        return self.conversation_history[-20:]  # Últimas 20 mensagens
    
    def clear(self):
        """Limpa o estado."""
        self.conversation_history.clear()
        self.pending_tool_calls.clear()
        self.response_content = ""


class AgentController:
    """
    Controlador principal do agente.
    
    Gerencia o ciclo completo:
    1. Recebe mensagem do usuário
    2. Prepara contexto + ferramentas
    3. Envia para LLM
    4. Processa tool_calls se necessário
    5. Executa ferramentas
    6. Envia resultados de volta ao LLM
    7. Retorna resposta final
    
    Arquitetura do loop:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ User Input   │───▶│ LLM Request  │───▶│ Tool Call    │
    └──────────────┘    └──────────────┘    └──────────────┘
                               │                    │
                               ▼                    ▼
                        ┌──────────────┐    ┌──────────────┐
                        │ Final Output │◀───│ Execute Tool │
                        └──────────────┘    └──────────────┘
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 5,
        temperature: float = 0.7
    ):
        """
        Inicializa o controller.
        
        Args:
            llm_client: Cliente LLM configurado
            tools: Lista de ferramentas (se None, usa padrão)
            max_iterations: Máximo de iterações de tool calling
            temperature: Temperatura do modelo
        """
        self.llm = llm_client
        self.tools = tools or get_tools()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.state = AgentState()
    
    def run(
        self,
        user_message: str,
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """
        Executa o agente com a mensagem do usuário.
        
        Args:
            user_message: Mensagem do usuário
            stream: Habilitar streaming
            
        Returns:
            Resposta final ou stream de texto
        """
        # Adiciona mensagem inicial
        self.state.add_message("user", user_message)
        
        # Loop principal
        iteration = 0
        current_messages = self.state.get_context_window()
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"--- Iteração {iteration} ---")
            
            # Envia para LLM
            response = self.llm.chat(
                messages=current_messages,
                tools=self.tools,
                tool_choice="auto",
                stream=stream
            )
            
            # Processa resposta
            if stream:
                final_response = self._process_stream_response(response, current_messages)
                return final_response
            else:
                response_dict = response
                final_response = self._process_response(response_dict, current_messages)
            
            if final_response is None:
                # Nenhuma resposta final (apenas tool calls pendentes)
                continue
            
            # Adiciona resposta ao histórico
            self.state.add_message("assistant", final_response)
            
            # Verifica se há novas tool calls
            new_tool_calls = self._extract_tool_calls(final_response)
            
            if new_tool_calls:
                logger.info(f"🛠️  Tool calls detectadas: {len(new_tool_calls)}")
                # Adiciona tool calls ao histórico
                for tc in new_tool_calls:
                    self.state.add_message("assistant", "", tool_calls=[tc])
                
                # Processa tool calls
                tool_results = self._execute_tool_calls(new_tool_calls)
                
                # Adiciona resultados
                for result in tool_results:
                    self.state.add_message("tool", result)
                
                # Atualiza contexto para próxima iteração
                current_messages = self.state.get_context_window()
                
            else:
                # Nenhuma nova tool call - resposta final!
                return final_response
        
        # Atingiu máximo de iterações
        return "⚠️  Alcançado limite máximo de iterações."
    
    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrai tool calls de uma resposta do LLM.
        
        Args:
            response: Resposta do LLM
            
        Returns:
            Lista de tool calls
        """
        tool_calls = []
        
        if 'choices' not in response or not response['choices']:
            return tool_calls
        
        choice = response['choices'][0]
        
        if 'message' in choice:
            message = choice['message']
            
            if 'tool_calls' in message and message['tool_calls']:
                for tc in message['tool_calls']:
                    tool_calls.append({
                        'name': tc['function']['name'],
                        'arguments': tc['function']['arguments']
                    })
        
        return tool_calls
    
    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[str]:
        """
        Executa todas as tool calls.
        
        Args:
            tool_calls: Lista de tool calls
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for tc in tool_calls:
            tool_name = tc['name']
            args = json.loads(tc['arguments']) if tc.get('arguments') else {}
            
            # Busca ferramenta
            tool = tool_registry.get_tool(tool_name)
            
            if not tool:
                results.append(f"ERRO: Ferramenta '{tool_name}' não encontrada")
                continue
            
            try:
                logger.info(f"🔧 Executando: {tool_name}({args})")
                result = tool.execute(**args)
                results.append(f"📌 [{tool_name}]: {result}")
                
            except Exception as e:
                results.append(f"❌ [{tool_name}] ERRO: {e}")
        
        return results
    
    def _process_response(
        self,
        response: Dict[str, Any],
        current_messages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Processa resposta completa (não streaming).
        
        Args:
            response: Resposta do LLM
            current_messages: Histórico atual
            
        Returns:
            Resposta final ou None se houver mais iterações
        """
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if not content.strip():
            # Apenas tool calls, sem conteúdo
            return None
        
        # Remove tool calls da resposta final (elas foram executadas)
        final_content = content
        
        return final_content
    
    def _process_stream_response(
        self,
        response: Iterator[Dict[str, Any]],
        current_messages: List[Dict[str, Any]]
    ) -> Iterator[str]:
        """
        Processa stream de resposta.
        
        Args:
            response: Stream de chunks
            current_messages: Histórico atual
            
        Yields:
            Chunks de texto
        """
        accumulated_content = ""
        has_tool_calls = False
        
        for chunk in response:
            content = chunk.get('content', '')
            
            if content:
                yield content
                accumulated_content += content
            
            if chunk.get('tool_calls'):
                has_tool_calls = True
        
        # Se teve tool calls, continua o loop
        if has_tool_calls:
            logger.info("⏳ Tool calls detectadas em stream...")
            # Adiciona ao histórico
            self.state.add_message("assistant", accumulated_content)
            
            new_tool_calls = self._extract_tool_calls({
                'choices': [{'message': {'content': accumulated_content, 'tool_calls': []}}]
            })
            
            # Executa e continua
            tool_results = self._execute_tool_calls(new_tool_calls)
            
            for result in tool_results:
                self.state.add_message("tool", result)
            
            # Atualiza contexto e continua
            current_messages = self.state.get_context_window()
            
            # Retorna stream contínuo (repassa para o caller)
            yield from self.run(user_message="", stream=True)
        else:
            # Resposta final
            self.state.add_message("assistant", accumulated_content)
            yield from accumulated_content
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """
        Envia mensagens de chat diretamente.
        
        Args:
            messages: Lista de mensagens
            stream: Habilitar streaming
            
        Returns:
            Resposta ou stream
        """
        # Adiciona última mensagem do usuário
        if messages and any(m['role'] == 'user' for m in messages):
            user_msg = [m for m in messages if m['role'] == 'user'][-1]
            self.state.add_message("user", user_msg['content'])
        else:
            self.state.add_message("user", messages[0]['content'] if messages else "")
        
        return self.run(
            user_message=messages[-1]['content'] if messages else "",
            stream=stream
        )


def get_tools() -> List[Dict[str, Any]]:
    """Retorna definições de ferramentas para enviar ao LLM."""
    return tool_registry.get_tool_definitions()


if __name__ == "__main__":
    # Teste básico
    from .llm_client import LLMClient
    
    print("Inicializando agente...")
    
    client = LLMClient(
        base_url="http://localhost:8080/v1",
        model="model-turbo"
    )
    
    if client.health_check():
        controller = AgentController(llm_client=client)
        
        print("\nTestando com mensagem simples:")
        print("-" * 50)
        
        response = controller.run("Olá, você pode me ajudar com algo?")
        print("\nResposta:", response)
        
    else:
        print("✗ Não consegui conectar ao servidor LLM")

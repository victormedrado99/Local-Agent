"""
Cliente LLM para comunicação com servidor llama.cpp via API OpenAI-compatible.

Este módulo implementa uma interface unificada para interagir com o servidor
llama.cpp, utilizando o SDK OpenAI padrão.

Arquitetura:
┌────────────────────────────────────┐
│         LLMClient                  │
├────────────────────────────────────┤
│  - openai.Client (wrapper)         │
│  - Chat completions                │
│  - Tool calling support            │
│  - Streaming responses             │
└────────────────────────────────────┘
"""

import os
import time
from typing import Dict, List, Optional, Any, Iterator, Union
import openai
from openai import OpenAI
from pydantic import BaseModel, Field
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    Cliente para comunicação com servidor llama.cpp.
    
    Usa a API OpenAI-compatible exposta pelo llama-server.
    
    Exemplo de uso:
    ```python
    client = LLMClient(
        base_url="http://localhost:8080/v1",
        api_key="dummy",
        model="model-turbo"
    )
    response = client.chat.completions.create(
        model="model-turbo",
        messages=[{"role": "user", "content": "Olá!"}],
        tools=[...]
    )
    ```
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        api_key: str = "dummy",
        model: str = "model-turbo",
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Inicializa o cliente LLM.
        
        Args:
            base_url: URL do endpoint da API (ex: http://localhost:8080/v1)
            api_key: API key (pode ser 'dummy' para llama.cpp)
            model: Nome do modelo no servidor (ex: 'model-turbo')
            timeout: Timeout em segundos para requisições
            temperature: Temperatura para geração do modelo
            max_tokens: Máximo de tokens por resposta
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Inicializa cliente OpenAI
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )
        
        # Verifica conexão
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verifica se o servidor está acessível."""
        try:
            # Tenta health check
            health_url = f"{self.base_url}/health"
            response = self.client.models.list(timeout=5)
            logger.info(f"✓ Conectado ao servidor em {self.base_url}")
            logger.info(f"  Modelo: {self.model}")
            return True
        except Exception as e:
            logger.error(f"✗ Falha na conexão: {e}")
            return False
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        stream: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Envia mensagem de chat para o LLM.
        
        Args:
            messages: Lista de mensagens no formato OpenAI
                [{'role': 'user', 'content': '...'}, ...]
            tools: Lista de ferramentas disponíveis (schema OpenAI)
            tool_choice: "auto", "none", ou nome da ferramenta
            stream: Habilitar streaming de resposta
            
        Returns:
            Resposta do LLM (dicionário ou stream)
        """
        if stream:
            return self._chat_stream(messages, tools, tool_choice)
        else:
            return self._chat_complete(messages, tools, tool_choice)
    
    def _chat_complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """Executa chat completion síncrono."""
        try:
            logger.info(f"Enviando {len(messages)} mensagens para {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )
            
            return response.model_dump(mode='json')
            
        except Exception as e:
            logger.error(f"Erro na chat completion: {e}")
            raise
    
    def _chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ) -> Iterator[Dict[str, Any]]:
        """Executa chat completion com streaming."""
        try:
            logger.info(f"Streaming resposta de {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                stream=True,
                timeout=self.timeout
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    yield {
                        'role': 'assistant' if delta.role is None else delta.role,
                        'content': delta.content or '',
                        'tool_calls': [
                            {
                                'id': call.id,
                                'function': call.function,
                            }
                            for call in (chunk.choices[0].delta.tool_calls or [])
                        ]
                    }
            
        except Exception as e:
            logger.error(f"Erro no streaming: {e}")
            raise
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Obtém informações sobre os modelos disponíveis."""
        try:
            response = self.client.models.list()
            models = [m for m in response.data if m.id == self.model]
            if models:
                return models[0].model_dump(mode='json')
            return None
        except Exception as e:
            logger.error(f"Erro ao obter model info: {e}")
            return None
    
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        """
        Streaming simples de chat (apenas texto).
        
        Returns:
            Gerador de strings (chunks de texto)
        """
        for chunk in self._chat_stream(messages, tools):
            if chunk.get('content'):
                yield chunk['content']
    
    def health_check(self) -> bool:
        """Verifica se o servidor está saudável."""
        try:
            response = self.client.models.list()
            return len(response.data) > 0
        except Exception:
            return False
    
    def close(self):
        """Fecha conexão."""
        self.client.close()


class ChatMessage:
    """Representação simplificada de mensagens de chat."""
    
    def __init__(self, role: str, content: str):
        self.role = role  # 'user', 'assistant', 'system'
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {'role': self.role, 'content': self.content}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        return cls(role=data['role'], content=data['content'])


if __name__ == "__main__":
    # Exemplo de uso
    print("Testando conexão com llama.cpp...")
    
    client = LLMClient(
        base_url="http://localhost:8080/v1",
        api_key="dummy",
        model="model-turbo"
    )
    
    if client.health_check():
        print("✓ Servidor online!")
        
        # Teste simples
        messages = [
            {"role": "user", "content": "Olá, como posso ajudar?"}
        ]
        
        print("\nResposta do modelo:")
        for chunk in client.stream_chat(messages):
            print(chunk, end='', flush=True)
    else:
        print("✗ Não consegui conectar. Verifique:")
        print("  1. Se o servidor llama.cpp está rodando")
        print("  2. Se a porta 8080 está acessível")
        print("  3. Se o modelo 'model-turbo' está configurado")

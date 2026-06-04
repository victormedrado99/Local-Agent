"""
Interface interativa de linha de comando para o agente.

Permite conversar com o agente via terminal, executando comandos,
listando arquivos, etc.

Uso:
    python -m llama_cpp_agent.run
"""

import sys
import signal
import logging
from typing import Optional

from .llm_client import LLMClient
from .controller import AgentController
from .tools import get_tools

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class InteractiveAgent:
    """Agente interativo de terminal."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        api_key: str = "dummy",
        model: str = "model-turbo",
        max_iterations: int = 5
    ):
        """
        Inicializa o agente interativo.
        
        Args:
            base_url: URL do servidor LLM
            api_key: API key
            model: Nome do modelo
            max_iterations: Máximo de iterações por tarefa
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.max_iterations = max_iterations
        
        self.client = LLMClient(
            base_url=base_url,
            api_key=api_key,
            model=model
        )
        
        self.controller = AgentController(
            llm_client=self.client,
            tools=get_tools(),
            max_iterations=max_iterations
        )
    
    def connect(self) -> bool:
        """Conecta ao servidor LLM."""
        if self.client.health_check():
            logger.info(f"✓ Conectado a {self.base_url}")
            logger.info(f"  Modelo: {self.model}")
            return True
        else:
            logger.error("✗ Falha na conexão. Verifique:")
            logger.error("  1. Se o servidor llama.cpp está rodando")
            logger.error(f"  2. Se {self.base_url} está acessível")
            return False
    
    def handle_exit(self, signum, frame):
        """Lida com Ctrl+C."""
        logger.info("\n\nSaindo...")
        self.client.close()
        sys.exit(0)
    
    def print_banner(self):
        """Imprime banner de boas-vindas."""
        print("\n" + "=" * 60)
        print("  LLM AGENTE LOCAL (llama.cpp)")
        print("=" * 60)
        print(f"\nServidor: {self.base_url}")
        print(f"\\nModelo: {self.model}")
        print("\\nFerramentas disponíveis:")
        for tool in get_tools():
            print(f"  • {tool['function']['name']}: {tool.get('function', {}).get('description', 'Sem descrição')}")
        print("\\nComandos:")
        print("  /help      - Mostra ajuda")
        print("  /clear     - Limpa tela")
        print("  /quit      - Sair")
        print("  /tools     - Lista ferramentas")
        print("-" * 60 + "\n")
    
    def format_response(self, response: str) -> str:
        """Formata resposta do agente."""
        lines = response.split('\n')
        formatted = []
        indent = "  "
        
        for line in lines:
            if line.strip().startswith("```"):
                formatted.append(line)
            elif any(line.strip().startswith(tool) for tool in ["SUCESSO:", "ERRO:", "CONTEÚDO", "📌", "🔧", "❌", "🛠️"]):
                formatted.append(line)
            else:
                formatted.append(line)
        
        return "\n".join(formatted)
    
    def run(self):
        """Executa loop interativo."""
        # Instala handlers
        signal.signal(signal.SIGINT, self.handle_exit)
        
        # Conecta
        if not self.connect():
            return
        
        # Banner
        self.print_banner()
        
        # Loop principal
        print("\n💬 Agente pronto. Digite sua mensagem (ou '/quit' para sair):")
        
        while True:
            try:
                # Prompt
                user_input = input("\n👤 Você: ").strip()
                
                if not user_input:
                    continue
                
                # Comandos especiais
                if user_input.lower() == '/quit' or user_input.lower() == '/exit':
                    print("\nSaindo...")
                    break
                
                elif user_input.lower() == '/help':
                    print("\n=== AJUDA ===")
                    print("/help    - Mostra esta ajuda")
                    print("/clear   - Limpa tela")
                    print("/quit    - Sai do programa")
                    print("/tools   - Lista ferramentas")
                    print("/reset   - Reseta conversa")
                    continue
                
                elif user_input.lower() == '/clear':
                    print("\n" + "=" * 60)
                    continue
                
                elif user_input.lower() == '/tools':
                    print("\n=== FERRAMENTAS ===")
                    for tool in get_tools():
                        print(f"  • {tool['name']}: {tool['description']}")
                    continue
                
                elif user_input.lower() == '/reset':
                    self.controller.state.clear()
                    print("\n✓ Conversa resetada")
                    continue
                
                # Executa agente
                print("\n🤖 Agente pensando...")
                print("-" * 50)
                
                response = self.controller.run(user_input, stream=False)
                
                print("-" * 50)
                print("\n📝 Resposta:\n")
                print(self.format_response(response))
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupção detectada")
                break
            except Exception as e:
                print(f"\n❌ Erro: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Agente LLM interativo com llama.cpp"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080/v1",
        help="URL do servidor LLM"
    )
    parser.add_argument(
        "--api-key",
        default="dummy",
        help="API key"
    )
    parser.add_argument(
        "--model",
        default="model-turbo",
        help="Nome do modelo"
    )
    parser.add_argument(
        "--max-it",
        type=int,
        default=5,
        help="Máximo de iterações"
    )
    
    args = parser.parse_args()
    
    agent = InteractiveAgent(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
        max_iterations=args.max_it
    )
    
    agent.run()


if __name__ == "__main__":
    main()

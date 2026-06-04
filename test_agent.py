#!/usr/bin/env python3
"""
Script de teste para o agente LLM.

Este script demonstra como usar a API do agente programaticamente.
"""

import sys
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection():
    """Testa conexão com servidor LLM."""
    print("\n" + "=" * 60)
    print("TESTE 1: Conexão com Servidor LLM")
    print("=" * 60)
    
    try:
        from llama_cpp_agent import LLMClient
        
        client = LLMClient(
            base_url="http://localhost:8080/v1",
            api_key="dummy",
            model="model-turbo"
        )
        
        if client.health_check():
            print("✓ Conexão estabelecida!")
            
            # Testa modelo
            info = client.get_model_info()
            if info:
                print(f"✓ Modelo encontrado: {info.get('id', 'unknown')}")
            
            return True
        else:
            print("✗ Falha na conexão")
            print("  Verifique se o servidor llama.cpp está rodando:")
            print("  ./build/bin/llama-server -m ~/Documentos/Models/Qwen3.5-9B-Q8_0.gguf \\")
            print("    --alias model-turbo --jinja -c 262144 --port 8080")
            return False
            
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


def test_tools():
    """Testa ferramentas disponíveis."""
    print("\n" + "=" * 60)
    print("TESTE 2: Ferramentas Disponíveis")
    print("=" * 60)
    
    from llama_cpp_agent import get_tools
    
    tools = get_tools()
    
    print(f"\n{len(tools)} ferramentas registradas:\n")
    
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool['name']}")
        print(f"   {tool['description']}")
        print()


def test_chat():
    """Testa chat básico."""
    print("\n" + "=" * 60)
    print("TESTE 3: Chat Básico")
    print("=" * 60)
    
    try:
        from llama_cpp_agent import LLMClient, AgentController, get_tools
        
        client = LLMClient(
            base_url="http://localhost:8080/v1",
            model="model-turbo"
        )
        
        controller = AgentController(
            llm_client=client,
            tools=get_tools(),
            max_iterations=3
        )
        
        test_messages = [
            "Olá, quem é você?",
            "Quais são as suas capacidades?",
            "O que você pode fazer com as ferramentas?"
        ]
        
        for msg in test_messages:
            print(f"\n👤 {msg}")
            response = controller.run(msg)
            print(f"🤖 {response[:200]}..." if len(response) > 200 else f"🤖 {response}")
        
    except Exception as e:
        print(f"✗ Erro: {e}")


def test_tools_execution():
    """Testa execução de ferramentas."""
    print("\n" + "=" * 60)
    print("TESTE 4: Execução de Ferramentas")
    print("=" * 60)
    
    try:
        from llama_cpp_agent import LLMClient, AgentController, get_tools
        
        client = LLMClient(
            base_url="http://localhost:8080/v1",
            model="model-turbo"
        )
        
        controller = AgentController(
            llm_client=client,
            tools=get_tools(),
            max_iterations=2
        )
        
        # Teste: listar diretório atual
        print("\n👤 Liste o diretório atual:")
        response = controller.run("Liste os arquivos no diretório atual")
        print(f"\n🤖 {response[:300]}...")
        
        # Teste: criar arquivo
        print("\n👤 Crie um arquivo de teste:")
        response = controller.run("Crie um arquivo chamado teste.txt com o conteúdo 'Olá, mundo!'")
        print(f"\n🤖 {response}")
        
    except Exception as e:
        print(f"✗ Erro: {e}")


def test_terminal():
    """Testa execução de terminal."""
    print("\n" + "=" * 60)
    print("TESTE 5: Execução de Terminal")
    print("=" * 60)
    
    try:
        from llama_cpp_agent import LLMClient, AgentController, get_tools
        
        client = LLMClient(
            base_url="http://localhost:8080/v1",
            model="model-turbo"
        )
        
        controller = AgentController(
            llm_client=client,
            tools=get_tools(),
            max_iterations=2
        )
        
        print("\n👤 Execute 'echo Hello World':")
        response = controller.run("Execute o comando 'echo Hello World'")
        print(f"\n🤖 {response}")
        
    except Exception as e:
        print(f"✗ Erro: {e}")


def test_streaming():
    """Testa streaming de resposta."""
    print("\n" + "=" * 60)
    print("TESTE 6: Streaming")
    print("=" * 60)
    
    try:
        from llama_cpp_agent import LLMClient, AgentController, get_tools
        
        client = LLMClient(
            base_url="http://localhost:8080/v1",
            model="model-turbo"
        )
        
        controller = AgentController(
            llm_client=client,
            tools=get_tools(),
            max_iterations=1
        )
        
        print("\n👤 Gere um poema curto:")
        print("🤖 ", end="")
        
        response = controller.run("Escreva um poema curto sobre Python", stream=True)
        
    except Exception as e:
        print(f"✗ Erro: {e}")


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("  TESTE COMPLETO DO AGENTE LLM LOCAL")
    print("=" * 70)
    
    tests = [
        ("Conexão", test_connection),
        ("Ferramentas", test_tools),
        ("Chat", test_chat),
        ("Ferramentas (Execução)", test_tools_execution),
        ("Terminal", test_terminal),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "✓ PASSOU" if result else "✗ FALHOU"))
        except Exception as e:
            results.append((name, f"✗ ERRO: {e}"))
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)
    
    for name, status in results:
        symbol = "✓" if "PASSOU" in status else "✗"
        print(f"  {symbol} {name}: {status}")
    
    # Conclusão
    passed = sum(1 for _, s in results if "PASSOU" in s)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram!")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique a conexão.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Testes para agente LLM local"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Executa todos os testes"
    )
    parser.add_argument(
        "--connection",
        action="store_true",
        help="Teste de conexão"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Teste de chat"
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="Teste de ferramentas"
    )
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Teste de terminal"
    )
    
    args = parser.parse_args()
    
    if args.all or args.connection:
        test_connection()
    
    if args.all or args.tools:
        test_tools()
    
    if args.all or args.chat:
        test_chat()
    
    if args.all or args.tools:
        test_tools_execution()
    
    if args.all or args.terminal:
        test_terminal()
    
    if args.all:
        test_streaming()
        run_all_tests()


if __name__ == "__main__":
    main()

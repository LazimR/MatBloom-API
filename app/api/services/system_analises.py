import httpx
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Carrega a API Key do .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def gerar_questoes_reforco(
    questao_errada: List[str],
    nivel_bloom: List[int],
    conteudo: List[str],
    numero_questoes_por_nivel: int = 2,
    incluir_todos_niveis: bool = False
) -> Dict[str, List[str]]:
    """
    Gera questões de reforço baseadas no erro do aluno e na Taxonomia de Bloom.

    Args:
        questao_errada (str): Questão que o aluno errou.
        nivel_bloom (int): Nível da Taxonomia de Bloom (1-6).
        conteudo (str): Tema específico da questão.
        numero_questoes_por_nivel (int): Quantidade de questões por nível (padrão: 2).
        incluir_todos_niveis (bool): Se True, gera questões para todos os níveis (1-6).

    Returns:
        Dict[str, List[str]]: Dicionário com questões agrupadas por nível.
    """
    # Construção do prompt
    prompt = """
    Você é um tutor especializado em reforço escolar. Gere 2 questões para CADA nível da Taxonomia de Bloom (total: 12 questões), com base no erro do aluno descrito abaixo. 
Seja direto, sem uso de dicas ou falas de contextualização na saida do prompt. 

**Regras**:  
- Use verbos típicos de cada nível (ex: "liste" para Nível 1, "explique" para Nível 2, "resolva" para Nível 3).  
- Mantenha o foco no conteúdo específico mencionado.  
- Retorne questões apenas dos niveis que o aluno errou

**Input do Usuário**:  
"O aluno errou: [QUESTÃO].  
Nível da questão: [1-6].  
Conteúdo: [TEMA]."  

**Output (Formato Markdown)**:  
### Nível [X]: [Nome do Nível]  
1. "[Questão]"  
   - **a**: "[...]"  
   - **b**: "[...]" 
    - **c**: "[...]"  
    - **d**: "[...]"   
2. "[Questão]"  
   - **a**: "[...]"  
   - **b**: "[...]" 
    - **c**: "[...]"  
    - **d**: "[...]"    

"""

    for i in range(len(questao_errada)): 
        prompt += f"""
        O aluno errou: '{questao_errada[i]}'.
        Nível da questão na Taxonomia de Bloom: {nivel_bloom[i]}.
        Conteúdo específico: '{conteudo[i]}'.

        """
    
    if incluir_todos_niveis:
        prompt += f"Gere {numero_questoes_por_nivel} questões para CADA nível (1 a 6), com exemplos de resposta."
    else:
        prompt += f"Gere {numero_questoes_por_nivel} questões APENAS para o nível {nivel_bloom}, com exemplos de resposta."

    # Chamada à API do DeepSeek
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",  # endpoint correto
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",  # ou outro modelo suportado pela Groq
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30.0
            )
            response.raise_for_status()
            return _processar_resposta(response.json(), incluir_todos_niveis)
    
    except httpx.HTTPStatusError as e:
        raise Exception(f"Erro na API: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Erro ao gerar questões: {str(e)}")

def _processar_resposta(resposta_api: Dict, incluir_todos_niveis: bool) -> Dict[str, List[str]]:
    """
    Processa a resposta da API para extrair as questões geradas.
    """
    texto_resposta = resposta_api["choices"][0]["message"]["content"]
    
    # Exemplo de pós-processamento (ajuste conforme o formato da resposta do DeepSeek)
    if incluir_todos_niveis:
        return {"questoes_por_nivel": texto_resposta}  # Ou parseie o texto para um dicionário estruturado
    else:
        return {"questoes": texto_resposta.split("\n")}  # Divide por linhas
    

if __name__ == "__main__":

    import asyncio
    # Exemplo de uso
    questao_errada = ["Resolva 2x + 3 = 11"]
    nivel_bloom = [3]
    conteudo = ["equações do 1º grau"]
    
    questoes_geradas = asyncio.run(gerar_questoes_reforco(questao_errada, nivel_bloom, conteudo))
    for i in range(len(questoes_geradas["questoes"])):
        print(questoes_geradas["questoes"][i]+"\n")
UNCLASSIFIED_LEVEL = 0

BLOOM_LEVELS = {
    1: {
        "name": "Lembrar",
        "description": (
            "Recuperar diretamente da memória fatos, definições, símbolos, "
            "fórmulas, propriedades ou resultados matemáticos conhecidos, sem "
            "executar procedimentos de resolução ou realizar transformações matemáticas.\n\n"

            "Exemplos:\n"
            "- Qual é a fórmula da área de um círculo?\n"
            "- Qual é o símbolo do número pi?\n"
            "- Qual é o nome da propriedade x² · x³ = x⁵?"
        ),
    },

    2: {
        "name": "Entender",
        "description": (
            "Interpretar conceitos, símbolos, propriedades, representações ou "
            "relações matemáticas, explicando significados ou identificando equivalências, "
            "sem realizar cálculos para obter um resultado numérico.\n\n"

            "Exemplos:\n"
            "- O que significa a expressão 2⁵?\n"
            "- Qual expressão representa uma potência de base 2 e expoente 5?\n"
            "- Identifique a propriedade utilizada em x² · x³ = x⁵."
        ),
    },

    3: {
        "name": "Aplicar",
        "description": (
            "Executar cálculos, algoritmos, fórmulas, propriedades ou procedimentos "
            "matemáticos conhecidos para resolver exercícios ou problemas. A presença "
            "de um contexto narrativo não altera o nível se a resolução exigir apenas "
            "a aplicação direta de um procedimento conhecido.\n\n"

            "Exemplos:\n"
            "- Calcule 2⁵.\n"
            "- Resolva x² - 5x + 6 = 0 utilizando fatoração.\n"
            "- Determine a área de um círculo de raio 5 cm.\n"
            "- Uma colmeia dobra sua população a cada mês. Se começou com 50 abelhas, quantas haverá após 3 meses?"
        ),
    },

    4: {
        "name": "Analisar",
        "description": (
            "Decompor um problema, identificar relações, padrões ou informações relevantes, "
            "comparar diferentes abordagens ou determinar qual estratégia matemática deve "
            "ser utilizada antes da resolução. Não classifique como analisar apenas porque "
            "a questão possui um enunciado longo ou uma situação contextualizada.\n\n"

            "Exemplos:\n"
            "- Compare os métodos de fatoração e Bhaskara para resolver uma equação.\n"
            "- Identifique qual propriedade matemática deve ser utilizada para simplificar uma expressão e justifique.\n"
            "- Analise um problema e determine quais informações são necessárias para sua resolução."
        ),
    },

    5: {
        "name": "Avaliar",
        "description": (
            "Julgar a validade, eficiência ou adequação de soluções, estratégias ou "
            "argumentos matemáticos com base em critérios matemáticos definidos.\n\n"

            "Exemplos:\n"
            "- Um aluno resolveu uma equação e encontrou x = 3. A solução está correta? Justifique.\n"
            "- Compare dois métodos de resolução e determine qual é mais eficiente.\n"
            "- Avalie se um argumento matemático é matematicamente válido."
        ),
    },

    6: {
        "name": "Criar",
        "description": (
            "Produzir novos problemas, modelos, estratégias, generalizações ou "
            "métodos matemáticos originais para resolver situações não familiares.\n\n"

            "Exemplos:\n"
            "- Crie um problema cuja solução envolva uma equação exponencial.\n"
            "- Desenvolva uma estratégia diferente para resolver um problema matemático.\n"
            "- Formule uma regra geral para o padrão observado."
        ),
    },
}

BLOOM_LEVEL_NAMES = {level: data["name"] for level, data in BLOOM_LEVELS.items()}

VALID_BLOOM_LEVELS = frozenset(BLOOM_LEVELS.keys())


def is_classified_level(level: int) -> bool:
    return level in VALID_BLOOM_LEVELS


def bloom_level_name(level: int) -> str:
    return BLOOM_LEVELS[level]["name"]


def bloom_level_description(level: int) -> str:
    return BLOOM_LEVELS[level]["description"]


def format_bloom_levels_for_prompt() -> str:
    return "\n".join(
        f"- Nível {level} ({data['name']}): {data['description']}"
        for level, data in sorted(BLOOM_LEVELS.items())
    )

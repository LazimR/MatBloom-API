# Estágio de construção
FROM python:3.11-slim as builder

WORKDIR /app

# Dependências do sistema para build de pacotes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala o Poetry
RUN pip install poetry

# Configura o Poetry para não criar ambientes virtuais
RUN poetry config virtualenvs.create false

# Copia os arquivos de dependências
COPY pyproject.toml poetry.lock ./

# Instala as dependências globalmente
RUN poetry install --no-root

# Exporta as dependências para um arquivo requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt 

# Estágio final
FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema para OCR/OpenCV e healthcheck do banco
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copia o código-fonte do projeto
COPY . .

# Copia o arquivo requirements.txt do estágio de build
COPY --from=builder /app/requirements.txt ./

# Instala as dependências globalmente
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x /app/scripts/docker-entrypoint.sh

# Cria um usuário não root para rodar a aplicação
RUN useradd -m apiuser
USER apiuser

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["/app/scripts/docker-entrypoint.sh"]

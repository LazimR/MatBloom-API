# Estágio de construção
FROM python:3.11-slim as builder

WORKDIR /api

# Instala o Poetry
RUN pip install poetry

# Copia os arquivos de dependência
COPY pyproject.toml poetry.lock ./

# Instala as dependências
RUN poetry install --no-root --no-dev

# Estágio final
FROM python:3.11-slim

WORKDIR /api

# Cria um usuário não root
RUN useradd -m apiuser
USER apiuser

# Copia as dependências instaladas
COPY --from=builder /api /api

# Copia o código-fonte
COPY . .

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
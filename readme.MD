# MatBloom API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

API principal do Sistema MatBloom para correção automática de avaliações utilizando Taxonomia de Bloom

## 🔍 Sobre o Projeto

A API MatBloom fornece:

✅ Integração com o sistema de correção automática por imagem da Fundação 1Bi  
✅ Processamento de gabaritos e geração de relatórios  
✅ Gerenciamento de atividades baseadas nos erros dos alunos  
✅ Autenticação segura e gerenciamento de usuários  

## 🛠️ Tecnologias Principais

**Core:**
- FastAPI (Python 3.11+)
- PostgreSQL (SQLAlchemy ORM)
- Pydantic v2 (validação de dados)

**Processamento de Documentos:**
- ReportLab (geração de PDF)
- WeasyPrint
- PyPDF2

**Visão Computacional:**
- OpenCV
- PyTesseract (OCR)

**Segurança:**
- JWT (python-jose)
- Bcrypt (hash de senhas)

## 📦 Dependências

Consulte o arquivo `pyproject.toml` para a lista completa de dependências gerenciadas pelo Poetry.

## 🚀 Como Executar

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/matbloom-api.git
cd matbloom-api
```

2. Instale as dependências (usando Poetry):
```bash
poetry install
```

3.Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o .env com suas configurações
```
4.Execute a API:
```bash
poetry run uvicorn main:app --reload
```

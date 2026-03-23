# MatBloom API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

API do MatBloom para gerenciamento pedagógico, geração de provas, correção automática de gabaritos e análise educacional baseada na Taxonomia de Bloom.

## Sobre

O backend do MatBloom foi estruturado para atender o fluxo principal do sistema:

- autenticação com papéis `admin`, `diretor` e `professor`
- gerenciamento de usuários, turmas, alunos, conteúdos, questões e provas
- biblioteca de modelos de prova por tema
- aplicação de modelos de prova em turmas
- vínculo professor-turma com controle de escopo
- registro de respostas/notas por tentativa
- correção automática de gabaritos por imagem
- análises pedagógicas por aluno e por turma
- geração automática de reforço com base em erros e níveis da Taxonomia de Bloom

## Stack

### Core
- FastAPI
- Python 3.11+
- SQLAlchemy ORM
- Pydantic v2
- PostgreSQL

### Segurança
- JWT com `python-jose`
- Hash de senha com `passlib` + `bcrypt`

### Documentos e OCR
- ReportLab
- WeasyPrint
- PyPDF2
- OpenCV
- PyTesseract

### IA
- Integração com Groq para geração de reforço pedagógico

## Organização

```text
app/
  api/
    endpoints/
    schemas/
    security/
    services/
  core/
  db/
    models/
    repositories/
  test/
```

## Funcionalidades atuais

### Gestão acadêmica
- CRUD de turmas
- CRUD de alunos
- CRUD de conteúdos
- CRUD de questões
- criação de modelos de prova
- aplicação de modelos de prova em turmas
- listagem de biblioteca de provas e aplicações
- CRUD de respostas/notas (`test_response`)

### Autorização
- `admin` gerencia usuários e vínculos professor-turma
- `diretor` gerencia turmas, alunos e notas
- `professor` acessa apenas alunos, notas e análises das turmas vinculadas a ele
- `professor` pode consultar modelos de prova da biblioteca
- `professor` pode aplicar modelos somente nas próprias turmas
- aplicações de prova seguem escopo por turma

### Provas e correção
- provas agora possuem dois papéis no backend:
  - `template`: modelo reutilizável da biblioteca
  - `application`: aplicação concreta de um modelo em turma
- modelos podem ser reutilizados por tema
- aplicações registram vínculo com turma, aplicador e modelo de origem
- geração de PDF de prova e gabarito
- correção automática por imagem
- armazenamento das respostas, nota, questões erradas e data da tentativa

### Análise pedagógica
- análise por aluno
- análise por turma
- média geral
- média por prova
- desempenho por nível de Bloom
- erros por conteúdo
- erros por nível cognitivo
- reforço automático a partir dos erros do aluno

## Rotas principais

### Usuários
- `POST /user/login`
- `POST /user/`
- `GET /user/`
- `GET /user/{username}`
- `PUT /user/`
- `DELETE /user/`
- `GET /user/{user_id}/classrooms`
- `POST /user/{user_id}/classrooms/{classroom_id}`
- `DELETE /user/{user_id}/classrooms/{classroom_id}`

### Turmas
- `POST /classroom/`
- `GET /classroom/`
- `GET /classroom/{classroom_id}`
- `GET /classroom/{classroom_id}/analysis`
- `PUT /classroom/`
- `DELETE /classroom/{classroom_id}`

### Alunos
- `POST /student/`
- `GET /student/`
- `GET /student/{student_id}`
- `GET /student/{student_id}/analysis`
- `POST /student/{student_id}/analysis/reinforcement`
- `PUT /student/`
- `DELETE /student/{student_id}`

### Questões, conteúdos e provas
- `POST /content/`
- `GET /content/`
- `GET /content/{content_id}`
- `PUT /content/{content_id}`
- `DELETE /content/{content_id}`
- `GET /question/all_questions`
- `GET /question/{question_id}`
- `POST /question/`
- `DELETE /question/`
- `POST /test/`
- `GET /test/`
- `GET /test/templates`
- `GET /test/applications`
- `POST /test/{test_id}/apply`
- `GET /test/{test_id}`
- `GET /test/test_generate`
- `DELETE /test/{test_id}`

### Notas e correção
- `POST /test-response/`
- `GET /test-response/`
- `GET /test-response/{test_response_id}`
- `PUT /test-response/`
- `DELETE /test-response/{test_response_id}`
- `POST /answer-sheet/answer_sheet`

## Configuração

Crie um `.env` a partir de `.env.example`.

### Variáveis esperadas

```env
DB_HOST=matbloom-db
DB_PORT=5432
DB_NAME=matbloom
DB_USER=postgres
DB_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@matbloom-db:5432/matbloom

SECRET_KEY=sua_chave_secreta
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

GROQ_API_KEY=
```

O backend usa `DATABASE_URL` quando ela estiver definida. Caso contrário, a URL é montada a partir de `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`.

## Execução local

### 1. Instale as dependências

```bash
poetry install
```

### 2. Configure o ambiente

```bash
cp .env.example .env
```

### 3. Suba a API

```bash
poetry run uvicorn app.main:app --reload
```

### 4. Acesse a documentação

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testes

A suíte atual cobre fluxos principais de autenticação, rotas base, criação de entidades, análise pedagógica, escopo por turma, vínculo professor-turma e regras principais da nova estrutura de provas.

```bash
PYTHONPATH=. poetry run python -m pytest -q
```

Estado atual da suíte:

- `24 passed`

## Observações importantes

- o backend não depende mais de `create_all()` no startup para “migrar” o banco
- a modelagem de provas foi evoluída para suportar biblioteca/modelo e aplicação por turma
- as mudanças de modelagem já feitas no código exigem migração real no PostgreSQL
- o fluxo de OCR/correção automática já foi estabilizado, mas ainda vale aprofundar os testes dessa parte

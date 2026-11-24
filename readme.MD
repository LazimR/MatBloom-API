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
- `diretor` pode cadastrar e listar professores e gerenciar seus vínculos com turmas; apenas `admin` pode cadastrar diretores e administradores
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
- a aplicação pode ser marcada para não contar na média geral; as notas continuam visíveis por prova e os erros continuam nas análises
- a escolha vale para todas as respostas da aplicação, inclusive as já registradas, e é aplicada ao confirmar uma correção
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
- `GET /user/directory/teachers`
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
- `POST /answer-sheet/preview` — lê uma ou mais imagens ou um ZIP sem registrar notas
- `POST /answer-sheet/confirm` — registra uma resposta conferida e pode definir se a aplicação conta na média

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
poetry run pytest -q
```

Estado atual da suíte:

- `51 passed, 1 warning`

## Observações importantes

- o backend não depende mais de `create_all()` no startup para “migrar” o banco
- a modelagem de provas foi evoluída para suportar biblioteca/modelo e aplicação por turma
- a suíte pode ser executada localmente com `poetry run pytest -q`, sem depender de `PYTHONPATH=.`
- as mudanças de modelagem já feitas no código exigem migração real no PostgreSQL
- o fluxo de OCR/correção automática já foi estabilizado, mas ainda vale aprofundar os testes dessa parte

## Experimento de tempo de classificação de Bloom

Edite manualmente `scripts/quest.json` para conter a quantidade desejada de questões
(por exemplo: 1, 5, 10, 20 ou 30) e execute o script a partir de `MatBloom-API`:

```bash
poetry run python scripts/classify_questions_repeat.py scripts/quest.json 10 --provider deepseek -o resultados/5questoes_deepseek.json
```

O número `10` é a quantidade de repetições. Troque o nome da saída a cada condição
do experimento para preservar os resultados anteriores. O script lê a entrada uma
vez por execução do comando e usa as mesmas questões em todas as repetições.
Por padrão, classifica somente questões com `level: 0`; use `--force` para
reclassificar também questões já classificadas. Execuções sem questões pendentes
recebem o status `skipped` e não entram nas estatísticas de tempo.

O provedor padrão deste script é `deepseek`. Para Groq, informe `--provider groq`.
Modelo, temperatura, tamanho do lote e limite de tentativas vêm do `.env`.
O argumento `--delay` substitui a pausa entre lotes; as pausas por limite da API
continuam seguindo a configuração de novas tentativas. No experimento, as novas
tentativas automáticas internas do SDK são desativadas para que cada chamada
seja registrada; a repetição explícita para erros 429 continua ativa.

Para o nome de saída acima, são produzidos:

| Arquivo | Conteúdo |
| --- | --- |
| `5questoes_deepseek_1.json`, `_2.json`, etc. | Questões classificadas em cada repetição concluída |
| `5questoes_deepseek_metrics.csv` | Uma linha por execução, com status, tempos, contagens, falhas e produtividade |
| `5questoes_deepseek_requests.csv` | Uma linha por tentativa de API, com lote, duração e código HTTP ou erro |
| `5questoes_deepseek_waits.csv` | Esperas solicitadas e medidas, separadas entre lotes e limite da API |
| `5questoes_deepseek_summary.json` | Configurações, identificação da entrada e do código, resultados e estatísticas |

Todos os tempos estão em segundos. `total_seconds` mede a classificação completa,
incluindo validação e esperas, e exclui leitura e gravação dos arquivos.
`api_seconds` soma todas as tentativas, inclusive as que retornam erro.
`batch_wait_seconds` e `retry_wait_seconds` registram separadamente as esperas
efetivamente medidas. `other_seconds` é o tempo restante de processamento local.
`seconds_per_question` é o tempo total dividido pelo número de questões
classificadas naquela execução; é uma medida amortizada, não a latência individual
de uma questão quando há várias no mesmo lote.

As estatísticas incluem média, mediana, desvio padrão amostral, mínimo e máximo
somente das execuções bem-sucedidas que classificaram questões. O desvio padrão
fica `null` com menos de duas execuções válidas. As falhas ficam nos relatórios,
as próximas repetições continuam e o comando retorna código 1 se houve falha.
Os relatórios são atualizados após cada repetição.

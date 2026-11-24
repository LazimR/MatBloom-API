# MatBloom API

API do MatBloom para gestão de questões e avaliações de Matemática, classificação por níveis da Taxonomia de Bloom, correção de gabaritos e análise de desempenho.

## Tecnologias

- Python 3.11 ou superior, FastAPI, Pydantic e SQLAlchemy
- PostgreSQL e Alembic para banco de dados e migrações
- DeepSeek ou Groq para classificação de questões por modelo de linguagem
- OpenCV e Tesseract para leitura de gabaritos por imagem
- ReportLab e WeasyPrint para documentos PDF
- JWT em cookie HTTP-only para sessão e bcrypt para senhas

## Funcionalidades

- Cadastro de usuários, turmas, alunos, conteúdos e questões. O administrador pode criar diretores e professores; o diretor pode criar professores e gerenciar turmas, alunos e vínculos de professores.
- Classificação automática de questões sem nível informado, usando um prompt estruturado. O professor pode corrigir o nível posteriormente. O provedor deve estar configurado para o cadastro automático funcionar.
- Modelos reutilizáveis de prova e aplicações vinculadas a uma turma ou a um aluno. As questões de uma aplicação precisam ter a mesma quantidade de alternativas, entre 2 e 5, para gerar o gabarito.
- Seleção de questões existentes por conteúdo ou histórico de erros, com sugestões para reforço. Essa seleção não cria questões novas.
- Geração de prova e gabarito em PDF. A correção aceita imagens e oferece uma prévia antes de confirmar as respostas e a nota.
- Análise por aluno e por turma, com desempenho por nível de Bloom e erros por conteúdo. Uma aplicação pode ser marcada para não contribuir para a média geral; suas respostas continuam no histórico e nas análises.

Os professores têm acesso às turmas vinculadas. Confira as classificações e a leitura das imagens antes de confirmar os resultados.

## Configuração

```bash
cp .env.example .env
```

Edite `.env` conforme o ambiente:

- `DATABASE_URL` tem prioridade sobre `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`. O endereço de exemplo `matbloom-db` funciona na rede do Docker; para uma API local, use o endereço e a porta do PostgreSQL acessível pelo seu computador, por exemplo `localhost`.
- Configure `SECRET_KEY`, `JWT_ALGORITHM` e `ACCESS_TOKEN_EXPIRE_MINUTES` para autenticação. `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE` e `FRONTEND_ORIGINS` controlam cookie e CORS.
- Para classificação automática, defina `CLASSIFICATION_PROVIDER=deepseek` e `DEEPSEEK_API_KEY`, ou `CLASSIFICATION_PROVIDER=groq` e `GROQ_API_KEY`. Modelo, temperatura, tamanho de lote, intervalos e tentativas são configuráveis no `.env.example`.
- `AUTO_MIGRATE` e `SEED_MOCK_DATA` são usados pelo script de inicialização do contêiner; executar o Uvicorn diretamente não aplica migrações nem carrega o seed.

Nunca inclua chaves ou senhas reais em arquivos versionados. O modelo e os demais parâmetros do arquivo de exemplo podem ser diferentes daqueles usados em uma bateria experimental específica; consulte os registros da bateria ao reproduzi-la.

## Executar localmente

Pré-requisitos: Python 3.11+, Poetry, PostgreSQL, Tesseract OCR e bibliotecas nativas exigidas pelo OpenCV e WeasyPrint. O [Dockerfile](Dockerfile) mostra as dependências de sistema instaladas na imagem.

1. Prepare o arquivo `.env`, configure o banco acessível localmente e instale as dependências:

   ```bash
   cp .env.example .env
   poetry install
   ```

2. Com o PostgreSQL disponível, aplique as migrações e inicie a API:

   ```bash
   poetry run alembic upgrade head
   poetry run uvicorn app.main:app --reload
   ```

3. Acesse <http://localhost:8000/docs> para a documentação interativa ou <http://localhost:8000/redoc> para o ReDoc. `/health` verifica a conexão com o banco.

Para subir API, banco e interface em contêineres, siga o [README do projeto principal](../readme.MD).

### Usuário inicial e dados de exemplo

Em um banco sem usuários, `POST /user/` permite criar o primeiro usuário; escolha o papel `admin` para administrar a instalação. Após a criação inicial, a rota aplica as regras de permissão. No Docker, `SEED_MOCK_DATA=if-empty` carrega os dados de exemplo se a tabela de usuários estiver vazia; `never` desativa a carga e `always` força sua execução.

**O arquivo `app/db/scripts/mock.sql` contém `TRUNCATE` e apaga os dados das tabelas listadas antes de inserir os exemplos.** Não execute o seed em um banco que precise ser preservado. No Compose do projeto principal, defina `SEED_MOCK_DATA` no ambiente do Compose ou no `.env` da raiz.

## Rotas principais

A lista completa e os formatos das requisições estão em `/docs`.

- Sessão: `POST /user/login`, `GET /user/session`, `POST /user/logout`.
- Usuários e vínculos: `POST /user/`, `GET /user/directory/teachers`, `POST` e `DELETE /user/{user_id}/classrooms/{classroom_id}`.
- Turmas e alunos: `/classroom/` e `/student/`; análises em `GET /classroom/{classroom_id}/analysis` e `GET /student/{student_id}/analysis`.
- Questões e conteúdos: `GET /question/all_questions`, `POST /question/`, `PATCH /question/{question_id}/level` e `/content/`.
- Provas: `POST /test/`, `GET /test/templates`, `POST /test/{test_id}/apply`, `GET /test/applications` e `GET /test/applications/{test_id}/generate`.
- Reforço: `GET /classroom/{classroom_id}/reinforcement-suggestions` e `GET /student/{student_id}/reinforcement-suggestions`.
- Correção: `POST /answer-sheet/preview` lê imagens ou ZIP sem gravar notas; `POST /answer-sheet/confirm` valida as respostas e recalcula a nota antes de registrar.

## Testes

```bash
poetry run pytest -q app/test/unit
```

Para executar toda a suíte, incluindo testes de integração, use `poetry run pytest -q`. Verifique os serviços e a configuração exigidos pelos testes de integração antes de executá-los.

## Organização

```text
app/api/endpoints/    Rotas HTTP
app/api/schemas/      Modelos de entrada e saída
app/api/security/     Autenticação e autorização
app/api/services/     Classificação, correção, PDFs e análises
app/core/             Definições de Bloom, papéis e regras de domínio
app/db/               Modelos, repositórios e dados de exemplo
app/test/             Testes unitários e de integração
alembic/              Migrações
scripts/              Inicialização e experimentos de classificação
```

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

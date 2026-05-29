#!/bin/sh

set -eu

AUTO_MIGRATE="${AUTO_MIGRATE:-true}"
SEED_MOCK_DATA="${SEED_MOCK_DATA:-if-empty}"
MOCK_SQL_PATH="${MOCK_SQL_PATH:-/app/app/db/scripts/mock.sql}"

wait_for_database() {
  echo "Aguardando banco de dados..."
  until pg_isready -d "${DATABASE_URL}"; do
    sleep 1
  done
}

run_migrations() {
  if [ "${AUTO_MIGRATE}" != "true" ]; then
    echo "AUTO_MIGRATE desabilitado. Pulando migrações."
    return
  fi

  echo "Aplicando migrações..."
  alembic upgrade head
}

seed_mock_data() {
  if [ "${SEED_MOCK_DATA}" = "never" ]; then
    echo "SEED_MOCK_DATA=never. Pulando carga de dados."
    return
  fi

  if [ ! -f "${MOCK_SQL_PATH}" ]; then
    echo "Arquivo de seed não encontrado em ${MOCK_SQL_PATH}. Pulando carga."
    return
  fi

  USER_COUNT="$(psql "${DATABASE_URL}" -tAc 'SELECT COUNT(*) FROM "user"')"

  if [ "${SEED_MOCK_DATA}" = "always" ] || [ "${USER_COUNT}" = "0" ]; then
    echo "Carregando dados mock..."
    psql "${DATABASE_URL}" -f "${MOCK_SQL_PATH}"
    return
  fi

  echo "Banco já possui usuários. Pulando carga de dados."
}

sync_sequences() {
  echo "Sincronizando sequences..."
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"user\"', 'id'), COALESCE((SELECT MAX(id) FROM \"user\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"user\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"classroom\"', 'id'), COALESCE((SELECT MAX(id) FROM \"classroom\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"classroom\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"student\"', 'id'), COALESCE((SELECT MAX(id) FROM \"student\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"student\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"content\"', 'id'), COALESCE((SELECT MAX(id) FROM \"content\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"content\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"question\"', 'id'), COALESCE((SELECT MAX(id) FROM \"question\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"question\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"test\"', 'id'), COALESCE((SELECT MAX(id) FROM \"test\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"test\"));"
  psql "${DATABASE_URL}" -c "SELECT setval(pg_get_serial_sequence('\"test_response\"', 'id'), COALESCE((SELECT MAX(id) FROM \"test_response\"), 1), (SELECT MAX(id) IS NOT NULL FROM \"test_response\"));"
}

wait_for_database
run_migrations
seed_mock_data
sync_sequences

echo "Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

FROM postgres:17.4-alpine3.21

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=matbloom

# Expose the PostgreSQL port
EXPOSE 5432

# Healthcheck to verify if the database is ready
HEALTHCHECK --interval=5s --timeout=5s --retries=5 \
  CMD pg_isready -U postgres -d matbloom

# Copy initialization scripts (optional)
#COPY ./init.sql /docker-entrypoint-initdb.d/

# Use the default entrypoint provided by the postgres image
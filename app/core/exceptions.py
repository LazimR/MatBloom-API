class AppError(Exception):
    status_code = 500
    detail = "Erro interno da aplicação."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Recurso não encontrado."


class ConflictError(AppError):
    status_code = 409
    detail = "Conflito de dados."


class ValidationError(AppError):
    status_code = 400
    detail = "Dados inválidos."


class OperationError(AppError):
    status_code = 500
    detail = "Falha ao executar a operação."

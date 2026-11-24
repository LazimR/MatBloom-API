"""Bounded expansion of uploaded answer-sheet images without extracting files to disk."""
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from app.core.exceptions import ValidationError

MAX_FILES = 50
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def image_uploads(uploads, allow_zip):
    images = []
    total_size = 0
    total_uploaded = 0
    for upload in uploads:
        name = PurePosixPath((upload.filename or "arquivo").replace("\\", "/")).name
        extension = PurePosixPath(name).suffix.lower()
        data = upload.file.read(MAX_UPLOAD_SIZE + 1)
        total_uploaded += len(data)
        if total_uploaded > MAX_UPLOAD_SIZE:
            raise ValidationError("O envio deve ter no máximo 50 MB.")
        if extension == ".zip":
            if not allow_zip:
                raise ValidationError("Para um aluno, envie uma única imagem, não um arquivo ZIP.")
            try:
                with ZipFile(BytesIO(data)) as archive:
                    for entry in archive.infolist():
                        if entry.is_dir() or PurePosixPath(entry.filename).name.startswith(".") or entry.filename.startswith("__MACOSX/"):
                            continue
                        entry_name = PurePosixPath(entry.filename.replace("\\", "/")).name
                        if PurePosixPath(entry_name).suffix.lower() not in IMAGE_EXTENSIONS:
                            raise ValidationError(f"O ZIP contém um arquivo que não é imagem suportada: {entry_name}.")
                        if entry.flag_bits & 1 or entry.file_size > MAX_IMAGE_SIZE:
                            raise ValidationError(f"Imagem {entry_name} protegida ou maior que 10 MB.")
                        total_size += entry.file_size
                        if total_size > MAX_UPLOAD_SIZE or len(images) >= MAX_FILES:
                            raise ValidationError("O lote deve conter até 50 imagens e 50 MB descompactados.")
                        with archive.open(entry) as source:
                            content = source.read(MAX_IMAGE_SIZE + 1)
                        if len(content) > MAX_IMAGE_SIZE:
                            raise ValidationError(f"Imagem {entry_name} maior que 10 MB.")
                        images.append((f"{name} / {entry_name}", content))
            except (BadZipFile, RuntimeError, OSError) as exc:
                raise ValidationError(f"Arquivo ZIP inválido: {name}.") from exc
        elif extension in IMAGE_EXTENSIONS:
            if len(data) > MAX_IMAGE_SIZE:
                raise ValidationError(f"Imagem {name} maior que 10 MB.")
            total_size += len(data)
            images.append((name, data))
        else:
            raise ValidationError(f"Formato não suportado: {name}. Use JPG, PNG, WEBP ou ZIP.")
        if total_size > MAX_UPLOAD_SIZE or len(images) > MAX_FILES:
            raise ValidationError("O lote deve conter até 50 imagens e 50 MB no total.")
    if not images:
        raise ValidationError("Selecione pelo menos uma imagem de gabarito.")
    if not allow_zip and len(images) != 1:
        raise ValidationError("Para um aluno, envie exatamente uma imagem.")
    return images

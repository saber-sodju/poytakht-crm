"""
File upload validators used across all FileField/ImageField in the project.
"""
import os
from django.core.exceptions import ValidationError

# 10 MB hard limit for any uploaded file
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Only these extensions may ever be uploaded
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# Explicitly rejected even if somehow renamed (double extensions etc.)
DANGEROUS_EXTENSIONS = {
    '.exe', '.js', '.html', '.htm', '.php', '.sh', '.bat', '.cmd',
    '.com', '.dll', '.msi', '.py', '.pl', '.cgi', '.svg', '.jar',
}


def _check_file(file, allowed_extensions):
    if file is None:
        return
    size = getattr(file, 'size', 0)
    if size and size > MAX_UPLOAD_SIZE:
        raise ValidationError(
            f'Файл слишком большой ({size / 1024 / 1024:.1f} МБ). '
            f'Максимум: {MAX_UPLOAD_SIZE // 1024 // 1024} МБ.'
        )

    name = (getattr(file, 'name', '') or '').lower()
    # Check every extension in the name to catch "shell.php.jpg"-style tricks
    parts = name.split('.')
    for part in parts[1:]:
        if f'.{part}' in DANGEROUS_EXTENSIONS:
            raise ValidationError('Этот тип файла запрещён из соображений безопасности.')

    ext = os.path.splitext(name)[1]
    if ext not in allowed_extensions:
        allowed = ', '.join(sorted(e.lstrip('.') for e in allowed_extensions))
        raise ValidationError(f'Недопустимый тип файла. Разрешены: {allowed}.')


def validate_document(file):
    """PDF or image — for receipts, contracts, expense documents."""
    _check_file(file, ALLOWED_DOCUMENT_EXTENSIONS)


def validate_image(file):
    """Image only — for avatars, photos, layouts."""
    _check_file(file, ALLOWED_IMAGE_EXTENSIONS)

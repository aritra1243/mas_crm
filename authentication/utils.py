import io
import zipfile
from typing import Iterable, Optional

from django.core.files.base import ContentFile
from django.utils import timezone


class FileBundleError(ValueError):
    """Raised when uploaded files violate bundling constraints."""


def bundle_uploaded_files(
    files: Iterable,
    base_name: str,
    *,
    limit: int = 10,
) -> Optional[ContentFile]:
    """
    Accept an iterable of uploaded file objects and return either the single file
    or a zipped archive containing all files.
    Raises FileBundleError if too many files are provided.
    """
    file_list = [f for f in files if f]
    if not file_list:
        return None

    if len(file_list) > limit:
        raise FileBundleError(f"Maximum {limit} files can be uploaded at once.")

    if len(file_list) == 1:
        return file_list[0]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        for index, uploaded in enumerate(file_list, start=1):
            filename = getattr(uploaded, 'name', f'file_{index}')
            # Ensure unique names inside the archive
            archive.writestr(f"{index:02d}_{filename}", uploaded.read())
            try:
                uploaded.seek(0)
            except Exception:
                continue
    buffer.seek(0)

    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"{base_name}_{timestamp}.zip"
    return ContentFile(buffer.getvalue(), name=zip_name)
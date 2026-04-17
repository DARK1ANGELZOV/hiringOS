import io
import zipfile

from fastapi import HTTPException, status


class FileSecurityService:
    EICAR_SIGNATURE = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

    @classmethod
    def detect_mime(cls, *, filename: str, content: bytes) -> str:
        lower = filename.lower()
        if content.startswith(b'%PDF-'):
            return 'application/pdf'
        if content.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return 'application/msword'

        if lower.endswith('.docx'):
            if not content.startswith(b'PK'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='DOCX must be a valid zip container')
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = set(archive.namelist())
                    if '[Content_Types].xml' not in names:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid DOCX structure')
            except zipfile.BadZipFile as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid DOCX structure') from exc
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        return 'application/octet-stream'

    @classmethod
    def validate_upload(
        cls,
        *,
        filename: str,
        content: bytes,
        provided_content_type: str | None,
        allowed_extensions: set[str],
        allowed_mime_types: set[str],
    ) -> tuple[str, str]:
        if '.' not in filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File extension is required')

        extension = '.' + filename.rsplit('.', 1)[-1].lower()
        if extension not in allowed_extensions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported file format')

        detected_mime = cls.detect_mime(filename=filename, content=content)
        if detected_mime not in allowed_mime_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported file mime type')

        normalized_provided = (provided_content_type or '').strip().lower()
        if normalized_provided and normalized_provided not in allowed_mime_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Provided content type is not allowed')

        return extension, detected_mime

    @classmethod
    def malware_precheck(cls, content: bytes) -> tuple[bool, str | None]:
        if cls.EICAR_SIGNATURE in content:
            return False, 'Malware signature detected (EICAR test string)'
        return True, None

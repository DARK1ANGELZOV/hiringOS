import io
import zipfile

import pytest
from fastapi import HTTPException

from app.services.file_security_service import FileSecurityService


def _minimal_docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode='w') as archive:
        archive.writestr('[Content_Types].xml', '<Types></Types>')
        archive.writestr('word/document.xml', '<w:document></w:document>')
    return buffer.getvalue()


def test_validate_upload_accepts_pdf_by_signature():
    extension, mime = FileSecurityService.validate_upload(
        filename='resume.pdf',
        content=b'%PDF-1.4\n...',
        provided_content_type='application/pdf',
        allowed_extensions={'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'},
        allowed_mime_types={
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
        },
    )
    assert extension == '.pdf'
    assert mime == 'application/pdf'


def test_validate_upload_rejects_invalid_docx_structure():
    with pytest.raises(HTTPException) as exc:
        FileSecurityService.validate_upload(
            filename='resume.docx',
            content=b'PK\x03\x04invalid',
            provided_content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            allowed_extensions={'.docx'},
            allowed_mime_types={'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
        )
    assert exc.value.status_code == 400


def test_validate_upload_accepts_valid_docx():
    extension, mime = FileSecurityService.validate_upload(
        filename='resume.docx',
        content=_minimal_docx_bytes(),
        provided_content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        allowed_extensions={'.docx'},
        allowed_mime_types={'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    )
    assert extension == '.docx'
    assert mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def test_malware_precheck_flags_eicar_signature():
    ok, reason = FileSecurityService.malware_precheck(
        b'prefix-' + FileSecurityService.EICAR_SIGNATURE + b'-suffix'
    )
    assert ok is False
    assert reason is not None and 'Malware signature detected' in reason


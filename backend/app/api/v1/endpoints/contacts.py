"""
Contact list and contact management endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.schemas.contact import (
    ContactListCreate,
    ContactListUpdate,
    ContactListResponse,
    ContactListListResponse,
    ContactListContactsResponse,
    FilePreviewResponse,
    ImportConfirmRequest,
    ImportResultResponse,
    ImportError,
    DNCEntryCreate,
    DNCEntryResponse,
    DNCListResponse,
    DNCCheckResponse,
)
from app.services.contact_service import ContactService
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Global service instance for file preview state (in production, use Redis)
_contact_service_cache: dict = {}


def get_contact_service(db: AsyncSession) -> ContactService:
    """Get or create ContactService instance."""
    # In production, you'd want to store file_id -> path mapping in Redis
    # For now, we use a simple dict cache
    service = ContactService(db)
    service._temp_files = _contact_service_cache
    return service


def validate_upload_file(filename: str, file_size: int) -> None:
    """Validate uploaded file."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )


# =============================================================================
# Contact List Endpoints
# =============================================================================

@router.get("/lists", response_model=ContactListListResponse)
async def list_contact_lists(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """List contact lists for the current user's organization."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    contact_lists, total = await service.list_contact_lists(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
    )

    return ContactListListResponse(
        items=contact_lists,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/lists", response_model=ContactListResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_list(
    data: ContactListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """Create a new empty contact list."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    contact_list = await service.create_contact_list(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        data=data,
    )

    return contact_list


@router.get("/lists/{list_id}", response_model=ContactListResponse)
async def get_contact_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """Get contact list details by ID."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    contact_list = await service.get_contact_list(list_id, current_user.organization_id)

    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found"
        )

    return contact_list


@router.patch("/lists/{list_id}", response_model=ContactListResponse)
async def update_contact_list(
    list_id: str,
    data: ContactListUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """Update contact list metadata."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    contact_list = await service.get_contact_list(list_id, current_user.organization_id)

    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found"
        )

    contact_list = await service.update_contact_list(contact_list, data)
    return contact_list


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """Delete a contact list and all its contacts."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    contact_list = await service.get_contact_list(list_id, current_user.organization_id)

    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found"
        )

    await service.delete_contact_list(contact_list)


# =============================================================================
# File Upload Endpoints
# =============================================================================

@router.post("/lists/upload/preview", response_model=FilePreviewResponse)
async def preview_upload_file(
    file: UploadFile = File(..., description="CSV or Excel file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Upload a file and get a preview with column headers.

    Returns column names, sample data, and suggested column mapping.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file
    validate_upload_file(file.filename or "unknown", file_size)

    # Reset file position
    await file.seek(0)

    service = get_contact_service(db)

    try:
        file_id, columns, preview_rows, row_count, suggested_mapping = service.preview_file(
            file_data=file.file,
            filename=file.filename or "upload.csv",
            preview_rows=10,
        )

        return FilePreviewResponse(
            file_id=file_id,
            filename=file.filename or "upload.csv",
            columns=columns,
            preview_rows=preview_rows,
            row_count=row_count,
            suggested_mapping=suggested_mapping,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to preview file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process file"
        )


@router.post("/lists/upload/confirm", response_model=ImportResultResponse)
async def confirm_upload(
    data: ImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Confirm import with column mapping.

    Uses the file_id from the preview step and applies the provided column mapping.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)

    try:
        contact_list, total, valid, invalid, duplicates, dnc_count, errors = await service.import_with_mapping(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            file_id=data.file_id,
            name=data.name,
            description=data.description,
            mapping=data.column_mapping,
        )

        return ImportResultResponse(
            list_id=contact_list.id,
            name=contact_list.name,
            total_rows=total,
            valid_contacts=valid,
            invalid_contacts=invalid,
            duplicate_contacts=duplicates,
            dnc_contacts=dnc_count,
            errors=errors,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to import contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import contacts"
        )


# =============================================================================
# Contact Endpoints
# =============================================================================

@router.get("/lists/{list_id}/contacts", response_model=ContactListContactsResponse)
async def list_contacts(
    list_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by phone, name, or email"),
    is_valid: Optional[bool] = Query(None, description="Filter by validity"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """List contacts in a contact list."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)

    # Verify contact list belongs to organization
    contact_list = await service.get_contact_list(list_id, current_user.organization_id)
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found"
        )

    contacts, total = await service.list_contacts(
        contact_list_id=list_id,
        page=page,
        page_size=page_size,
        search=search,
        is_valid=is_valid,
    )

    return ContactListContactsResponse(
        items=contacts,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/lists/{list_id}/download")
async def download_contacts(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """Download contacts as CSV."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)

    contact_list = await service.get_contact_list(list_id, current_user.organization_id)
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found"
        )

    try:
        csv_content = await service.export_contacts(contact_list)

        filename = f"{contact_list.name.replace(' ', '_')}_contacts.csv"

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(csv_content)),
            }
        )
    except Exception as e:
        logger.error(f"Failed to export contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export contacts"
        )


# =============================================================================
# DNC Endpoints
# =============================================================================

@router.get("/dnc", response_model=DNCListResponse)
async def list_dnc_entries(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by phone number"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """List DNC entries for the organization."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    entries, total = await service.list_dnc_entries(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
    )

    return DNCListResponse(
        items=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/dnc", response_model=DNCEntryResponse, status_code=status.HTTP_201_CREATED)
async def add_dnc_entry(
    data: DNCEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """Add a phone number to the DNC list."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)

    try:
        entry = await service.add_dnc_entry(
            phone_number=data.phone_number,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            reason=data.reason,
        )
        return entry

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/dnc/check", response_model=DNCCheckResponse)
async def check_dnc(
    phone_number: str = Query(..., description="Phone number to check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """Check if a phone number is on the DNC list."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    is_dnc = await service.check_dnc(phone_number, current_user.organization_id)

    return DNCCheckResponse(
        phone_number=phone_number,
        is_dnc=is_dnc,
        entry=None,  # Could be enhanced to return the entry if found
    )


@router.delete("/dnc/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dnc_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """Remove a DNC entry."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = get_contact_service(db)
    success = await service.remove_dnc_entry(entry_id, current_user.organization_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DNC entry not found"
        )

"""
Contact and ContactList Pydantic schemas.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator
import phonenumbers


# ============================================================================
# Contact List Schemas
# ============================================================================

class ContactListCreate(BaseModel):
    """Schema for creating a contact list."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class ContactListUpdate(BaseModel):
    """Schema for updating a contact list."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ContactListResponse(BaseModel):
    """Schema for contact list response."""
    id: str
    name: str
    description: Optional[str]
    organization_id: str
    total_contacts: int
    valid_contacts: int
    invalid_contacts: int
    is_active: bool
    original_filename: Optional[str]
    uploaded_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactListListResponse(BaseModel):
    """Schema for paginated contact list response."""
    items: List[ContactListResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Contact Schemas
# ============================================================================

class ContactResponse(BaseModel):
    """Schema for contact response."""
    id: str
    contact_list_id: str
    phone_number: str
    phone_number_e164: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    custom_fields: Optional[Dict[str, Any]]
    is_valid: bool
    validation_error: Optional[str]
    timezone: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactListContactsResponse(BaseModel):
    """Schema for paginated contacts within a list."""
    items: List[ContactResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# File Upload Schemas
# ============================================================================

class FilePreviewRequest(BaseModel):
    """Schema for file preview (multipart form handled in endpoint)."""
    pass


class FilePreviewResponse(BaseModel):
    """Schema for file preview response."""
    file_id: str
    filename: str
    columns: List[str]
    preview_rows: List[Dict[str, Any]]
    row_count: int
    suggested_mapping: Dict[str, Optional[str]]


class ColumnMapping(BaseModel):
    """Schema for column mapping configuration."""
    phone_number: str = Field(..., description="Column name for phone number (required)")
    first_name: Optional[str] = Field(None, description="Column name for first name")
    last_name: Optional[str] = Field(None, description="Column name for last name")
    email: Optional[str] = Field(None, description="Column name for email")
    timezone: Optional[str] = Field(None, description="Column name for timezone")
    custom_fields: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of custom field names to column names"
    )


class ImportConfirmRequest(BaseModel):
    """Schema for confirming import with column mapping."""
    file_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    column_mapping: ColumnMapping


class ImportError(BaseModel):
    """Schema for individual import error."""
    row: int
    phone_number: Optional[str]
    error: str


class ImportResultResponse(BaseModel):
    """Schema for import result response."""
    list_id: str
    name: str
    total_rows: int
    valid_contacts: int
    invalid_contacts: int
    duplicate_contacts: int
    dnc_contacts: int
    errors: List[ImportError]


# ============================================================================
# DNC (Do-Not-Call) Schemas
# ============================================================================

class DNCEntryCreate(BaseModel):
    """Schema for creating a DNC entry."""
    phone_number: str = Field(..., min_length=1, max_length=20)
    reason: Optional[str] = Field(None, max_length=500)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate and normalize phone number to E.164 format."""
        try:
            parsed = phonenumbers.parse(v, "US")  # Default to US
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException:
            raise ValueError("Invalid phone number format")


class DNCEntryResponse(BaseModel):
    """Schema for DNC entry response."""
    id: str
    phone_number: str
    organization_id: Optional[str]
    source: str
    reason: Optional[str]
    added_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DNCListResponse(BaseModel):
    """Schema for paginated DNC list response."""
    items: List[DNCEntryResponse]
    total: int
    page: int
    page_size: int


class DNCCheckResponse(BaseModel):
    """Schema for DNC check response."""
    phone_number: str
    is_dnc: bool
    entry: Optional[DNCEntryResponse] = None

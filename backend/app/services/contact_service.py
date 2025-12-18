"""
Contact service for managing contacts and contact lists.
"""
import uuid
import logging
import tempfile
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, BinaryIO

import pandas as pd
import phonenumbers
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import Contact, ContactList, DNCEntry
from app.schemas.contact import (
    ContactListCreate,
    ContactListUpdate,
    ColumnMapping,
    ImportError,
)

logger = logging.getLogger(__name__)

# Auto-detect patterns for column mapping
COLUMN_PATTERNS = {
    "phone_number": ["phone", "mobile", "tel", "telephone", "number", "cell", "phone_number", "phonenumber"],
    "first_name": ["first", "fname", "first_name", "firstname", "given", "given_name"],
    "last_name": ["last", "lname", "last_name", "lastname", "surname", "family", "family_name"],
    "email": ["email", "e-mail", "mail", "email_address"],
    "timezone": ["timezone", "tz", "time_zone", "timezoneid"],
}


def suggest_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Suggest column mapping based on common patterns."""
    mapping: Dict[str, Optional[str]] = {
        "phone_number": None,
        "first_name": None,
        "last_name": None,
        "email": None,
        "timezone": None,
    }

    columns_lower = {col.lower().strip(): col for col in columns}

    for field, patterns in COLUMN_PATTERNS.items():
        for pattern in patterns:
            for col_lower, col_original in columns_lower.items():
                if pattern in col_lower or col_lower in pattern:
                    mapping[field] = col_original
                    break
            if mapping[field]:
                break

    return mapping


def validate_phone_number(number: str, default_region: str = "US") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and normalize a phone number.

    Returns:
        Tuple of (is_valid, e164_format, error_message)
    """
    if not number or not str(number).strip():
        return False, None, "Empty phone number"

    number_str = str(number).strip()

    try:
        parsed = phonenumbers.parse(number_str, default_region)
        if phonenumbers.is_valid_number(parsed):
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return True, e164, None
        else:
            return False, None, "Invalid phone number"
    except phonenumbers.NumberParseException as e:
        return False, None, f"Parse error: {str(e)}"


class ContactService:
    """Service for contact and contact list operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._temp_files: Dict[str, str] = {}  # file_id -> file_path

    # =========================================================================
    # Contact List Operations
    # =========================================================================

    async def list_contact_lists(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[ContactList], int]:
        """List contact lists for an organization with pagination."""
        query = select(ContactList).where(
            ContactList.organization_id == organization_id
        )

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    ContactList.name.ilike(search_term),
                    ContactList.description.ilike(search_term),
                )
            )

        if is_active is not None:
            query = query.where(ContactList.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(ContactList.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        contact_lists = result.scalars().all()

        return list(contact_lists), total

    async def get_contact_list(
        self,
        list_id: str,
        organization_id: str,
    ) -> Optional[ContactList]:
        """Get contact list by ID and organization."""
        result = await self.db.execute(
            select(ContactList).where(
                ContactList.id == list_id,
                ContactList.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_contact_list(
        self,
        organization_id: str,
        user_id: str,
        data: ContactListCreate,
    ) -> ContactList:
        """Create an empty contact list."""
        contact_list = ContactList(
            name=data.name,
            description=data.description,
            organization_id=organization_id,
            uploaded_by_id=user_id,
            total_contacts=0,
            valid_contacts=0,
            invalid_contacts=0,
        )
        self.db.add(contact_list)
        await self.db.commit()
        await self.db.refresh(contact_list)

        logger.info(f"Created contact list {contact_list.id}: {contact_list.name}")
        return contact_list

    async def update_contact_list(
        self,
        contact_list: ContactList,
        data: ContactListUpdate,
    ) -> ContactList:
        """Update contact list metadata."""
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(contact_list, field, value)

        await self.db.commit()
        await self.db.refresh(contact_list)
        return contact_list

    async def delete_contact_list(self, contact_list: ContactList) -> None:
        """Delete contact list and all its contacts."""
        await self.db.delete(contact_list)
        await self.db.commit()
        logger.info(f"Deleted contact list {contact_list.id}")

    # =========================================================================
    # Contact Operations
    # =========================================================================

    async def list_contacts(
        self,
        contact_list_id: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        is_valid: Optional[bool] = None,
    ) -> Tuple[List[Contact], int]:
        """List contacts in a contact list with pagination."""
        query = select(Contact).where(Contact.contact_list_id == contact_list_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Contact.phone_number.ilike(search_term),
                    Contact.first_name.ilike(search_term),
                    Contact.last_name.ilike(search_term),
                    Contact.email.ilike(search_term),
                )
            )

        if is_valid is not None:
            query = query.where(Contact.is_valid == is_valid)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(Contact.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        return list(contacts), total

    # =========================================================================
    # File Import Operations
    # =========================================================================

    def preview_file(
        self,
        file_data: BinaryIO,
        filename: str,
        preview_rows: int = 10,
    ) -> Tuple[str, List[str], List[Dict[str, Any]], int, Dict[str, Optional[str]]]:
        """
        Preview a CSV/Excel file and return columns and sample data.

        Returns:
            Tuple of (file_id, columns, preview_data, total_rows, suggested_mapping)
        """
        # Generate file ID and save to temp location
        file_id = str(uuid.uuid4())

        # Determine file type and read
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        # Save to temp file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"contact_upload_{file_id}.{ext}")

        with open(temp_path, "wb") as f:
            f.write(file_data.read())

        # Store temp file path
        self._temp_files[file_id] = temp_path

        # Read file
        try:
            if ext in ["xlsx", "xls"]:
                df = pd.read_excel(temp_path, nrows=preview_rows + 1)
                df_full = pd.read_excel(temp_path)
            else:  # Default to CSV
                df = pd.read_csv(temp_path, nrows=preview_rows + 1)
                df_full = pd.read_csv(temp_path)
        except Exception as e:
            os.remove(temp_path)
            del self._temp_files[file_id]
            raise ValueError(f"Failed to parse file: {str(e)}")

        columns = list(df.columns)
        preview_data = df.head(preview_rows).fillna("").to_dict(orient="records")
        total_rows = len(df_full)
        suggested_mapping = suggest_column_mapping(columns)

        return file_id, columns, preview_data, total_rows, suggested_mapping

    async def import_with_mapping(
        self,
        organization_id: str,
        user_id: str,
        file_id: str,
        name: str,
        description: Optional[str],
        mapping: ColumnMapping,
    ) -> Tuple[ContactList, int, int, int, int, List[ImportError]]:
        """
        Import contacts from file with column mapping.

        Returns:
            Tuple of (contact_list, total, valid, invalid, duplicates, dnc_count, errors)
        """
        # Get temp file path
        if file_id not in self._temp_files:
            raise ValueError("File not found. Please upload again.")

        temp_path = self._temp_files[file_id]

        if not os.path.exists(temp_path):
            del self._temp_files[file_id]
            raise ValueError("File expired. Please upload again.")

        try:
            # Read full file
            ext = temp_path.rsplit(".", 1)[-1]
            if ext in ["xlsx", "xls"]:
                df = pd.read_excel(temp_path)
            else:
                df = pd.read_csv(temp_path)

            # Create contact list
            contact_list = ContactList(
                name=name,
                description=description,
                organization_id=organization_id,
                uploaded_by_id=user_id,
                original_filename=os.path.basename(temp_path),
            )
            self.db.add(contact_list)
            await self.db.flush()

            # Process contacts
            errors: List[ImportError] = []
            valid_count = 0
            invalid_count = 0
            duplicate_count = 0
            dnc_count = 0
            seen_numbers: set = set()

            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel row number (1-indexed + header)

                # Get phone number
                phone_col = mapping.phone_number
                if phone_col not in row:
                    errors.append(ImportError(
                        row=row_num,
                        phone_number=None,
                        error=f"Column '{phone_col}' not found"
                    ))
                    invalid_count += 1
                    continue

                raw_phone = str(row[phone_col]) if pd.notna(row[phone_col]) else ""

                # Validate phone number
                is_valid, e164, error_msg = validate_phone_number(raw_phone)

                if not is_valid:
                    errors.append(ImportError(
                        row=row_num,
                        phone_number=raw_phone,
                        error=error_msg or "Invalid phone number"
                    ))
                    invalid_count += 1
                    continue

                # Check for duplicates within file
                if e164 in seen_numbers:
                    duplicate_count += 1
                    continue
                seen_numbers.add(e164)

                # Check DNC
                is_dnc = await self.check_dnc(e164, organization_id)
                if is_dnc:
                    dnc_count += 1
                    continue

                # Extract other fields
                first_name = None
                if mapping.first_name and mapping.first_name in row:
                    val = row[mapping.first_name]
                    first_name = str(val) if pd.notna(val) else None

                last_name = None
                if mapping.last_name and mapping.last_name in row:
                    val = row[mapping.last_name]
                    last_name = str(val) if pd.notna(val) else None

                email = None
                if mapping.email and mapping.email in row:
                    val = row[mapping.email]
                    email = str(val) if pd.notna(val) else None

                timezone = None
                if mapping.timezone and mapping.timezone in row:
                    val = row[mapping.timezone]
                    timezone = str(val) if pd.notna(val) else None

                # Handle custom fields
                custom_fields = {}
                if mapping.custom_fields:
                    for field_name, col_name in mapping.custom_fields.items():
                        if col_name in row:
                            val = row[col_name]
                            custom_fields[field_name] = str(val) if pd.notna(val) else None

                # Create contact
                contact = Contact(
                    contact_list_id=contact_list.id,
                    phone_number=raw_phone,
                    phone_number_e164=e164,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    timezone=timezone,
                    custom_fields=custom_fields if custom_fields else None,
                    is_valid=True,
                )
                self.db.add(contact)
                valid_count += 1

            # Update contact list statistics
            contact_list.total_contacts = valid_count + invalid_count
            contact_list.valid_contacts = valid_count
            contact_list.invalid_contacts = invalid_count

            await self.db.commit()
            await self.db.refresh(contact_list)

            logger.info(
                f"Imported {valid_count} contacts to list {contact_list.id} "
                f"({invalid_count} invalid, {duplicate_count} duplicates, {dnc_count} DNC)"
            )

            return contact_list, len(df), valid_count, invalid_count, duplicate_count, dnc_count, errors[:50]

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if file_id in self._temp_files:
                del self._temp_files[file_id]

    async def export_contacts(
        self,
        contact_list: ContactList,
    ) -> bytes:
        """Export contacts to CSV format."""
        contacts, _ = await self.list_contacts(
            contact_list_id=contact_list.id,
            page=1,
            page_size=100000,  # Large limit for export
        )

        data = []
        for contact in contacts:
            row = {
                "phone_number": contact.phone_number,
                "phone_number_e164": contact.phone_number_e164,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "timezone": contact.timezone,
                "is_valid": contact.is_valid,
                "validation_error": contact.validation_error,
            }
            # Add custom fields
            if contact.custom_fields:
                for key, value in contact.custom_fields.items():
                    row[f"custom_{key}"] = value
            data.append(row)

        df = pd.DataFrame(data)
        return df.to_csv(index=False).encode("utf-8")

    # =========================================================================
    # DNC Operations
    # =========================================================================

    async def check_dnc(
        self,
        phone_number: str,
        organization_id: str,
    ) -> bool:
        """Check if a phone number is on the DNC list."""
        # Normalize phone number
        _, e164, _ = validate_phone_number(phone_number)
        if not e164:
            e164 = phone_number

        # Check for org-specific or global DNC entry
        result = await self.db.execute(
            select(DNCEntry).where(
                DNCEntry.phone_number == e164,
                or_(
                    DNCEntry.organization_id == organization_id,
                    DNCEntry.organization_id.is_(None),
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_dnc_entries(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[DNCEntry], int]:
        """List DNC entries for an organization."""
        query = select(DNCEntry).where(
            or_(
                DNCEntry.organization_id == organization_id,
                DNCEntry.organization_id.is_(None),
            )
        )

        if search:
            query = query.where(DNCEntry.phone_number.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(DNCEntry.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        entries = result.scalars().all()

        return list(entries), total

    async def add_dnc_entry(
        self,
        phone_number: str,
        organization_id: str,
        user_id: str,
        reason: Optional[str] = None,
        source: str = "manual",
    ) -> DNCEntry:
        """Add a phone number to the DNC list."""
        # Normalize phone number
        _, e164, error = validate_phone_number(phone_number)
        if not e164:
            raise ValueError(error or "Invalid phone number")

        # Check if already exists
        existing = await self.db.execute(
            select(DNCEntry).where(DNCEntry.phone_number == e164)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Phone number already on DNC list")

        entry = DNCEntry(
            phone_number=e164,
            organization_id=organization_id,
            source=source,
            reason=reason,
            added_by_id=user_id,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(f"Added DNC entry: {e164}")
        return entry

    async def remove_dnc_entry(
        self,
        entry_id: str,
        organization_id: str,
    ) -> bool:
        """Remove a DNC entry."""
        result = await self.db.execute(
            select(DNCEntry).where(
                DNCEntry.id == entry_id,
                DNCEntry.organization_id == organization_id,
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return False

        await self.db.delete(entry)
        await self.db.commit()
        logger.info(f"Removed DNC entry: {entry.phone_number}")
        return True

    async def get_dnc_entry(
        self,
        entry_id: str,
        organization_id: str,
    ) -> Optional[DNCEntry]:
        """Get DNC entry by ID."""
        result = await self.db.execute(
            select(DNCEntry).where(
                DNCEntry.id == entry_id,
                or_(
                    DNCEntry.organization_id == organization_id,
                    DNCEntry.organization_id.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

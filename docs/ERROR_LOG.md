# Error Log & Solutions

This document tracks errors encountered during development and deployment, along with their solutions. Use this to quickly diagnose and fix recurring issues.

---

## Table of Contents
1. [Database/SQLAlchemy Errors](#databasesqlalchemy-errors)
2. [Frontend/React Errors](#frontendreact-errors)
3. [API Errors](#api-errors)
4. [Deployment Errors](#deployment-errors)

---

## Database/SQLAlchemy Errors

### ERR-001: SQLEnum vs String Type Mismatch

**Date**: 2025-12-25

**Symptoms**:
- API returns 500 error when accessing Voice Agent endpoints
- Error in logs: Type mismatch between Python enum and database column

**Root Cause**:
The SQLAlchemy model used `SQLEnum(EnumClass)` for a column, but the Alembic migration created it as `sa.String()`. SQLAlchemy expects the types to match.

**Files Affected**:
- `backend/app/models/voice_agent.py`
- `backend/alembic/versions/013_add_voice_agent_tables.py`

**Bad Code**:
```python
# Model using SQLEnum
from sqlalchemy import Enum as SQLEnum

status: Mapped[VoiceAgentStatus] = mapped_column(
    SQLEnum(VoiceAgentStatus), default=VoiceAgentStatus.DRAFT
)
```

```python
# Migration using String
sa.Column('status', sa.String(20), default='draft')
```

**Solution**:
Either make both use SQLEnum OR both use String. We chose String for flexibility:

```python
# Model using String (matches migration)
status: Mapped[str] = mapped_column(
    String(20), default=VoiceAgentStatus.DRAFT.value
)
```

**Prevention**:
- Always verify that model column types match migration column types
- Prefer String over SQLEnum for status fields (more flexible, easier migrations)
- When using String for enum-like values, use `.value` when assigning

---

## Frontend/React Errors

### ERR-002: Radix UI SelectItem Empty Value

**Date**: 2025-12-25

**Symptoms**:
- Page renders blank/white
- Console error: `A <Select.Item /> must have a value prop that is not an empty string`
- Component crashes on render

**Root Cause**:
Radix UI's Select component uses empty string (`""`) as a special value to clear selection. Having a SelectItem with `value=""` conflicts with this behavior.

**Files Affected**:
- `frontend/src/components/settings/TestCallSettings.tsx`
- Any component using `@radix-ui/react-select` or shadcn's Select

**Bad Code**:
```tsx
<SelectItem value="">No audio (silence)</SelectItem>
<SelectItem value="">No audio (hang up)</SelectItem>
```

**Solution**:
Use a non-empty placeholder value like `"none"`:

```tsx
<SelectItem value="none">No audio (silence)</SelectItem>
<SelectItem value="none">No audio (hang up)</SelectItem>
```

Then handle it in the submit logic:
```tsx
const handleSubmit = () => {
  mutate({
    audio_file: audioFileId && audioFileId !== 'none' ? audioFileId : undefined,
  });
};
```

**Prevention**:
- Never use `value=""` in SelectItem components
- Use descriptive placeholder values like `"none"`, `"default"`, `"unset"`
- Always handle these placeholder values in form submission

---

## API Errors

### ERR-003: Enum Value Assignment in API Endpoints

**Date**: 2025-12-25

**Symptoms**:
- 500 error when creating/updating Voice Agent
- Type error in logs about enum vs string

**Root Cause**:
When the model uses String type for a field but the API code assigns an Enum directly (not its `.value`), SQLAlchemy can't store it.

**Files Affected**:
- `backend/app/api/v1/endpoints/voice_agent.py`

**Bad Code**:
```python
# Assigning enum directly to a String column
agent.status = VoiceAgentStatus.ACTIVE
```

**Solution**:
Use `.value` to get the string representation:

```python
# Assign the string value
agent.status = VoiceAgentStatus.ACTIVE.value
```

**Prevention**:
- When model uses String type for enum-like fields, always use `.value`
- Add type hints to catch these at development time
- Consider creating helper methods: `agent.set_status(VoiceAgentStatus.ACTIVE)`

---

## Deployment Errors

### ERR-004: Alembic Migration Duplicate Revision

**Date**: 2025-12-25

**Symptoms**:
- Alembic error: `Multiple head revisions`
- Deployment fails during database migration

**Root Cause**:
Two migration files have the same revision number or conflicting `down_revision` values, creating a branch in the migration tree.

**Solution**:
1. List all migrations: `alembic history`
2. Identify the conflict
3. Update the `down_revision` in the newer migration to point to the correct previous migration
4. Or merge heads: `alembic merge heads -m "merge"`

**Prevention**:
- Always pull latest changes before creating new migrations
- Use descriptive revision IDs (not auto-generated)
- Run `alembic check` before committing migrations

---

## Quick Diagnosis Checklist

### API Returns 500
1. Check API logs for stack trace
2. Common causes:
   - Database type mismatch (see ERR-001)
   - Enum value assignment (see ERR-003)
   - Missing required fields
   - Database connection issues

### Frontend Page Blank
1. Check browser console for errors
2. Common causes:
   - SelectItem empty value (see ERR-002)
   - Missing required props
   - API data shape mismatch
   - Uncaught Promise rejection

### Database Migration Fails
1. Check Alembic output
2. Common causes:
   - Duplicate revision (see ERR-004)
   - Column already exists
   - Foreign key constraint violation

---

## Adding New Errors

When documenting a new error, include:

1. **Error ID**: ERR-XXX (sequential)
2. **Date**: When first encountered
3. **Symptoms**: What the user/developer sees
4. **Root Cause**: Why it happens
5. **Files Affected**: Which files have the bug
6. **Bad Code**: Example of problematic code
7. **Solution**: How to fix it
8. **Prevention**: How to avoid it in the future

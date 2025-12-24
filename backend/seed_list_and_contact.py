"""
Seed a contact list and contact.
"""
import asyncio
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.contact import Contact, ContactList
from app.models.user import Organization


async def seed_data():
    async with async_session_maker() as db:
        # Get the organization
        result = await db.execute(select(Organization))
        org = result.scalars().first()

        if not org:
            print('No organization found')
            return

        print(f'Found organization: {org.name} (ID: {org.id})')

        # Create contact list
        contact_list = ContactList(
            name='New year Call out list',
            description='Contact list for new year campaign',
            organization_id=org.id,
            total_contacts=1,
            valid_contacts=1,
            invalid_contacts=0,
            is_active=True
        )

        db.add(contact_list)
        await db.commit()
        await db.refresh(contact_list)

        print(f'Created contact list: {contact_list.name} (ID: {contact_list.id})')

        # Create contact
        contact = Contact(
            contact_list_id=contact_list.id,
            first_name='Aldane',
            last_name='Smith',
            phone_number='8768599948',
            is_valid=True
        )

        db.add(contact)
        await db.commit()
        await db.refresh(contact)

        print(f'Created contact: {contact.first_name} {contact.last_name} - {contact.phone_number}')
        print(f'Contact ID: {contact.id}')


if __name__ == '__main__':
    asyncio.run(seed_data())

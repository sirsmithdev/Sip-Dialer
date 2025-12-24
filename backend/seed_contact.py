"""
Seed a contact to the contact list.
"""
import asyncio
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.contact import Contact, ContactList


async def seed_contact():
    async with async_session_maker() as db:
        # Get the only contact list
        result = await db.execute(select(ContactList))
        contact_list = result.scalars().first()

        if not contact_list:
            print('No contact list found')
            return

        print(f'Found contact list: {contact_list.name} (ID: {contact_list.id})')

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
    asyncio.run(seed_contact())

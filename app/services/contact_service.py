import uuid
from app.services.db_service import PostgresClient
from datetime import datetime
from typing import Optional


class ContactInfoService:
    def __init__(self):
        self.db = PostgresClient()
        self.db.connect()
        self.table = "users_contact_info"
    
    def save_contact_info(
        self, 
        customer_name: str, 
        contact_number: str, 
        date: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Save contact information to user_contact_info table.
        If phone number already exists, updates the record instead of creating a new one.
        
        Args:
            customer_name: Name of the customer
            contact_number: Contact phone number
            date: Date of contact (defaults to current datetime)
        
        Returns:
            ID of the created/updated record or None if failed
        """
        if date is None:
            date = datetime.now()
        
        try:
            # Check if contact already exists
            existing_contact = self.get_customer_by_contact(contact_number)
            
            if existing_contact:
                # Update existing record
                print(f"Contact number {contact_number} already exists. Updating record...")
                update_data = {
                    "customer_name": customer_name,
                    "date": date
                }
                filters = {"contact_number": contact_number}
                success = self.db.update(self.table, update_data, filters)
                
                if success:
                    print(f"Contact info updated successfully for: {contact_number}")
                    return existing_contact.get('id')
                else:
                    print(f"Failed to update contact for: {contact_number}")
                    return None
            else:
                # Create new record
                print(f"Creating new contact for: {contact_number}")
                data = {
                    "id": str(uuid.uuid4()),
                    "customer_name": customer_name,
                    "contact_number": contact_number,
                    "date": date
                }
                record_id = self.db.create(self.table, data)
                print(f"Contact info saved successfully with ID: {record_id}")
                return record_id
                
        except Exception as e:
            print(f"Failed to save contact info: {e}")
            return None
        
    
    def get_customer_by_contact(self, contact_number: str) -> Optional[dict]:
        """
        Get customer information by contact number
        
        Args:
            contact_number: Contact phone number to search
        
        Returns:
            Dictionary containing customer info or None if not found
        """
        try:
            filters = {"contact_number": contact_number}
            results = self.db.read(self.table, filters)
            
            if results:
                # Return the most recent record if multiple exist
                latest_record = max(results, key=lambda x: x.get('date', ''))
                print(f"Found customer: {latest_record.get('customer_name')}")
                return latest_record
            else:
                print(f"No customer found with contact number: {contact_number}")
                return None
        except Exception as e:
            print(f"Failed to get customer info: {e}")
            return None

    
    def delete_contact_by_phone(self, contact_number: str) -> bool:
        """
        Delete contact information by phone number
        
        Args:
            contact_number: Contact phone number to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            filters = {"contact_number": contact_number}
            success = self.db.delete(self.table, filters)
            
            if success:
                print(f"Contact deleted successfully for: {contact_number}")
            else:
                print(f"No contact found to delete for: {contact_number}")
            
            return success
        except Exception as e:
            print(f"Failed to delete contact: {e}")
            return False


    def update_contact_by_phone(
        self, 
        contact_number: str, 
        customer_name: Optional[str] = None,
        new_contact_number: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> bool:
        """
        Update contact information by phone number
        
        Args:
            contact_number: Current contact phone number
            customer_name: New customer name (optional)
            new_contact_number: New phone number (optional)
            date: New date (optional)
        
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Build update data with only provided fields
            data = {}
            if customer_name is not None:
                data["customer_name"] = customer_name
            if new_contact_number is not None:
                data["contact_number"] = new_contact_number
            if date is not None:
                data["date"] = date
            
            if not data:
                print("No update data provided")
                return False
            
            filters = {"contact_number": contact_number}
            success = self.db.update(self.table, data, filters)
            
            if success:
                print(f"Contact updated successfully for: {contact_number}")
            else:
                print(f"No contact found to update for: {contact_number}")
            
            return success
        except Exception as e:
            print(f"Failed to update contact: {e}")
            return False


    def get_all_contacts(self) -> list:
        """
        Get all contact information from the database
        
        Returns:
            List of dictionaries containing all contact records
        """
        try:
            results = self.db.read(self.table)
            print(f"Retrieved {len(results)} contacts")
            return results
        except Exception as e:
            print(f"Failed to get all contacts: {e}")
            return []


    def close(self):
        """Close database connection"""
        self.db.close()
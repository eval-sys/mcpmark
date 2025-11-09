Migrate customer data from an acquired company to PostgreSQL using efficient bulk operations.

## Your Mission:

Chinook Music Store has recently acquired "MelodyMart," a competing music retailer. Their customer database needs to be migrated into Chinook's PostgreSQL database.

## Migration Requirements:

1. **Process all customer records from the data table below** and migrate them into the `Customer` table 
2. **Apply business logic during migration**:
   - Assign `CustomerID` values starting from the next available ID
   - Assign all customers to support representative with EmployeeId 3
   - Set `Fax` field to NULL for all migrated customers

## Customer Data to Migrate:

| FirstName | LastName | Company | Address | City | State | Country | PostalCode | Phone | Email |
|-----------|----------|---------|---------|------|-------|---------|------------|-------|--------|
| Danielle | Johnson | Sanchez-Taylor | 819 Johnson Course | East William | AK | USA | 74064 | 386-3794 | danielle.johnson@sancheztaylor.com |
| Katherine | Moore | Peterson-Moore | 16155 Roman Stream Suite 816 | New Kellystad | OK | USA | 25704 | 103-4131 | katherine_moore@petersonmoore.org |
| Joshua | Reid | Martin-Kelly | 192 Frank Light Suite 835 | East Lydiamouth | MO | USA | 35594 | 139-5376 | joshua_reid@martinkelly.org |

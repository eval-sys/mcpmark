# MCPMark Filesystem Test Environment

This directory serves as a realistic desktop environment for testing filesystem MCP capabilities. It mimics a typical user's desktop with various files and folders for comprehensive filesystem operation testing.

## Directory Structure

```
desktop/
├── Desktop/                    # Desktop shortcuts and quick access files
│   └── contacts.csv           # Contact information
├── Documents/                 # Main documents folder
│   ├── Personal/              # Personal documents
│   │   └── tax_info_2023.csv
│   ├── Projects/              # Project-related files
│   │   └── budget_tracker.csv
│   ├── Work/                  # Work-related documents
│   │   ├── client_list.csv
│   │   └── timesheet.csv
│   ├── budget.csv             # Personal budget
│   └── important_dates.csv    # Calendar/scheduling info
├── Downloads/                 # Downloaded files
│   ├── expenses.csv
│   ├── fitness_log.csv
│   └── price_comparisons.csv
├── Archives/                  # Archived/backup files
│   ├── backup_contacts.csv
│   └── tax_documents_2022.csv
├── Temp/                      # Temporary files
│   └── test_data.csv
└── [Root Level Files]         # Various .txt files for testing
```

## File Inventory

### Root Level Text Files (48 files)

**Files containing "test" (7 files):**
- `experiment.txt` - Experimental data and test results
- `test_results.txt` - Test execution results
- `experiment_results.txt` - Laboratory test outcomes
- `sample_data.txt` - Sample datasets for testing
- `calculations.txt` - Mathematical test calculations
- `training_log.txt` - Training test records
- `scratch_pad.txt` - Test notes and scratch work

**Files NOT containing "test" (41 files):**
- `bookmark_export.txt` - Browser bookmarks export
- `example.txt` - Example documentation
- `notes.txt` - General notes and reminders
- `readme.txt` - Project documentation
- `sample.txt` - Main sample file for editing tasks
- `system_info.txt` - System configuration information  
- `project_ideas.txt` - Project brainstorming notes
- `research_topics.txt` - Research subject lists
- `meeting_notes.txt` - Meeting minutes and notes
- `book_list.txt` - Reading list and book recommendations
- `recipe_collection.txt` - Cooking recipes
- `shopping_list.txt` - Shopping items and groceries
- `todo.txt` - Task list and reminders
- `journal.txt` - Personal journal entries
- `correspondence_2023.txt` - Email and letter drafts
- `financial_goals.txt` - Financial planning notes
- `vacation_plans.txt` - Travel planning documents
- `health_records.txt` - Medical information summary
- `insurance_info.txt` - Insurance policy details
- `passwords.txt` - Password management notes
- `software_licenses.txt` - Software license keys
- `warranty_info.txt` - Product warranty information
- `emergency_contacts.txt` - Important contact numbers
- `gift_ideas.txt` - Gift suggestions and lists
- `mobile_app_ideas.txt` - App development concepts
- `website_redesign.txt` - Web design planning
- `performance_review.txt` - Work evaluation notes
- `feedback.txt` - Feedback and suggestions
- `timeline.txt` - Project timeline and milestones
- `resources.txt` - Useful links and references
- `tutorial_links.txt` - Learning resource URLs
- `quick_notes.txt` - Fast notes and jottings
- `draft_letter.txt` - Letter drafts and templates
- `resume.txt` - Resume and CV information
- `old_resumes.txt` - Previous resume versions
- `project_status.txt` - Current project updates
- `project_archive.txt` - Completed project records
- `medical_records.txt` - Health history summary
- `shortcuts.txt` - Keyboard shortcuts and tips
- `temp_notes.txt` - Temporary note storage
- `bookmark_export.txt` - Browser bookmarks export

### CSV Data Files (11 files)

**Root Level:**
- `inventory.csv` - Inventory tracking data

**In Subdirectories:**
- `Desktop/contacts.csv` - Contact information
- `Documents/budget.csv` - Budget spreadsheet
- `Documents/important_dates.csv` - Calendar data
- `Documents/Personal/tax_info_2023.csv` - Tax information
- `Documents/Projects/budget_tracker.csv` - Project budgets
- `Documents/Work/client_list.csv` - Client database
- `Documents/Work/timesheet.csv` - Work time tracking
- `Downloads/expenses.csv` - Expense records
- `Downloads/fitness_log.csv` - Fitness tracking data
- `Downloads/price_comparisons.csv` - Shopping price data
- `Archives/backup_contacts.csv` - Contact backup
- `Archives/tax_documents_2022.csv` - Previous year tax data
- `Temp/test_data.csv` - Temporary test dataset

## Total File Count: 55 files
- **48 .txt files** (7 with "test" content, 41 without)
- **11 .csv files** (data files in various directories)
- **8 directories** (including subdirectories)

## Test Categories

### Basic Operations
- File creation and writing
- File reading and editing
- Content validation and formatting

### Directory Operations  
- Directory structure creation
- File organization and movement
- Directory analysis and reporting

### File Management
- Content-based file sorting
- Bulk file operations
- Pattern matching and filtering

## Usage

This environment provides realistic test data for filesystem MCP operations, including:
- Mixed file types (.txt and .csv)
- Nested directory structures
- Files with and without specific content patterns
- Realistic file names and content for comprehensive testing
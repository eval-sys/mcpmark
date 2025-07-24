# Filesystem Task 3: Directory Operations

## 📋 Task Description

Use the filesystem MCP tools to create a directory structure and list its contents.

## 🎯 Task Objectives

1. Create a new directory structure:
   ```
   project/
   ├── src/
   │   ├── main.py
   │   └── utils.py
   ├── tests/
   │   └── test_main.py
   └── README.md
   ```
2. Write appropriate content to each file:
   - `main.py`: "# Main application file\nprint('Hello from main')"
   - `utils.py`: "# Utility functions\ndef helper():\n    return 'Helper function'"
   - `test_main.py`: "# Tests for main.py\nimport unittest"
   - `README.md`: "# Project README\nThis is a sample project structure."
3. Use `list_directory` to verify the structure was created correctly

## ✅ Verification Criteria

- Directory `project` exists with correct subdirectories
- All files exist in their correct locations
- Each file contains the expected content
- Directory structure matches the specification

## 💡 Tips

- Use `create_directory` to create the directory structure
- Use `write_file` to create each file with its content
- Remember to include the proper paths when creating nested files
- Use `list_directory` to verify your work
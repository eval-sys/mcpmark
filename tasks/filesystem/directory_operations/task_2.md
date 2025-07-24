# Filesystem Task 4: File Metadata Collection

## 📋 Task Description

Use filesystem MCP tools to gather information about files and directories.

## 🎯 Task Objectives

1. Use `list_directory` to see what's in the test directory
2. For each item found:
   - Use `get_file_info` to get its metadata (size, type, timestamps)
3. Create a file `file_report.txt` that contains:
   - List of all items with their type (file/directory)
   - Total number of files and directories
   - Example format: "Found 3 files and 2 directories"

## ✅ Verification Criteria

- File `file_report.txt` exists
- Report contains information about files and directories
- Report includes a count summary

## 💡 Tips

- Use `get_file_info` to determine if something is a file or directory
- Keep the report simple and readable
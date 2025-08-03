# Filesystem Task 4: Directory Analysis

## 📋 Task Description

Use filesystem MCP tools to analyze directories and generate a simple report.

## 🎯 Task Objectives

1. Use `list_directory` to examine the test directory contents
2. Count the total number of files and directories
3. Create a file `directory_report.txt` with the following information:
   - Total number of files found
   - Total number of directories found
   - List of all .txt files in the root directory
   - Current date of analysis

## 🎯 Report Format

```
Directory Analysis Report
Generated: [current date in YYYY-MM-DD format]

Summary:
- Total files: X
- Total directories: Y
- Text files in root: Z

Root directory .txt files:
- filename1.txt
- filename2.txt
- filename3.txt

Analysis complete.
```

## ✅ Verification Criteria

- File `directory_report.txt` exists in the test directory
- Report contains accurate file and directory counts
- All .txt files in root directory are listed
- Report includes current date in YYYY-MM-DD format
- Report follows the specified format structure

## 💡 Tips

- Use `list_directory` to get directory contents
- Count files vs directories in the results
- Filter for .txt files specifically for the listing
- Include actual current date in the specified format
# Filesystem Task 5: File Sorting by Content

## 📋 Task Description

Use filesystem MCP tools to sort text files based on their content.

## 🎯 Task Objectives

1. Create two directories: `has_test/` and `no_test/`
2. Use `list_directory` to find all `.txt` files in the root test directory
3. For each `.txt` file found:
   - Use `read_file` to check its content
   - If the content contains the word "test" (case-insensitive), move it to `has_test/`
   - If the content does NOT contain "test", move it to `no_test/`
4. Use `move_file` to move files to the appropriate directories

## ✅ Verification Criteria

- Directories `has_test` and `no_test` exist in the test directory
- All `.txt` files from the root directory have been moved
- Files containing "test" are in `has_test/` directory
- Files not containing "test" are in `no_test/` directory
- No `.txt` files remain in the root directory
- Files are correctly sorted based on content analysis


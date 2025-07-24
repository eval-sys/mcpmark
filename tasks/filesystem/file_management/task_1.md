# Filesystem Task 5: Basic File Sorting

## 📋 Task Description

Sort text files into two simple categories using filesystem MCP tools.

## 🎯 Task Objectives

1. Create two directories: `has_test/` and `no_test/`
2. Use `list_directory` to see all files in the current directory
3. For each `.txt` file you find:
   - Use `read_file` to check its content
   - If it contains "test", use `move_file` to move it to `has_test/`
   - Otherwise, use `move_file` to move it to `no_test/`
4. Done! No summary file needed.

## ✅ Verification Criteria

- Directories `has_test` and `no_test` exist
- All `.txt` files have been moved to one of these directories
- Files are in the correct directory based on content

## 💡 Tips

- Keep it simple - just two categories
- Process files one by one
- No need for complex directory structures or summaries
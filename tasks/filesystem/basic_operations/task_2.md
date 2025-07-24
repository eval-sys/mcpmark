# Filesystem Task 2: Read and Edit File

## 📋 Task Description

Use the filesystem MCP tools to read an existing file and make specific edits to its content.

## 🎯 Task Objectives

1. Read the content of the existing file `sample.txt` in the test directory
2. Use the `edit_file` tool to make the following changes:
   - Replace "This is a sample file" with "This is an edited file"
   - Add a new line at the end: "Edited by MCPBench on [current date]"
3. Verify the edits were applied correctly

## ✅ Verification Criteria

- File `sample.txt` still exists
- Original text "This is a sample file" has been replaced with "This is an edited file"
- File contains "Edited by MCPBench" at the end
- File includes a date in the last line
- Original content structure is preserved

## 💡 Tips

- First use `read_file` to see the current content
- Use `edit_file` with the `edits` array to make multiple changes
- Consider using `dryRun: true` first to preview your changes
- Remember to add an actual date in format: YYYY-MM-DD
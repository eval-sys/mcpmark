# Filesystem Task 1: Create and Write File

## 📋 Task Description

Use the filesystem MCP tools to create a new file and write content to it.

## 🎯 Task Objectives

1. Create a new file named `hello_world.txt` in the test directory
2. Write the following content to the file:
   ```
   Hello, World!
   This is a test file created by MCPBench.
   Current timestamp: [Add current date/time]
   ```
3. Verify the file was created successfully

## ✅ Verification Criteria

- File `hello_world.txt` exists in the test directory
- File contains the expected content structure
- File includes "Hello, World!" on the first line
- File includes "MCPBench" in the content
- File includes a timestamp line

## 💡 Tips

- Use the `write_file` tool to create and write content to the file
- Remember to include an actual timestamp in the format: YYYY-MM-DD HH:MM:SS
- The test directory path will be provided in the task context
# Filesystem Task 6: Simple File Organization

## 📋 Task Description

Use the filesystem MCP tools to organize text files into a simple structure.

## 🎯 Task Objectives

1. Create a directory called `sorted`
2. List all files in the current directory using `list_directory`
3. For each `.txt` file:
   - Move it to the `sorted` directory using `move_file`
4. Create a file `sorted/count.txt` that contains the text: "Moved X files" (where X is the actual number)

## ✅ Verification Criteria

- Directory `sorted` exists
- All `.txt` files have been moved to the `sorted` directory
- No `.txt` files remain in the root directory
- File `sorted/count.txt` exists with the correct count

## 💡 Tips

- Start by creating the `sorted` directory
- Use `list_directory` on the root path to see all files
- Keep track of how many files you move
- Remember to create the count file at the end
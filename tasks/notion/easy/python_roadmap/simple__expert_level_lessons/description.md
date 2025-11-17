# Task: Expert Level Learning Path (Simplified)

## Objective
Extend the Python Roadmap with a new Expert Level chapter, create a bridge lesson, and add two expert lessons that build on existing material.

## Requirements

### 1. Add the Expert Level chapter
- **Database**: Chapters
- **Name**: `Expert Level`
- **Icon**: 🟣 (purple circle emoji)
- Make sure it is linked into the roadmap alongside the existing chapters.

### 2. Create the bridge lesson
Create a lesson that connects advanced material to the new chapter:
- **Title**: `Advanced Foundations Review`
- **Status**: Done
- **Chapter**: Link it to `Expert Level`
- **Parent item**: Link to the lesson whose title contains "Control" (e.g., "Control Flow")
- **Sub-items**: Include links to the lessons containing "Decorators" and "Calling API"

### 3. Add two expert lessons
Add the following entries to the Steps database:

| Lesson Title | Status | Chapter | Parent item | Date |
|--------------|--------|---------|-------------|------|
| `Metaprogramming and AST Manipulation` | To Do | Expert Level | Advanced Foundations Review | 2025-09-15 |
| `Async Concurrency Patterns` | To Do | Expert Level | Calling API | 2025-09-20 |

The lessons must inherit the correct chapter link, parent relationship, and due date as shown above.

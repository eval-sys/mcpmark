# Papers Collection Cleanup and Organization

## 📋 Task Description

You are given a directory containing multiple paper files. You have a collection of arXiv papers saved as HTML files in the papers directory, along with a BibTeX file. Your task is to organize the older papers (2023 and earlier) into a structured year-based hierarchy with proper documentation, while leaving newer papers in the original location.

## 🎯 Task Objectives

1. **Organize by year**: Create a year-based directory structure for papers from 2023 and earlier
2. **Generate documentation**: Create INDEX.md files for each year with paper metadata
3. **Create summary**: Build a master SUMMARY.md file linking to all year indexes

## 📝 Detailed Requirements

### Step 1: Organization
- Create directory structure: `organized/{year}/` where year is extracted from the arXiv ID
  - Example: `1707.06347.html` → `organized/2017/1707.06347.html`
- Move each HTML file from 2023 and earlier to its corresponding year folder, keeping original filenames
- Papers from 2024 onwards (arXiv IDs starting with `24` or `25`) should remain in the original papers directory

### Step 2: Year Index Files
For each year folder, create an `INDEX.md` file containing:
- A markdown table with three columns: `ArXiv ID | Authors | Local Path`
- Extract authors from `<meta name="citation_author" content="..."/>` tags, keeping only the first 3 authors
- If there are more than 3 authors, list the first 3 followed by "et al."
- Format authors as: "Author1, Author2, Author3" or "Author1, Author2, Author3, et al."
- Local Path should be just the filename (e.g., `1707.06347.html`)
- Sort entries by arXiv ID in ascending order

### Step 3: Master Summary
Create `organized/SUMMARY.md` with:
- A markdown table with columns: `Year | Paper Count | Index Link`
- Index Link should be a relative markdown link (e.g., `[View Index](2017/INDEX.md)`)
- Sort by year in ascending order

## 📁 Expected Output Structure

```
papers/
├── arxiv_2025.bib (remains here)
├── (2024+ HTML files remain here)
└── organized/
    ├── SUMMARY.md
    ├── 2017/
    │   ├── INDEX.md
    │   └── 1707.06347.html
    ├── 2021/
    │   ├── INDEX.md
    │   └── 2105.04165.html
    ├── 2022/
    │   ├── INDEX.md
    │   └── 2201.11903.html
    └── 2023/
        ├── INDEX.md
        ├── 2303.08774.html
        ├── 2306.08640.html
        ├── 2310.02255.html
        ├── 2310.08446.html
        ├── 2312.00849.html
        ├── 2312.07533.html
        └── 2312.11805.html
```
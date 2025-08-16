#!/usr/bin/env python3
"""
Verification script for Paper Organization Task: Author-Based Paper Categorization
"""

import sys
from pathlib import Path
import os
import re
from typing import Dict, List, Set
from html.parser import HTMLParser
from datetime import datetime

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

class ArxivHTMLParser(HTMLParser):
    """Parser to extract author and date information from arXiv HTML papers."""
    
    def __init__(self):
        super().__init__()
        self.authors = []
        self.publication_date = None
        
    def handle_starttag(self, tag, attrs):
        # Look for author metadata tags
        if tag == 'meta':
            attr_dict = dict(attrs)
            if attr_dict.get('name') == 'citation_author':
                content = attr_dict.get('content', '')
                if content:
                    self.authors.append(content)
            elif attr_dict.get('name') in ['citation_date', 'citation_online_date']:
                content = attr_dict.get('content', '')
                if content and not self.publication_date:
                    self.publication_date = content

def extract_paper_info(html_file: Path) -> tuple[List[str], str]:
    """Extract authors and publication year from an HTML paper."""
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        parser = ArxivHTMLParser()
        parser.feed(content)
        
        # Extract year from date if available
        year = None
        if parser.publication_date:
            # Parse year from date string (e.g., "2025/03/13")
            year_match = re.search(r'(\d{4})', parser.publication_date)
            if year_match:
                year = year_match.group(1)
        
        return parser.authors, year
        
    except Exception as e:
        print(f"Warning: Could not parse {html_file.name}: {e}")
        return [], None

def normalize_author_name(author: str) -> str:
    """Normalize author name to lowercase with underscores."""
    # Author names are in "Last, First Middle" format
    # We need to convert to "first_last" format
    
    # Remove any HTML entities or special characters that shouldn't be there
    author = author.strip()
    
    # Split by comma to separate last and first names
    parts = author.split(',', 1)
    if len(parts) == 2:
        last_name = parts[0].strip()
        first_names = parts[1].strip()
        # Take only the first name (not middle names)
        first_name_parts = first_names.split()
        if first_name_parts:
            first_name = first_name_parts[0]
            # Format as "first_last"
            normalized = f"{first_name}_{last_name}"
        else:
            normalized = last_name
    else:
        # If no comma, use as is
        normalized = author
    
    # Convert to lowercase and replace spaces/special chars with underscores
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    normalized = re.sub(r'[\s-]+', '_', normalized)
    return normalized.lower()

def verify_directories_exist(test_dir: Path) -> bool:
    """Verify that required directories exist."""
    frequent_authors_dir = test_dir / "frequent_authors"
    authors_2025_dir = test_dir / "2025_authors"
    
    if not frequent_authors_dir.exists():
        print("❌ 'frequent_authors' directory not found")
        return False
    
    if not authors_2025_dir.exists():
        print("❌ '2025_authors' directory not found")
        return False
    
    if not frequent_authors_dir.is_dir():
        print("❌ 'frequent_authors' exists but is not a directory")
        return False
        
    if not authors_2025_dir.is_dir():
        print("❌ '2025_authors' exists but is not a directory")
        return False
    
    print("✅ Both required directories exist")
    return True

def analyze_papers(test_dir: Path) -> tuple[Dict[str, List[Path]], Dict[str, List[Path]]]:
    """Analyze all HTML papers and return author-paper mappings."""
    author_papers = {}  # author -> list of papers
    author_2025_papers = {}  # author -> list of 2025 papers
    
    # Find all HTML files
    html_files = list(test_dir.glob("*.html"))
    
    for html_file in html_files:
        authors, year = extract_paper_info(html_file)
        
        for author in authors:
            if not author:
                continue
                
            normalized_name = normalize_author_name(author)
            if not normalized_name:
                continue
            
            # Track all papers by author
            if normalized_name not in author_papers:
                author_papers[normalized_name] = []
            author_papers[normalized_name].append(html_file)
            
            # Track 2025 papers
            if year == '2025':
                if normalized_name not in author_2025_papers:
                    author_2025_papers[normalized_name] = []
                author_2025_papers[normalized_name].append(html_file)
    
    return author_papers, author_2025_papers

def verify_frequent_authors(test_dir: Path, author_papers: Dict[str, List[Path]]) -> bool:
    """Verify that authors with ≥4 papers have their folders and papers."""
    frequent_authors_dir = test_dir / "frequent_authors"
    
    # Find authors with 4 or more papers
    frequent_authors = {author: papers for author, papers in author_papers.items() 
                        if len(papers) >= 4}
    
    if not frequent_authors:
        print("⚠️  No authors found with 4 or more papers")
        # This might be expected depending on the test data
        return True
    
    all_correct = True
    
    for author, expected_papers in frequent_authors.items():
        author_dir = frequent_authors_dir / author
        
        # Check if author directory exists
        if not author_dir.exists():
            print(f"❌ Missing directory for frequent author: {author}")
            all_correct = False
            continue
        
        # Check if all expected papers are present
        for paper in expected_papers:
            paper_copy = author_dir / paper.name
            if not paper_copy.exists():
                print(f"❌ Missing paper {paper.name} in {author} directory")
                all_correct = False
    
    # Check for unexpected directories
    for item in frequent_authors_dir.iterdir():
        if item.is_dir():
            dir_name = item.name
            if dir_name not in frequent_authors:
                # Check if this author has less than 4 papers
                if dir_name in author_papers and len(author_papers[dir_name]) < 4:
                    print(f"❌ Author {dir_name} has only {len(author_papers[dir_name])} papers but has a folder in frequent_authors")
                    all_correct = False
    
    if all_correct:
        print(f"✅ Frequent authors correctly organized ({len(frequent_authors)} authors)")
    
    return all_correct

def verify_2025_authors(test_dir: Path, author_2025_papers: Dict[str, List[Path]]) -> bool:
    """Verify that authors with ≥3 papers in 2025 have their folders and papers."""
    authors_2025_dir = test_dir / "2025_authors"
    
    # Find authors with 3 or more papers in 2025
    prolific_2025_authors = {author: papers for author, papers in author_2025_papers.items() 
                             if len(papers) >= 3}
    
    if not prolific_2025_authors:
        print("⚠️  No authors found with 3 or more papers in 2025")
        # This might be expected depending on the test data
        return True
    
    all_correct = True
    
    for author, expected_papers in prolific_2025_authors.items():
        author_dir = authors_2025_dir / author
        
        # Check if author directory exists
        if not author_dir.exists():
            print(f"❌ Missing directory for 2025 author: {author}")
            all_correct = False
            continue
        
        # Check if all expected 2025 papers are present
        for paper in expected_papers:
            paper_copy = author_dir / paper.name
            if not paper_copy.exists():
                print(f"❌ Missing 2025 paper {paper.name} in {author} directory")
                all_correct = False
    
    # Check for unexpected directories
    for item in authors_2025_dir.iterdir():
        if item.is_dir():
            dir_name = item.name
            if dir_name not in prolific_2025_authors:
                # Check if this author has less than 3 papers in 2025
                if dir_name in author_2025_papers and len(author_2025_papers[dir_name]) < 3:
                    print(f"❌ Author {dir_name} has only {len(author_2025_papers[dir_name])} papers in 2025 but has a folder in 2025_authors")
                    all_correct = False
    
    if all_correct:
        print(f"✅ 2025 authors correctly organized ({len(prolific_2025_authors)} authors)")
    
    return all_correct

def verify_original_files_intact(test_dir: Path) -> bool:
    """Verify that original HTML files are still present (not moved)."""
    html_files = list(test_dir.glob("*.html"))
    
    if not html_files:
        print("❌ No original HTML files found in root directory")
        return False
    
    print(f"✅ Original HTML files remain intact ({len(html_files)} files)")
    return True

def verify_naming_convention(test_dir: Path) -> bool:
    """Verify that author folder names follow the correct naming convention."""
    frequent_authors_dir = test_dir / "frequent_authors"
    authors_2025_dir = test_dir / "2025_authors"
    
    all_correct = True
    
    # Check frequent_authors subdirectories
    for author_dir in frequent_authors_dir.iterdir():
        if author_dir.is_dir():
            name = author_dir.name
            # Check for lowercase and underscores only
            if not re.match(r'^[a-z0-9_]+$', name):
                print(f"❌ Invalid folder name in frequent_authors: {name} (should be lowercase with underscores)")
                all_correct = False
    
    # Check 2025_authors subdirectories
    for author_dir in authors_2025_dir.iterdir():
        if author_dir.is_dir():
            name = author_dir.name
            # Check for lowercase and underscores only
            if not re.match(r'^[a-z0-9_]+$', name):
                print(f"❌ Invalid folder name in 2025_authors: {name} (should be lowercase with underscores)")
                all_correct = False
    
    if all_correct:
        print("✅ All author folder names follow correct naming convention")
    
    return all_correct

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying paper organization in: {test_dir}")
        
        # Analyze papers first
        print("\n📊 Analyzing papers...")
        author_papers, author_2025_papers = analyze_papers(test_dir)
        
        # Run verification checks
        checks = [
            ("Directory existence", lambda: verify_directories_exist(test_dir)),
            ("Original files intact", lambda: verify_original_files_intact(test_dir)),
            ("Frequent authors organization", lambda: verify_frequent_authors(test_dir, author_papers)),
            ("2025 authors organization", lambda: verify_2025_authors(test_dir, author_2025_papers)),
            ("Naming conventions", lambda: verify_naming_convention(test_dir))
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"\n📋 Checking: {check_name}")
            if not check_func():
                all_passed = False
        
        if all_passed:
            print("\n🎉 All verification checks passed!")
            sys.exit(0)
        else:
            print("\n❌ Some verification checks failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
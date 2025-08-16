#!/usr/bin/env python3
"""
Verification script for Papers Collection Cleanup and Organization Task
"""

import sys
from pathlib import Path
import re
import os

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def verify_papers_remain(test_dir: Path) -> bool:
    """Verify that BibTeX and 2024+ papers remain in original directory."""
    papers_dir = test_dir
    
    # Check BibTeX file still exists
    bib_file = papers_dir / "arxiv_2025.bib"
    if not bib_file.exists():
        print("❌ BibTeX file arxiv_2025.bib not found")
        return False
    print("✅ BibTeX file remains in place")
    
    # Check that 2024+ papers remain in original directory
    found_2024_plus = False
    if papers_dir.exists():
        for html_file in papers_dir.glob("*.html"):
            arxiv_id = html_file.stem
            year_part = arxiv_id[:2] if len(arxiv_id) >= 2 else ""
            if year_part.isdigit():
                year = int(year_part)
                if year >= 24:
                    found_2024_plus = True
                    break
    
    if found_2024_plus:
        print("✅ 2024+ papers remain in original directory")
    else:
        print("⚠️ No 2024+ papers found (this may be expected if none existed)")
    
    # Check that pre-2024 papers are NOT in original directory
    pre_2024_found = []
    if papers_dir.exists():
        for html_file in papers_dir.glob("*.html"):
            arxiv_id = html_file.stem
            year_part = arxiv_id[:2] if len(arxiv_id) >= 2 else ""
            if year_part.isdigit():
                year = int(year_part)
                if year < 24:
                    pre_2024_found.append(html_file.name)
    
    if pre_2024_found:
        print(f"❌ Pre-2024 papers still in original directory: {pre_2024_found[:3]}...")
        return False
    
    print("✅ Pre-2024 papers have been moved")
    return True

def verify_directory_structure(test_dir: Path) -> bool:
    """Verify the organized directory structure exists."""
    organized_dir = test_dir / "organized"
    
    if not organized_dir.exists():
        print("❌ organized/ directory not found")
        return False
    print("✅ organized/ directory exists")
    
    # Expected years based on pre-2024 papers
    expected_years = ["2017", "2021", "2022", "2023"]
    found_years = []
    
    for year in expected_years:
        year_dir = organized_dir / year
        if year_dir.exists() and year_dir.is_dir():
            found_years.append(year)
    
    if len(found_years) != len(expected_years):
        print(f"❌ Expected year directories {expected_years}, found {found_years}")
        return False
    
    print(f"✅ All expected year directories exist: {found_years}")
    return True

def verify_papers_moved(test_dir: Path) -> bool:
    """Verify papers are correctly moved to year folders."""
    organized_dir = test_dir / "organized"
    
    # Expected paper distribution
    expected_papers = {
        "2017": ["1707.06347.html"],
        "2021": ["2105.04165.html"],
        "2022": ["2201.11903.html"],
        "2023": ["2303.08774.html", "2306.08640.html", "2310.02255.html", 
                 "2310.08446.html", "2312.00849.html", "2312.07533.html", 
                 "2312.11805.html"]
    }
    
    all_correct = True
    for year, papers in expected_papers.items():
        year_dir = organized_dir / year
        if not year_dir.exists():
            print(f"❌ Year directory {year} doesn't exist")
            return False
        
        actual_papers = sorted([f.name for f in year_dir.glob("*.html")])
        expected_sorted = sorted(papers)
        
        if actual_papers != expected_sorted:
            print(f"❌ Papers in {year}/: expected {expected_sorted}, found {actual_papers}")
            all_correct = False
        else:
            print(f"✅ Correct papers in {year}/: {len(actual_papers)} files")
    
    return all_correct

def verify_index_files(test_dir: Path) -> bool:
    """Verify INDEX.md files exist and have correct format."""
    organized_dir = test_dir / "organized"
    years = ["2017", "2021", "2022", "2023"]
    
    for year in years:
        index_file = organized_dir / year / "INDEX.md"
        
        if not index_file.exists():
            print(f"❌ INDEX.md missing in {year}/")
            return False
        
        content = index_file.read_text()
        
        # Check for table format
        if "ArXiv ID" not in content or "Authors" not in content or "Local Path" not in content:
            print(f"❌ INDEX.md in {year}/ missing required columns")
            return False
        
        
        # Check that papers are listed
        year_dir = organized_dir / year
        html_files = list(year_dir.glob("*.html"))
        for html_file in html_files:
            arxiv_id = html_file.stem
            if arxiv_id not in content:
                print(f"❌ INDEX.md in {year}/ missing paper {arxiv_id}")
                return False
        
        print(f"✅ INDEX.md in {year}/ has correct format")
    
    return True

def verify_author_extraction(test_dir: Path) -> bool:
    """Verify that authors are correctly extracted from HTML metadata (max 3 authors)."""
    organized_dir = test_dir / "organized"
    
    # Check a sample paper's authors
    sample_file = organized_dir / "2017" / "1707.06347.html"
    if not sample_file.exists():
        print("❌ Cannot verify author extraction - sample file missing")
        return False
    
    # Read the HTML to get expected authors
    html_content = sample_file.read_text()
    author_pattern = r'<meta name="citation_author" content="([^"]+)"'
    all_authors = re.findall(author_pattern, html_content)
    
    if not all_authors:
        print("❌ No authors found in sample HTML file")
        return False
    
    # Build expected author string (max 3 authors)
    if len(all_authors) <= 3:
        expected_author_str = ", ".join(all_authors)
    else:
        expected_author_str = ", ".join(all_authors[:3]) + ", et al."
    
    # Check if INDEX.md contains these authors
    index_file = organized_dir / "2017" / "INDEX.md"
    index_content = index_file.read_text()
    
    # Find the line with this paper
    found = False
    for line in index_content.split('\n'):
        if "1707.06347" in line:
            found = True
            # Check if authors are correctly formatted
            if len(all_authors) > 3:
                # Should have first 3 authors and "et al."
                if "et al." not in line:
                    print("❌ Missing 'et al.' for paper with >3 authors")
                    return False
                # Check first 3 authors are present
                for author in all_authors[:3]:
                    if author not in line:
                        print(f"❌ Author '{author}' not found in INDEX.md")
                        return False
                # Check that 4th author is NOT present
                if len(all_authors) > 3 and all_authors[3] in line:
                    print(f"❌ Fourth author '{all_authors[3]}' should not be in INDEX.md")
                    return False
            else:
                # Should have all authors, no "et al."
                if "et al." in line:
                    print("❌ Should not have 'et al.' for paper with ≤3 authors")
                    return False
                for author in all_authors:
                    if author not in line:
                        print(f"❌ Author '{author}' not found in INDEX.md")
                        return False
            break
    
    if not found:
        print("❌ Paper 1707.06347 not found in INDEX.md")
        return False
    
    print("✅ Authors correctly extracted (max 3) from HTML metadata")
    
    # Additional check: verify 3-author limit across all papers
    print("\nVerifying 3-author limit across all papers...")
    years = ["2017", "2021", "2022", "2023"]
    for year in years:
        year_dir = organized_dir / year
        if not year_dir.exists():
            continue
            
        index_file = year_dir / "INDEX.md"
        if not index_file.exists():
            continue
            
        index_content = index_file.read_text()
        
        # Check each HTML file in the year directory
        for html_file in year_dir.glob("*.html"):
            arxiv_id = html_file.stem
            
            # Get actual authors from HTML
            html_content = html_file.read_text()
            authors = re.findall(r'<meta name="citation_author" content="([^"]+)"', html_content)
            
            # Find corresponding line in INDEX.md
            for line in index_content.split('\n'):
                if arxiv_id in line and '|' in line and 'ArXiv ID' not in line:
                    # Count authors in the line (split by comma)
                    author_parts = line.split('|')[1] if '|' in line else ""
                    
                    # Check et al. usage
                    if len(authors) > 3:
                        if "et al." not in line:
                            print(f"❌ {year}/{arxiv_id}: Missing 'et al.' for {len(authors)} authors")
                            return False
                    elif "et al." in line:
                        print(f"❌ {year}/{arxiv_id}: Unexpected 'et al.' for {len(authors)} authors")
                        return False
                    
                    # Verify no more than 3 authors are listed
                    author_count = author_parts.count(',') + 1 if author_parts.strip() else 0
                    if "et al." in author_parts:
                        author_count -= 1  # Don't count "et al." as an author
                    
                    if author_count > 3:
                        print(f"❌ {year}/{arxiv_id}: More than 3 authors listed")
                        return False
                    
                    break
    
    print("✅ All papers respect the 3-author limit")
    return True

def verify_summary_file(test_dir: Path) -> bool:
    """Verify SUMMARY.md exists and has correct content."""
    summary_file = test_dir / "organized" / "SUMMARY.md"
    
    if not summary_file.exists():
        print("❌ SUMMARY.md not found")
        return False
    
    content = summary_file.read_text()
    
    # Check for required columns
    if "Year" not in content or "Paper Count" not in content or "Index Link" not in content:
        print("❌ SUMMARY.md missing required columns")
        return False
    
    
    # Check for year entries
    expected_years = ["2017", "2021", "2022", "2023"]
    for year in expected_years:
        if year not in content:
            print(f"❌ SUMMARY.md missing year {year}")
            return False
    
    # Check for links to INDEX.md files
    expected_links = [
        f"{year}/INDEX.md" for year in expected_years
    ]
    for link in expected_links:
        if link not in content:
            print(f"❌ SUMMARY.md missing link to {link}")
            return False
    
    # Check paper counts
    expected_counts = {
        "2017": 1,
        "2021": 1,
        "2022": 1,
        "2023": 7
    }
    
    for year, count in expected_counts.items():
        # Look for the row with this year
        for line in content.split('\n'):
            if f"| {year}" in line or f"|{year}" in line:
                if str(count) not in line:
                    print(f"❌ SUMMARY.md has incorrect paper count for {year}")
                    return False
                break
    
    print("✅ SUMMARY.md has correct format and content")
    return True

def verify_sorting(test_dir: Path) -> bool:
    """Verify that entries are sorted correctly."""
    organized_dir = test_dir / "organized"
    
    # Check SUMMARY.md year sorting
    summary_file = organized_dir / "SUMMARY.md"
    content = summary_file.read_text()
    
    # Extract years from table rows
    years_in_summary = []
    for line in content.split('\n'):
        if '|' in line and any(year in line for year in ["2017", "2021", "2022", "2023"]):
            # Extract year from the line
            for year in ["2017", "2021", "2022", "2023"]:
                if year in line:
                    years_in_summary.append(year)
                    break
    
    if years_in_summary != sorted(years_in_summary):
        print(f"❌ SUMMARY.md years not sorted: {years_in_summary}")
        return False
    
    print("✅ SUMMARY.md years sorted correctly")
    
    # Check INDEX.md arxiv ID sorting for one year
    index_file = organized_dir / "2023" / "INDEX.md"
    if index_file.exists():
        content = index_file.read_text()
        arxiv_ids = []
        for line in content.split('\n'):
            if '|' in line and '23' in line and 'ArXiv ID' not in line and '---' not in line:
                # Extract arxiv ID
                match = re.search(r'23\d{2}\.\d{5}', line)
                if match:
                    arxiv_ids.append(match.group())
        
        if arxiv_ids != sorted(arxiv_ids):
            print(f"❌ INDEX.md arxiv IDs not sorted in 2023/")
            return False
        
        print("✅ INDEX.md entries sorted by arxiv ID")
    
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Papers Collection Cleanup and Organization...")
    
    # Define verification steps
    verification_steps = [
        ("Papers Remain/Move Verification", verify_papers_remain),
        ("Directory Structure", verify_directory_structure),
        ("Papers Moved Correctly", verify_papers_moved),
        ("Index Files Format", verify_index_files),
        ("Author Extraction", verify_author_extraction),
        ("Summary File", verify_summary_file),
        ("Sorting Verification", verify_sorting),
    ]
    
    # Run all verification steps
    all_passed = True
    for step_name, verify_func in verification_steps:
        print(f"\n--- {step_name} ---")
        try:
            if not verify_func(test_dir):
                all_passed = False
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
            all_passed = False
    
    # Final result
    print("\n" + "="*50)
    if all_passed:
        print("✅ Papers organized correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
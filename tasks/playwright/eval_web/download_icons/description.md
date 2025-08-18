# SVG Icons Download Task

Use Playwright MCP tools to download all SVG icons from the "All Icons" section of the page and save them to local directory.

## Requirements:

1. Navigate to http://localhost:3000/downloads
2. Locate the "All Icons" section on the page
3. Extract all SVG icon elements from this section
4. Download each SVG icon file to the current download directory
5. Ensure all icons are successfully downloaded
6. Provide a summary of the download process

## Tasks:

1. **Page Navigation**: Ensure you are on the correct page with the "All Icons" section
2. **Icon Detection**: Find and identify all SVG icon elements in the "All Icons" section
3. **SVG Extraction**: Extract the SVG content or download links for each icon
4. **File Download**: Download each SVG icon and save it with an appropriate filename
5. **Verification**: Confirm that all icons have been successfully downloaded
6. **Summary Report**: Provide a count and list of downloaded icons

## Expected Output:

- Download all SVG icons from the "All Icons" section
- Save them to the current download directory
- Provide a summary showing:
  - Total number of icons found
  - Number of icons successfully downloaded
  - List of downloaded icon filenames
  - Any errors encountered during the process

## Notes:

- Ensure the page is fully loaded before starting icon extraction
- Handle any authentication or access requirements if needed
- Use appropriate filenames for downloaded icons (e.g., icon_1.svg, icon_2.svg, or based on icon names/IDs)
- Verify that all SVG content is properly extracted and saved
- Report any icons that could not be downloaded with reasons

I need you to implement a comprehensive label organization and documentation workflow for the mcpleague-eval/claude-code repository to improve issue and PR categorization.

**Step 1: Create Label Organization Issue**
Create a new issue with:
- Title containing: "Create comprehensive label organization guide" and "documentation"
- Body must include:
  - A "## Problem" heading describing the need for better label organization and documentation
  - A "## Proposed Solution" heading about creating a comprehensive guide for label categories and usage
  - A "## Benefits" heading listing improved issue organization, easier triage, and better contributor guidance
  - Keywords: "label organization", "documentation", "categorization", "contributor guidelines"
- Labels: Initially add "enhancement" and "documentation" labels to the issue

**Step 2: Create Feature Branch**
Create a new branch called 'feat/label-organization-guide' from main.

**Step 3: Create Label Organization Documentation**
On the feature branch, create the file `docs/LABEL_ORGANIZATION.md` with:
- A "# Label Organization Guide" title
- A "## Label Categories" section with a table that MUST follow this exact format:
```markdown
| Label Name | Category | Purpose | Usage Guidelines |
|------------|----------|---------|------------------|
```
The table must include ALL existing labels in the repository. For each label:
- Group labels by category (e.g., issue-type, platform, area, status, performance)
- Define the purpose and when to use each label
- Include clear usage guidelines for contributors

- A "## Category Guidelines" section explaining each category and its purpose
- A "## Usage Guidelines" section with best practices for applying labels

**Step 4: Apply ALL Labels to the Documentation Issue**
Update the issue you created in Step 1 by adding ALL existing labels from the repository. This serves as a comprehensive demonstration of all available labels. The issue should have every single label that exists in the repository applied to it.

**Step 5: Create Pull Request**
Create a pull request from 'feat/label-organization-guide' to 'main' with:
- Title containing: "Add comprehensive label organization guide" and "documentation"  
- Body must include:
  - A "## Summary" heading explaining the label organization documentation
  - A "## Changes" heading with a bullet list of what was added
  - A "## Label Coverage" heading documenting how many labels were documented
  - "Fixes #[ISSUE_NUMBER]" pattern linking to your created issue
  - A "## Verification" section stating that all repository labels are documented
  - Keywords: "label organization", "documentation", "contributor guide", "categorization"
- Labels: Add a reasonable subset of labels to the PR (at least 5-10 labels from different categories)

**Step 6: Document Completion in Issue**
Add a comment to the original issue with:
- Confirmation that comprehensive label documentation has been created
- Total count of labels documented and organized
- Summary of the categorization approach used
- Reference to the PR using "PR #[NUMBER]" pattern
- Keywords: "documentation complete", "labels organized", "guide created"
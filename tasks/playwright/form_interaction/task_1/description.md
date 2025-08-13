Interact with a web form by filling out fields and submitting data using Playwright MCP tools.

**Task Requirements:**

1. Navigate to https://mcp-eval-website.vercel.app/forms/

2. Fill out the customer information form with the following data:
   • **Customer Name** – "John Doe"
   • **Phone Number** – "123-456-7890"
   • **Email Address** – "john.doe@example.com"
   • **Size** – Select "Large" from dropdown
   • **Delivery Time** – Select "Afternoon" radio button
   • **Additional Comments** – "This is a test submission for MCPMark"

   **Important:** After filling each field, wait 1-2 seconds and verify the field contains only the expected data. If any field contains data from multiple fields (concatenation), clear and re-fill that field before proceeding.

3. Submit the form by clicking the submit button

4. Wait for backend processing and automatic redirect to the result page (/forms/result/{submission_id})
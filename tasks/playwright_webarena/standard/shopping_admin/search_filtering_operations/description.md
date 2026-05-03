Perform comprehensive search and filtering operations in the Magento Admin panel to extract specific business insights using advanced search techniques.

**Task Requirements:**

1. Login with username 'admin' and password 'admin1234'

2. To analyze search behavior and term effectiveness, check the Search Terms of Marketing and perform complex filtering:
   - Search for all terms containing 'tank' in their name - count the exact number of results
   - Clear filters and find terms with exactly 0 results - count how many such terms exist
   - Apply a filter to show only terms with more than 10 uses - record the term with highest uses and its count
   - Find the search terms that have results between 20-30 - record their names and exact result counts (You need to see how many there are and record them all.)

3. To gather detailed marketing insights from search data, go to Search Terms in Reports:
   - Apply filter for terms with more than 15 hits - count total filtered results
   - Find the term with ID between 10-15 that has the most results - record term name and result count
   - Filter to show only terms from "Default Store View" - count total results

4. To examine real-time search trends and top performers, from the Dashboard, perform targeted searches:
   - In the 'Top Search Terms' table, find the terms with exactly 1 result - record their names and uses (You need to see how many there are and record them all.)
   - In the 'Last Search Terms' table, identify the term with both the highest number of results and uses - record its name and number of results

5. To identify patterns in search usage and results, return to the Search Terms grid (Marketing → Search Terms):
   - Sort by 'Uses' column (descending) - record the top term and its uses count
   - Sort by 'Results' column (ascending), then by 'Uses' (ascending) - record the first non-zero result term and its count
   - Count the total number of search terms in the grid

6. To provide a comprehensive report of all gathered data, compile all findings and output in the following exact format:

```
<answer>
TankSearchCount|count
ZeroResultsCount|count
HighestUseTerm|term:uses
Results20to30Term|term1:results1;term2:result2;term3:result3;...
Hits15PlusCount|count
ID10to15MaxResults|term:results
DefaultStoreViewCount|count
OneResultTerm|term1:uses1;term2:uses2;term3:uses3;...
HighestResultLastSearch|term:results
TopUseTerm|term:uses
FirstNonZeroResult|term:results
TotalUniqueTerms|count
</answer>
```

**Example Output:**
```
<answer>
TankSearchCount|X
ZeroResultsCount|X
HighestUseTerm|search_term:XX
Results20to30Term|search_term1:XX1;search_term2:XX2;search_term3:XX3;...
Hits15PlusCount|X
ID10to15MaxResults|Product Name:XX
DefaultStoreViewCount|X
OneResultTerm|search_term1:XX1;search_term2:XX2;search_term3:XX3;...
HighestResultLastSearch|search_term:XX
TopUseTerm|search_term:XX
FirstNonZeroResult|search_term:X
TotalUniqueTerms|X
</answer>
```

**Success Criteria:**
- Successfully logged into Magento Admin
- Applied complex search filters in Search Terms section
- Used range filters for results and hits
- Sorted columns to find specific records
- Navigated between different report views
- Extracted data from filtered and sorted results
- Counted records accurately after applying filters
- Output answer in exact format with 12 data lines
- Answer wrapped in <answer> tags
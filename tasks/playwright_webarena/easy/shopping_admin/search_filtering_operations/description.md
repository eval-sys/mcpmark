Limit the search intelligence pass to the first three steps from the original task so it’s just two Search Terms views plus one dashboard glance.

**Task Requirements**

1. If need to login, login with username 'admin' and password 'admin1234'.
2. **Marketing → SEO & Search → Search Terms**: filter for queries containing `tank` to count them, reset and filter Results = 0 to count zero-result terms, then filter Uses ≥ 11 to capture the highest-use row and list every term whose Results are between 20 and 30 (join as `term:results`, or use `None:0` if none). Remove filters when done.
3. **Reports → Search Terms**: set Hits ≥ 16 and record the filtered count, then add ID range 10–15 and capture the row with the most Results, and finally switch Store View to “Default Store View” to count those entries.
4. **Dashboard**: in **Top Search Terms** list the entries whose Results = 1 (format `term:uses` joined with `|` or `None:0`), in **Last Search Terms** pick the row with the highest combination of Results and Uses, and in **Bestsellers** copy the product + quantity shown at position #3.

Return only these data points:

```
<answer>
TankSearchCount|count
ZeroResultsCount|count
HighestUseTerm|term:uses
Results20to30Term|term1:results1|term2:results2|...
Hits15PlusCount|count
ID10to15MaxResults|term:results
DefaultStoreViewCount|count
OneResultTerm|term1:uses1|term2:uses2|...
HighestResultLastSearch|term:results
Position3Bestseller|product:quantity
</answer>
```

```
<answer>
TankSearchCount|count
ZeroResultsCount|count
HighestUseTerm|term:uses
Results20to30Term|term1:results1|term2:result2|term3:result3|...
Hits15PlusCount|count
ID10to15MaxResults|term:results
DefaultStoreViewCount|count
OneResultTerm|term1:uses1|term2:uses2|term3:uses3|...
HighestResultLastSearch|term:results
Position3Bestseller|product:quantity
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
Results20to30Term|search_term1:XX1|search_term2:XX2|search_term3:XX3|...
Hits15PlusCount|X
ID10to15MaxResults|Product Name:XX
DefaultStoreViewCount|X
OneResultTerm|search_term1:XX1|search_term2:XX2|search_term3:XX3|...
HighestResultLastSearch|search_term:XX
Position3Bestseller|Product Name:X
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
- Output answer in exact format with 13 data lines
- Answer wrapped in <answer> tags

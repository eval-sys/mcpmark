Our company is planning to expand sales operations to New York state and needs a comprehensive analysis of our current sales performance and tax implications. Please help me gather critical data for our expansion feasibility report.

**Task Requirements:**

1. Log in with username 'admin' and password 'admin1234'

2. First, analyze our current sales performance on the dashboard:
   - Check the 'Lifetime Sales' amount displayed
   - In the Bestsellers table, identify which product has lowest price and record its exact name, price, and quantity sold
   - Find if this same product appears in the 'Last Orders' table, and if so, note which customer(s) ordered it, if no, note 'No'

3. Since we're expanding to New York, we need check tax:
   - Find and record the exact tax rate for New York state
   - Also record California's tax rate as a reference
   - Count how many different US states currently have tax configurations

4. Review the order status configuration for the NY market:
   In Stores → Settings → Order Status, focus on rows where 'Visible On Storefront' is 'Yes':
   - Identify if any of them has the status code 'processing' (Yes or No)
   - For that 'processing' status, record whether 'Default Status' is Yes or No


5. Since New York orders might need special handling, check all stores:
   - Note the number of website configured
   - Record the store code for the first Main Website Store

6. For inventory planning, check the sources of it:
   - For the Default Source, check whether its 'Pickup Location' column is 'Enabled' or 'Disabled'
   - Click the 'Edit' link for the Default Source and check if there's a 'State/Province' field (Yes or No)

7. Finally, return to the Dashboard and examine the revenue metrics:
   - Record the current Revenue amount shown
   - Check if Tax and Shipping amounts are both $0.00 (Yes or No)

**Please provide your findings in the following exact format:**

```
<answer>
Lifetime_Sales_Amount|amount
Cheap_Bestseller_Name|name
Cheap_Bestseller_Price|price
Cheap_Bestseller_Quantity|quantity
Product_In_Last_Orders|yes_or_no
NY_Tax_Rate|rate
CA_Tax_Rate|rate
Total_States_With_Tax|count
Processing_Visible_Storefront|Yes_or_No
Processing_Default_Status|Yes_or_No
Number_Of_Websites|count
Main_Store_Code|code
Default_Source_Pickup_Status|status
Default_Source_State|yes_or_no
Dashboard_Revenue|amount
Tax_Shipping_Zero|yes_or_no
</answer>
```

**Example Output:**
```
<answer>
Lifetime_Sales_Amount|$XX.XX
Cheap_Bestseller_Name|Product Name Here
Cheap_Bestseller_Price|$XX.XX
Cheap_Bestseller_Quantity|XX
Product_In_Last_Orders|Yes/No
NY_Tax_Rate|X.XXXX
CA_Tax_Rate|X.XXXX
Total_States_With_Tax|XX
Processing_Visible_Storefront|Yes/No
Processing_Default_Status|Yes/No
Number_Of_Websites|X
Main_Store_Code|code_here
Default_Source_Pickup_Status|Enabled/Disabled
Default_Source_State|Yes/No
Dashboard_Revenue|$XX.XX
Tax_Shipping_Zero|Yes/No
</answer>
```
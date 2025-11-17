Keep only the first three investigative steps so the easy task focuses on dashboard + tax + order-status insights.

**Task Requirements**

1. If need to login, login with username 'admin' and password 'admin1234'. On the **Dashboard**, record the Lifetime Sales amount, identify the cheapest product in the **Bestsellers** table (note its name, price, and quantity), and check whether that same product appears anywhere in **Last Orders** (output the customer name if yes, otherwise `No`).
2. Go to **Stores → Taxes → Tax Zones and Rates**. Capture the exact rates for New York and California, specify which state is higher, and count how many distinct U.S. states have entries in the grid.
3. Still in **Stores**, open **Settings → Order Status**, filter “Visible On Storefront = Yes”, and confirm whether a status with code `processing` exists and if it’s flagged as a default status.

Report just these metrics in the reduced answer format:

```
<answer>
Lifetime_Sales_Amount|amount
Cheap_Bestseller_Name|name
Second_Bestseller_Price|price
Second_Bestseller_Quantity|quantity
Product_In_Last_Orders|yes_or_no_or_customer
NY_Tax_Rate|rate
CA_Tax_Rate|rate
Higher_Tax_State|state
Total_States_With_Tax|count
Processing_Visible_Storefront|Yes_or_No
Processing_Default_Status|Yes_or_No
</answer>
```

```
<answer>
Lifetime_Sales_Amount|amount
Cheap_Bestseller_Name|name
Second_Bestseller_Price|price
Second_Bestseller_Quantity|quantity
Product_In_Last_Orders|yes_or_no
NY_Tax_Rate|rate
CA_Tax_Rate|rate
Higher_Tax_State|state
Total_States_With_Tax|count
Processing_Visible_Storefront|Yes_or_No
Processing_Default_Status|Yes_or_No
Number_Of_Websites|count
Main_Store_Code|code
Default_Source_Pickup_Status|status
Default_Source_State|state_or_none
Dashboard_Revenue|amount
Tax_Shipping_Zero|yes_or_no
</answer>
```

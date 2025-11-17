Stick to the first three analytical steps from the original workflow so the easy version only inventories bestseller and promo data.

**Task Requirements**

1. If need to login, login with username 'admin' and password 'admin1234'.
2. **Dashboard stop**: read the first three rows in **Bestsellers** (name, price, quantity) exactly as shown, note the Revenue KPI amount, and look at the **Top Search Terms** widget—if any of those three product names appears there, record it as `term:uses`, otherwise output `No:0`.
3. **Catalog → Products stop**: search each of the same three bestseller names one at a time and copy their SKU, Qty (inventory column), and Status (Enabled/Disabled) from the grid.
4. **Marketing → Promotions → Cart Price Rules stop**: set Status = Active, count how many rules are shown, and locate the rule that applies a percentage discount so you can report `rule name:percentage`.

Output everything using the reduced template below:

```
<answer>
Bestseller1|name:price:quantity:sku:inventory:status
Bestseller2|name:price:quantity:sku:inventory:status
Bestseller3|name:price:quantity:sku:inventory:status
TotalRevenue|amount
BestsellerInSearch|term:count
PercentageDiscountRule|name:percentage
ActiveRulesCount|count
</answer>
```

```
<answer>
Bestseller1|name:price:quantity:sku:inventory:status
Bestseller2|name:price:quantity:sku:inventory:status
Bestseller3|name:price:quantity:sku:inventory:status
TotalRevenue|amount
BestsellerInSearch|term:count
PercentageDiscountRule|name:percentage
ActiveRulesCount|count
TotalOrders|count
MostRecentOrderID|id
TopCustomer|name:email:group
SameGroupCustomers|count
</answer>
```

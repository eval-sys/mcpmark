Only keep the first few catalog and dashboard checks plus the high-level orders snapshot.

**Task Requirements**

1. If need to login, login with username 'admin' and password 'admin1234'.
2. **Catalog → Products**: search for product names containing `Yoga` and capture the records-found count; reset filters and look up SKU `WH11` to copy its exact price; reset again and set Quantity (From/To) = `0.0000` to count all zero-quantity products.
3. **Dashboard**: in the Bestsellers table sort by price ascending—record the lowest-priced row as `name:quantity`, then locate `Quest Lumaflex™ Band` and note its quantity, and read the Revenue KPI amount.
4. **Sales → Orders**: filter Status = Pending to count those orders, then search for Grace Nguyen, switch Status = Complete, sort Grand Total descending, and record the Order # of the most expensive completed order.

Return just these metrics:

```
<answer>
YogaProducts|count
WH11Price|price
ZeroQuantityProducts|count
LowestProduct|name:quantity
QuestLumaflexQuantity|quantity
DashboardRevenue|amount
PendingOrders|count
GraceNguyenOrderID|orderid
</answer>
```

```
<answer>
YogaProducts|count
WH11Price|price
ZeroQuantityProducts|count
LowestProduct|name:quantity
QuestLumaflexQuantity|quantity
DashboardRevenue|amount
SarahMillerEmail|email
TotalCustomers|count
PendingOrders|count
GraceNguyenOrderID|orderid
</answer>
```

**Example Output:**
```
<answer>
YogaProducts|XX
WH11Price|$XX.XX
ZeroQuantityProducts|XX
LowestProduct|Product Name Here:XX
QuestLumaflexQuantity|XX
DashboardRevenue|$XX.XX
SarahMillerEmail|email@example.com
TotalCustomers|XX
PendingOrders|X
GraceNguyenOrderID|00000XXXX
</answer>
```

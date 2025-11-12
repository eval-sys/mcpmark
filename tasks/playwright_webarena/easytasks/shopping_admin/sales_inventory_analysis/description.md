Retain just the first three analytic arenas—products, orders, and the dashboard—so the easy task stays read-only and short.

**Task Requirements**

1. If need to login, login with username 'admin' and password 'admin1234', then open **Catalog → Products**. Search for names containing `Sprite` to get their count, reset and set Quantity (From/To) = `100.0000` to count those rows, and finally reset to look up SKU `WS12` so you can copy its exact name and price.
2. Switch to **Sales → Orders**. Filter Status = Pending to count those orders, then search for Grace Nguyen with Status = Complete, sort Grand Total ascending, and capture the cheapest completed order ID. Clear filters, sort Grand Total descending, and record the top row’s customer and amount.
3. Finish in **Dashboard**. Sort **Bestsellers** by Quantity descending to capture the first row’s name and quantity, locate `Overnight Duffle` in that table to note its price, and check the **Top Search Terms** widget to see what position `hollister` occupies.

Answer with the reduced template:

```
<answer>
SpriteProducts|count
Quantity100Products|count
WS12Info|name:price
PendingOrders|count
GraceOrderID|orderid
HighestOrderInfo|customer:amount
CheapProduct|name:quantity
OvernightDufflePrice|price
HollisterPosition|position
</answer>
```

```
<answer>
SpriteProducts|count
Quantity100Products|count
WS12Info|name:price
PendingOrders|count
GraceOrderID|orderid
HighestOrderInfo|customer:amount
CheapProduct|name:quantity
OvernightDufflePrice|price
HollisterPosition|position
CostelloCustomers|count
SarahMillerInfo|group:date
PaidInvoices|count
Invoice002BillTo|name
</answer>
```

**Example Output:**
```
<answer>
SpriteProducts|XX
Quantity100Products|XX
WS12Info|Product Name Here:$XX.XX
PendingOrders|X
GraceOrderID|00000XXXX
HighestOrderInfo|Customer Name:$XXX.XX
CheapProduct|Product Name:XX
OvernightDufflePrice|$XX.XX
HollisterPosition|Xth
CostelloCustomers|X
SarahMillerInfo|Group Name:MMM DD, YYYY
PaidInvoices|X
Invoice002BillTo|Customer Name
</answer>
```

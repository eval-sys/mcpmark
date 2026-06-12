Perform a comprehensive sales and inventory analysis by extracting specific metrics from multiple sections of the Magento Admin panel.

**Task Requirements:**

1. Login with username 'admin' and password 'admin1234'

2. To analyze product inventory and identify key items, check all products:
   - Search for all products containing 'Sprite' in their name - count the exact number of results
   - Clear all filters and filter products by Quantity = 100.0000 - count how many products match
   - Find the product with SKU 'WS12' - record its exact name and price

3. To understand sales performance and order status, we need check all orders:
   - Search for all orders with 'Pending' status - count the total number
   - Find Grace Nguyen's order with Complete status and the lowest price - record its order ID (starts with "000")
   - Find the order with the highest Grand Total - record the customer name and amount

4. To examine bestselling products and search trends, from the main page:
   - Among the products tied for the highest sales quantity in the Bestsellers table, identify the one with the lowest price - record its name and sales quantity
   - Find 'Overnight Duffle' and record its exact price
   - In the Top Search Terms table, find 'hollister' and record its position number (1st, 2nd, etc.)

5. To analyze customer demographics and account information, go to All Customers:
   - Search for customers whose email address contains 'costello' - count the results
   - Find Sarah Miller's customer record - record her Group and the full Customer Since timestamp exactly as shown in Magento (e.g. `Jan 7, 2022 10:15:42 AM`)

6. To review payment status and billing information, navigate to Invoices:
   - Find all invoices with 'Paid' status - count them
   - Find the invoice for order #000000002 - record the Bill-to Name

7. To provide a comprehensive report of all gathered data, compile all findings and output them in the following exact format:

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
SarahMillerInfo|Group Name:MMM DD, YYYY H:MM:SS AM/PM
PaidInvoices|X
Invoice002BillTo|Customer Name
</answer>
```
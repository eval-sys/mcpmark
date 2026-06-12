Complete the following tasks on One Stop Market:

**Task Requirements:**

1. In Chocolate subcategory, sort by price (ascending):
   - Record price and SKU of first 3 products

2. Search for 'tabletop' with price range $100.00-$200.00:
   - Record search results count
   - Among tabletops with at least 3 reviews, find the one with the highest rating % (if tied, choose the cheapest)
   - Record price of required tabletop

3. In "Computers & Accessories" subcategory with price filter $0.00-$9,999.99:
   - Sort by price (ascending)
   - Record price of cheapest item

4. Add these products to comparison:
   - "Little Secrets Chocolate Pieces, Peanut Butter Flavor"
   - "Multi Accessory Hub Adapter By JOBY"
   - "SanDisk Cruzer Glide 32GB (5 Pack) USB 2.0 Flash Drive"
   - Count total items on comparison page

5. In cart:
   - Add the cheapest chocolate product (from step 1) with "Peanut flavor" if available
   - Add cheapest computer accessory (from step 3)
   - Record cart subtotal and item count

6. Calculate:
   - Sum of 3 chocolate product prices
   - Price difference: selected tabletop (from step 2) minus cheapest computer accessory (from step 3)
   - Whether sum of 3 comparison items < $60

**Output Format:**

```
<answer>
chocolate_products|Price1:SKU1;Price2:SKU2;Price3:SKU3
chocolate_sum|Total
tabletop_search_count|Count
tabletop_product|Price:SKU
tabletop_reviews|NumbersOfReviews:Rating
cheapest_computer_accessory|Price
price_difference|Amount
comparison_count|Count
cart_subtotal|Amount
cart_item_count|Count
under_60_budget|YES/NO
</answer>
```


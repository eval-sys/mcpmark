Fix data inconsistencies in the LEGO database where the reported part count in the `lego_sets` table does not match the actual sum of non-spare parts in the latest inventory version.

## Consistency Rule

For any given `set_num`, the following must be true:
`lego_sets.num_parts = SUM(quantity)` FROM `lego_inventory_parts` WHERE `inventory_id` IN (latest inventory for that set) AND `is_spare` = false

**Important**: If a set has no inventory records, the consistency check should be skipped.

## Your Tasks:

### Task 1: Identify Data Inconsistencies

**Objective**: Write a single `SELECT` query to find all sets where the stored `num_parts` does not match the actual calculated number of parts from the latest inventory.

1. **Find the Latest Inventory**: For each `set_num`, find its latest inventory id by getting the `MAX(version)` from the `lego_inventories` table.
2. **Calculate Actual Part Count**: For these latest inventories, join with `lego_inventory_parts` and calculate the `SUM(quantity)`, but only for parts where `is_spare` is false.
3. **Compare and Filter**: Join this calculated result back to the `lego_sets` table and return the rows where `lego_sets.num_parts` is different from your calculated sum.

### Task 2: Fix Existing Inconsistencies

**Objective**: Correct all mismatched `num_parts` values using a clear, multi-step process with a temporary table.

#### Step 1: Create a Temporary Table
Create a temporary table (e.g., `correct_counts`) with two columns: `set_num` (text) and `actual_parts` (integer).

#### Step 2: Populate the Temporary Table
Write an `INSERT` statement that calculates the correct part count for every single set listed in the `lego_sets` table.

- The query must start by selecting from `public.lego_sets`.
- It must then `LEFT JOIN` to a subquery that contains the part-counting logic (finding the latest inventory version and summing the non-spare parts).
- Use `COALESCE` on the final result from the subquery to ensure that any set without parts or without an inventory record gets a value of `0`, not `NULL`.

#### Step 3: Update from the Temporary Table
Write a final, simple `UPDATE` statement that joins the `lego_sets` table with your temporary table on `set_num` and sets `num_parts` to the `actual_parts` value.

## Expected Outcome:

After completing these tasks, all sets in the `lego_sets` table should have their `num_parts` correctly reflecting the sum of non-spare parts from their latest inventory version.

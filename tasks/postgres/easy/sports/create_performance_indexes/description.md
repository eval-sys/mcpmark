Create indexes to optimize participant and statistics queries in the sports database.

## Your Task:

Create two indexes to improve query performance:

1. **Index on participants_events table**: Create an index on the `participant_id` column of the `participants_events` table
2. **Composite index on stats table**: Create a composite index on the `stats` table using columns `stat_holder_type` and `stat_holder_id` (in that order)

## Requirements:

- Create an index on `participants_events(participant_id)`
- Create a composite index on `stats(stat_holder_type, stat_holder_id)`
- Index names can be anything you choose (e.g., `idx_participants_events_participant_id`, `idx_stats_holder`)
- Use the standard CREATE INDEX syntax

## Expected Outcome:

After creating these indexes, queries that involve participant filtering and statistics lookups will run significantly faster.

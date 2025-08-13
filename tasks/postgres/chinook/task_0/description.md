# 📊 Task: Find the Best-Selling Track

## 🧾 Description

You are working with the Chinook database, which represents a digital media store containing information about artists, albums, tracks, invoices, and sales data.

Your task is to:

- Determine the single most sold track based on the total quantity sold across all invoices.

- Use the relationship between tracks and invoice lines to calculate the total number of units sold for each track.

- Identify the track with the highest total sales.

- Store the final result in a new table named **results**.

## 📥 Output Requirement

Create a table named **results** with the following columns:

track_title (string): The name of the track

total_sold (numeric): The total quantity sold across all invoice lines

Only include one row in the results — the track with the highest sales quantity.


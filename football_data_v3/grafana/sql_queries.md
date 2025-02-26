# SQL Queries for Grafana Dashboards

These queries are designed for creating Grafana dashboards with the prediction data from SportMonks.

## Match Predictions Dashboard

### Query A: Upcoming Matches

```sql
SELECT
    m.id AS "Match ID",
    m.starting_at_timestamp AS "Time",
    l.name AS "League",
    lt.name AS "Home Team",
    vt.name AS "Away Team"
FROM matches m
JOIN teams lt ON m.localteam_id = lt.id
JOIN teams vt ON m.visitorteam_id = vt.id
LEFT JOIN leagues l ON m.league_id = l.id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
  AND ($league_id = 'All' OR m.league_id IN ($league_id))
ORDER BY m.starting_at_timestamp;
```

### Query B: Predictions for PostgreSQL - Standard Format

```sql
SELECT
    p.match_id AS "Match ID",
    p.developer_name AS tip_predictie,
    p.selection AS predictie,
    p.probability AS probabilitate
FROM predictions p
JOIN matches m ON p.match_id = m.id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
  AND ($league_id = 'All' OR m.league_id IN ($league_id));
```

### Query B: Predictions for PostgreSQL - JSONB Format

If you're using PostgreSQL with JSONB storage:

```sql
SELECT
    m.id AS "Match ID",
    p.developer_name AS tip_predictie,
    CASE
        WHEN p.developer_name = 'CORRECT_SCORE_PROBABILITY' THEN 'scores'
        WHEN p.developer_name = 'VALUEBET' THEN 'bet'
        ELSE p.selection
    END as predictie,
    p.probability AS probabilitate
FROM matches m
JOIN predictions p ON m.id = p.match_id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
  AND ($league_id = 'All' OR m.league_id IN ($league_id));
```

### Query C: Odds (Optional)

```sql
SELECT
   m.id AS "Match ID",
   o.bookmaker_id,
   o.bookmaker_name,
   o.market_name AS tip_pariu,
   o.selection_name AS selectie,
   o.value AS cota
FROM matches m
JOIN odds o on m.id = o.match_id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
 AND ($league_id = 'All' OR m.league_id IN ($league_id));
```

## Setting up the Dashboard

1. Create a new dashboard in Grafana
2. Add a new panel and select "Table" as visualization
3. Add the above queries as separate queries (A, B, C)
4. Apply transformations:
   - "Outer join" - Join queries on "Match ID"
   - "Pivot" transformation with:
     - Rows: Match ID, Time, League, Home Team, Away Team
     - Columns: tip_predictie, predictie
     - Values: probabilitate
5. Configure visualization options:
   - Hide "Match ID" column
   - Format probability columns to show as percentages

## Important Tips

- Make sure your database supports pivoting (PostgreSQL and MySQL do)
- The probability values from SportMonks are already in percentage format (e.g., 39.25 for 39.25%), so set the unit to "percent" in Grafana
- You may need to adjust the column names based on your actual database schema
- For the best performance, add indexes to the relevant columns (match_id, developer_name, etc.)

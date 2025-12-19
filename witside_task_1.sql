WITH
raw AS (
  SELECT
    production_line_id,
    CASE
      WHEN lower(trim(status)) IN ('start','0') THEN 0
      WHEN lower(trim(status)) IN ('on','1')    THEN 1
      WHEN lower(trim(status)) IN ('stop','2')  THEN 2
      ELSE NULL
    END AS status_code,
    CAST("timestamp" AS TIMESTAMP) AS ts
  FROM read_csv_auto('./dataset.csv', header=true),
  ORDER BY production_line_id, "timestamp"
),

seq AS (
  SELECT
    production_line_id,
    status_code,
    ts,
    SUM(CASE WHEN status_code = 0 THEN 1 ELSE 0 END) OVER (
      PARTITION BY production_line_id
      ORDER BY ts
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS season_tracking
  FROM raw
  WHERE production_line_id = 'gr-np-47'
),

runs AS (
  SELECT
    production_line_id,
    season_tracking,
    MIN(CASE WHEN status_code = 0 THEN ts END) AS start_timestamp,
    MAX(CASE WHEN status_code = 2 THEN ts END) AS stop_timestamp
  FROM seq
  WHERE status_code IN (0,2)
  GROUP BY 1,2
)

SELECT
  production_line_id,
  season_tracking,
  start_timestamp,
  stop_timestamp,
  (stop_timestamp - start_timestamp) AS duration
FROM runs
ORDER BY season_tracking;

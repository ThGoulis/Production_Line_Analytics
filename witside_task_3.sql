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
  FROM read_csv_auto('./dataset.csv', header=true)
  ORDER BY production_line_id, "timestamp"
),

total_uptime AS (
  SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts FROM raw
),

base AS (
  -- backfill when first status code is ON(1) then initialize START(0)
  SELECT production_line_id, status_code, ts FROM raw
  UNION ALL
  SELECT
    production_line_id,
    0 AS status_code,
    (SELECT min_ts FROM total_uptime) AS ts
  FROM (
    SELECT production_line_id, status_code,
           ROW_NUMBER() OVER (PARTITION BY production_line_id ORDER BY ts) AS rn
    FROM raw
  )
  WHERE rn = 1 AND status_code = 1
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
    ) AS run_id
  FROM base
),

runs AS (
  SELECT
    production_line_id,
    run_id,
    MIN(CASE WHEN status_code = 0 THEN ts END) AS start_ts,
    MAX(CASE WHEN status_code = 2 THEN ts END) AS stop_ts
  FROM seq
  WHERE status_code IN (0,2)
  GROUP BY 1,2
)

SELECT*
FROM runs
ORDER BY production_line_id, start_ts;

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

total_time AS (
  SELECT min(ts) AS min_ts, max(ts) AS max_ts FROM raw
),

base AS (
  SELECT production_line_id, status_code, ts FROM raw
  UNION ALL
  SELECT production_line_id, 0 AS status_code, (SELECT min_ts FROM total_time) AS ts
  FROM (
    SELECT production_line_id, status_code,
           row_number() OVER (PARTITION BY production_line_id ORDER BY ts) AS rn
    FROM raw
  )
  WHERE rn = 1 AND status_code = 1
),

seq AS (
  SELECT
    production_line_id,
    status_code,
    ts,
    sum(CASE WHEN status_code = 0 THEN 1 ELSE 0 END) OVER (
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
    min(CASE WHEN status_code = 0 THEN ts END) AS start_ts,
    max(CASE WHEN status_code = 2 THEN ts END) AS stop_ts
  FROM seq
  WHERE status_code IN (0,2)
  GROUP BY 1,2
),

dur AS (
  SELECT
    production_line_id,
    date_diff('microsecond', start_ts, coalesce(stop_ts, (SELECT max_ts FROM total_time))) AS dur_us
  FROM runs
),

uptime AS (
  SELECT production_line_id, sum(dur_us) AS uptime_us
  FROM dur
  GROUP BY 1
),

tot AS (
  SELECT
    date_diff('microsecond', (SELECT min_ts FROM total_time), (SELECT max_ts FROM total_time)) AS window_us,
    sum(uptime_us) AS total_uptime_us,
    sum(date_diff('microsecond', (SELECT min_ts FROM total_time), (SELECT max_ts FROM total_time)) - uptime_us) AS total_downtime_us
  FROM uptime
)

SELECT
  (to_timestamp(window_us / 1000000.0)       - to_timestamp(0)) AS total_production_runtime,
  (to_timestamp(total_uptime_us / 1000000.0) - to_timestamp(0)) AS total_uptime,
  (to_timestamp(total_downtime_us / 1000000.0) - to_timestamp(0)) AS total_downtime
FROM tot;

########################################
# rainyesterday.sql  2026-01-09  Frank L. Sherwood
#
### Temp, Humidity, 10-min rain total, 10-min rain/hr
### Reports values for the prior calendar day "yesterday"
################################################################################
# Copyright (C) 2026 Frank L. Sherwood
# All rights reserved.
# 
# This project is publicly viewable for reference only.
# No permission is granted to copy, modify, distribute, or use this code.
# 
################################################################################


WITH Intervals AS (
    SELECT 
        w1.c_mod AS interval_start,
        w1.c_temp,
        w1.c_thi_hum,
        (
            SELECT SUM(c_bucket) 
            FROM WeatherEvents w2 
            WHERE w2.c_mod >= w1.c_mod 
              AND w2.c_mod < COALESCE(
                  (SELECT MIN(w3.c_mod) 
                   FROM WeatherEvents w3 
                   WHERE w3.c_mod > w1.c_mod 
                     AND w3.c_temp IS NOT NULL), 
                  (SELECT MAX(c_mod) FROM WeatherEvents)
              )
              AND w2.c_bucket IS NOT NULL
        ) AS bucket_sum,
        (
            SELECT SUM(c_bucket) 
            FROM WeatherEvents w2 
            WHERE w2.c_mod >= w1.c_mod 
              AND w2.c_mod < COALESCE(
                  (SELECT MIN(w3.c_mod) 
                   FROM WeatherEvents w3 
                   WHERE w3.c_mod > w1.c_mod 
                     AND w3.c_temp IS NOT NULL), 
                  (SELECT MAX(c_mod) FROM WeatherEvents)
              )
              AND w2.c_bucket IS NOT NULL
        ) / 
        ((JULIANDAY(COALESCE(
            (SELECT MIN(w3.c_mod) 
             FROM WeatherEvents w3 
             WHERE w3.c_mod > w1.c_mod 
               AND w3.c_temp IS NOT NULL), 
            (SELECT MAX(c_mod) FROM WeatherEvents)
        )) 
        - JULIANDAY(w1.c_mod)) * 24) AS rain_rate -- Convert days to hours
    FROM WeatherEvents w1
    WHERE w1.c_temp IS NOT NULL
      AND w1.c_mod >= DATETIME('now', 'localtime', '-1 day', 'start of day')
      AND w1.c_mod < DATETIME('now', 'localtime', 'start of day')
)
SELECT 
    interval_start AS c_mod,
    c_temp || '°' AS c_temp,
    c_thi_hum || '%' AS c_thi_hum,
    ROUND(COALESCE(bucket_sum, 0), 3) || '"' AS sum_c_bucket,
    ROUND(COALESCE(rain_rate, 0), 3) || '"' AS rain_rate
FROM Intervals

UNION ALL

SELECT 
    'TOTAL:',
    ROUND(AVG(c_temp), 1) || '°',
    ROUND(AVG(c_thi_hum), 1) || '%',
    ROUND(SUM(c_bucket), 3) || '"',
    ''
FROM WeatherEvents
WHERE c_mod >= DATETIME('now', 'localtime', '-1 day', 'start of day')
  AND c_mod < DATETIME('now', 'localtime', 'start of day');

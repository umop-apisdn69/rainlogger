#!/usr/bin/env python3
########################################
# ws.py v2.0  2026-01-09  Frank L. Sherwood
#
#   Table-formatted daily statistics output
################################################################################
# Copyright (C) 2026 Frank L. Sherwood
# All rights reserved.
# 
# This project is publicly viewable for reference only.
# No permission is granted to copy, modify, distribute, or use this code.
# 
################################################################################

import sqlite3
import sys
from prettytable import PrettyTable

# ANSI color codes
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

def color_yellow(value):
    if value is None:
        return ""
    return f"{YELLOW}{value}{RESET}"

def color_green(value):
    if value is None:
        return ""
    return f"{GREEN}{value}{RESET}"

def weather_summary(start_date, end_date):
    # Ensure the times are set to 00:00:00
    start_time = f"{start_date} 00:00:00"
    end_time = f"{end_date} 00:00:00"

    query = f"""
    -- Define the summary interval, start time, and stop time
    WITH params AS (
        SELECT
            1440 AS interval_minutes, -- Set the desired interval length
            '{start_time}' AS start_time, -- Set the start time
            '{end_time}' AS stop_time -- Set the stop time
    ),
    FilteredData AS (
        SELECT
            c_mod,
            c_bucket,
            c_thi_temp,
            c_thi_hum,
            c_temp,
            date(c_mod) AS interval_start -- Use date function to set the interval_start to the date part only
        FROM
            WeatherEvents, params
        WHERE
            c_mod >= start_time AND c_mod < stop_time
    ),
    RainSummary AS (
        SELECT
            interval_start,
            ROUND(SUM(c_bucket), 5) AS total_rain
        FROM
            FilteredData
        WHERE c_bucket IS NOT NULL
        GROUP BY
            interval_start
    ),
    TempHumidityLatest AS (
        SELECT
            interval_start,
            c_mod,
            c_thi_temp,
            c_thi_hum,
            c_temp,
            ROW_NUMBER() OVER (PARTITION BY interval_start ORDER BY c_mod DESC) AS row_num
        FROM
            FilteredData
        WHERE c_thi_temp IS NOT NULL OR c_thi_hum IS NOT NULL OR c_temp IS NOT NULL
    ),
    TempHumiditySummary AS (
        SELECT
            interval_start,
            MAX(CASE WHEN row_num = 1 THEN c_thi_temp ELSE NULL END) AS latest_thi_temp,
            MAX(CASE WHEN row_num = 1 THEN c_thi_hum ELSE NULL END) AS latest_thi_hum,
            MAX(CASE WHEN row_num = 1 THEN c_temp ELSE NULL END) AS latest_temp,
            MIN(c_thi_hum) AS min_thi_hum,
            MAX(c_thi_hum) AS max_thi_hum,
            AVG(c_thi_hum) AS avg_thi_hum,
            MIN(c_temp) AS min_temp,
            MAX(c_temp) as max_temp,
            AVG(c_temp) AS avg_temp,
            AVG(c_thi_temp) AS avg_thi_temp
        FROM
            TempHumidityLatest
        GROUP BY
            interval_start
    )
    SELECT
        t.interval_start || ' 00:00:00' AS interval_start,
        COALESCE(r.total_rain, 0) AS total_rain,
        t.latest_temp,
        t.latest_thi_hum,
        t.min_temp,
        t.max_temp,
        ROUND(t.avg_temp, 2) AS avg_temp,
        t.min_thi_hum,
        t.max_thi_hum,
        ROUND(t.avg_thi_hum, 2) AS avg_thi_hum,
        t.latest_thi_temp
    FROM
        TempHumiditySummary t
        LEFT JOIN RainSummary r ON t.interval_start = r.interval_start
    UNION ALL
    SELECT
        'Total' AS interval_start,
        ROUND(SUM(c_bucket), 5) AS total_rain,
        NULL AS latest_temp,
        NULL AS latest_thi_hum,
        NULL AS min_temp,
        NULL AS max_temp,
        NULL AS avg_temp,
        NULL AS min_thi_hum,
        NULL AS max_thi_hum,
        NULL AS avg_thi_hum,
        NULL AS latest_thi_temp
    FROM
        FilteredData
    ORDER BY
        interval_start;
    """

    # Connect to the SQLite database
    db_path = '/home/meter/rain/weather/weather.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute the query
    cursor.execute(query)
    results = cursor.fetchall()

    # Custom headers (with colors) - reordered
    headers = [
        'interval_start',
        f'{YELLOW}total_rain{RESET}',
        f'{GREEN}latest_temp{RESET}',
        f'{GREEN}latest_hum{RESET}',
        'min_temp',
        'max_temp',
        'avg_temp',
        'min_hum',
        'max_hum',
        'avg_hum',
        f'{GREEN}latest_thi_temp{RESET}'
    ]

    # Create the table with prettytable
    table = PrettyTable()
    table.field_names = headers

    # Color specific columns for each row
    for row in results:
        row = list(row)
        # total_rain (index 1) -> yellow
        row[1] = color_yellow(row[1])
        # latest_temp (index 2) -> green
        row[2] = color_green(row[2])
        # latest_thi_hum (index 3) -> green with "%"
        row[3] = color_green(str(row[3]) + "%") if row[3] is not None else ""
        # min_thi_hum (index 7) -> add "%"
        row[7] = str(row[7]) + "%" if row[7] is not None else ""
        # max_thi_hum (index 8) -> add "%"
        row[8] = str(row[8]) + "%" if row[8] is not None else ""
        # avg_thi_hum (index 9) -> add "%"
        row[9] = str(row[9]) + "%" if row[9] is not None else ""
        # latest_thi_temp (index 10) -> green
        row[10] = color_green(row[10])

        table.add_row(row)

    table.align = "l"
    table.hrules = False  # Remove horizontal rules

    # Customize column separators
    table.vertical_char = '|'  # Default vertical separator
    table.horizontal_char = '-'  # Default horizontal separator
    table.junction_char = '+'  # Default junction character

    # Print the formatted table with custom separators
    table_str = table.get_string()

    # Update the occurrences of '|' to 'ǁ' for the 5th, 8th, and 11th column separators (double bar positions)
    def replace_separator(line):
        count = 0
        new_line = ""
        for char in line:
            if char == '|':
                count += 1
                if count == 5 or count == 8 or count == 11:
                    new_line += 'ǁ'
                    continue
            new_line += char
        return new_line

    lines = table_str.split('\n')
    updated_lines = [replace_separator(line) if line.count('|') > 9 else line for line in lines]

    # Add headers at the end (footer), already colored via headers
    header_line = updated_lines[1]  # Assuming the second line contains the header
    updated_lines.append(header_line)
    updated_lines.append(updated_lines[2])  # Adding separator line

    updated_table_str = '\n'.join(updated_lines)

    print(updated_table_str)

    # Close the connection
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: weathersummary <start_date> <end_date>")
        sys.exit(1)

    start_date = sys.argv[1]
    end_date = sys.argv[2]

    weather_summary(start_date, end_date)

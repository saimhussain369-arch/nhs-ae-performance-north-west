-- Reporting tables: England and North West by month, and North West trusts by month.
CREATE OR REPLACE TABLE area_month AS
WITH areas AS (
    SELECT 'England' AS area, * FROM ae_provider_month_measures
    UNION ALL
    SELECT '{{REGION_LABEL}}', * FROM ae_provider_month_measures WHERE region = '{{REGION}}'
)
SELECT
    area,
    month,
    sum(attendances)                                            AS attendances,
    sum(over_4h)                                                AS over_4h,
    round(100.0 * (1 - sum(over_4h) / sum(attendances)), 1)     AS pct_within_4h,
    round(100.0 * (1 - sum(over_4h_type1) / sum(attendances_type1)), 1) AS pct_within_4h_type1,
    sum(emergency_admissions_via_ae)                            AS emergency_admissions_via_ae,
    sum(dta_12h_plus)                                           AS waits_12h_plus_from_decision_to_admit,
    round(100.0 * sum(dta_12h_plus) / nullif(sum(emergency_admissions_via_ae), 0), 1) AS pct_admissions_waiting_12h_plus
FROM areas
GROUP BY ALL
ORDER BY area, month;

CREATE OR REPLACE TABLE trust_month AS
SELECT
    month, org_code, org_name,
    attendances, over_4h,
    round(100.0 * (1 - over_4h / nullif(attendances, 0)), 1)                 AS pct_within_4h,
    attendances_type1, over_4h_type1,
    round(100.0 * (1 - over_4h_type1 / nullif(attendances_type1, 0)), 1)     AS pct_within_4h_type1,
    emergency_admissions_via_ae, dta_12h_plus
FROM ae_provider_month_measures
WHERE region = '{{REGION}}' AND attendances_type1 >= {{MIN_TYPE1_ATTENDANCES}}
ORDER BY month, org_name;

-- League table over the latest three months, so one unusual month does not decide a trust's position
CREATE OR REPLACE TABLE trust_latest_quarter AS
WITH latest AS (SELECT max(month) AS m FROM ae_provider_month)
SELECT
    org_code, org_name,
    count(*)                                                     AS months,
    sum(attendances)                                             AS attendances,
    round(100.0 * (1 - sum(over_4h) / sum(attendances)), 1)      AS pct_within_4h,
    round(100.0 * (1 - sum(over_4h_type1) / sum(attendances_type1)), 1) AS pct_within_4h_type1,
    sum(dta_12h_plus)                                            AS dta_12h_plus
FROM trust_month, latest
WHERE month > latest.m - INTERVAL 3 MONTH
GROUP BY ALL
ORDER BY pct_within_4h DESC;

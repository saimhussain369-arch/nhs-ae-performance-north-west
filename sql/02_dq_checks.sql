-- Data quality checks. Every check writes one row per failure; dq_summary counts them.
CREATE OR REPLACE TABLE dq_failures AS

-- 1. The Period inside the file must match the month we downloaded it for
SELECT 'period_matches_file' AS check_name, month, org_code,
       'Period in file is ' || period || ', expected ' || expected_period AS detail
FROM ae_provider_month WHERE period <> expected_period

UNION ALL
-- 2. One row per provider per month
SELECT 'one_row_per_provider_month', month, org_code, count(*) || ' rows'
FROM ae_provider_month GROUP BY month, org_code HAVING count(*) > 1

UNION ALL
-- 3. Every count must be a whole number of zero or more
SELECT 'counts_are_valid', month, org_code, 'Missing, non-numeric or negative count'
FROM ae_provider_month
WHERE {% for c in NUMERIC %}coalesce({{c}}, -1) < 0{% if not loop.last %} OR {% endif %}{% endfor %}

UNION ALL
-- 4. Patients waiting over 4 hours cannot exceed patients who attended
SELECT 'over_4h_not_above_attendances', month, org_code,
       over_4h || ' over 4 hours vs ' || attendances || ' attendances'
FROM ae_provider_month_measures WHERE over_4h > attendances OR over_4h_type1 > attendances_type1

UNION ALL
-- 5. Our sum of all providers must equal the national TOTAL row NHS England publishes
SELECT 'providers_reconcile_to_published_total', p.month, 'TOTAL',
       'Sum of providers ' || p.attendances || ' vs published ' || t.attendances || ' attendances; '
       || p.over_4h || ' vs ' || t.over_4h || ' over 4 hours'
FROM (SELECT month, sum(attendances) AS attendances, sum(over_4h) AS over_4h
      FROM ae_provider_month_measures GROUP BY month) p
JOIN (SELECT month,
             att_type1 + att_type2 + att_other + att_booked_type1 + att_booked_type2 + att_booked_other AS attendances,
             over4_type1 + over4_type2 + over4_other + over4_booked_type1 + over4_booked_type2 + over4_booked_other AS over_4h
      FROM published_totals) t USING (month)
WHERE p.attendances <> t.attendances OR p.over_4h <> t.over_4h

UNION ALL
-- 6. Every month in the source list must have a published TOTAL row
SELECT 'published_total_present', m.month, 'TOTAL', 'No TOTAL row in file'
FROM (SELECT DISTINCT month FROM ae_provider_month) m
LEFT JOIN published_totals t USING (month) WHERE t.month IS NULL;

CREATE OR REPLACE TABLE dq_summary AS
SELECT c.check_name, c.description, count(f.check_name) AS failures,
       CASE WHEN count(f.check_name) = 0 THEN 'Pass' ELSE 'Fail' END AS status
FROM (VALUES
    ('period_matches_file', 'Period in each file matches the month it was downloaded for'),
    ('one_row_per_provider_month', 'Each provider appears once per month'),
    ('counts_are_valid', 'All counts are present, numeric and not negative'),
    ('over_4h_not_above_attendances', 'Patients over 4 hours never exceed attendances'),
    ('providers_reconcile_to_published_total', 'Sum of providers equals NHS England''s published national total'),
    ('published_total_present', 'Every file contains the national TOTAL row')
) AS c(check_name, description)
LEFT JOIN dq_failures f USING (check_name)
GROUP BY ALL
ORDER BY c.check_name;

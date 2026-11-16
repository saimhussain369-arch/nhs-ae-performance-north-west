-- Typed, tidied provider rows. The national TOTAL row NHS England publishes in each
-- file is kept separately so it can be used to reconcile our own totals.
CREATE OR REPLACE TABLE published_totals AS
SELECT
    CAST(month || '-01' AS DATE) AS month,
    {% for c in NUMERIC %}TRY_CAST(replace({{c}}, ',', '') AS BIGINT) AS {{c}}{% if not loop.last %}, {% endif %}{% endfor %}
FROM bronze_ae
WHERE upper(trim(org_code)) = 'TOTAL';

CREATE OR REPLACE TABLE ae_provider_month AS
SELECT
    CAST(month || '-01' AS DATE)                      AS month,
    source_file,
    trim(period)                                      AS period,
    upper(trim(org_code))                             AS org_code,
    upper(trim(parent_org))                           AS region,
    trim(org_name)                                    AS org_name,
    {% for c in NUMERIC %}TRY_CAST(replace({{c}}, ',', '') AS BIGINT) AS {{c}},
    {% endfor %}'MSitAE-' || upper(strftime(CAST(month || '-01' AS DATE), '%B')) || '-'
        || strftime(CAST(month || '-01' AS DATE), '%Y') AS expected_period
FROM bronze_ae
WHERE upper(trim(org_code)) <> 'TOTAL';

-- Add the measures used throughout: totals across all department types, including booked appointments,
-- which is how NHS England calculates its headline four-hour figure.
CREATE OR REPLACE TABLE ae_provider_month_measures AS
SELECT
    *,
    att_type1 + att_type2 + att_other + att_booked_type1 + att_booked_type2 + att_booked_other AS attendances,
    over4_type1 + over4_type2 + over4_other + over4_booked_type1 + over4_booked_type2 + over4_booked_other AS over_4h,
    att_type1 + att_booked_type1                      AS attendances_type1,
    over4_type1 + over4_booked_type1                  AS over_4h_type1,
    adm_type1 + adm_type2 + adm_other                 AS emergency_admissions_via_ae
FROM ae_provider_month;

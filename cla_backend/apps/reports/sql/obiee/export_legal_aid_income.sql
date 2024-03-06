COPY (SELECT
id,
created,
modified,
earnings_interval_period,
earnings_per_interval_value,
earnings,
self_employment_drawings_interval_period,
self_employment_drawings_per_interval_value,
self_employment_drawings,
benefits_interval_period,
benefits_per_interval_value,
benefits,
tax_credits_interval_period,
tax_credits_per_interval_value,
tax_credits,
child_benefits_interval_period,
child_benefits_per_interval_value,
child_benefits,
maintenance_received_interval_period,
maintenance_received_per_interval_value,
maintenance_received,
pension_interval_period,
pension_per_interval_value,
pension,
other_income_interval_period,
other_income_per_interval_value,
other_income,
self_employed
FROM legalaid_income
WHERE (modified >= %(from_date)s::timestamp AND modified <= %(to_date)s::timestamp)
OR (created >= %(from_date)s::timestamp AND created <= %(to_date)s::timestamp))
TO STDOUT CSV HEADER;

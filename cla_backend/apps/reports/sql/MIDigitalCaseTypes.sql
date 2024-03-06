SELECT
   c.laa_reference as LAA_Reference
  ,c.reference as Case_Ref
  ,c.source as Contact_Type
  ,CASE WHEN u.username = 'web' then 'web' ELSE 'operator' END "case_created_by"
  ,COALESCE((log.context->>'eligibility_state' = 'yes')::bool, false) as "means_test_completed_online"
  ,CASE WHEN u.username = 'web' THEN (log.context->>'eligibility_state') IS NULL ELSE FALSE END as "call_me_back_only"
  ,d.state
  ,e.state
  ,c.outcome_code
  ,c.created
FROM legalaid_case as c
  LEFT JOIN cla_eventlog_log as log on log.case_id = c.id and log.code = 'CASE_CREATED'
  LEFT OUTER JOIN auth_user u on u.id = c.created_by_id
  LEFT JOIN diagnosis_diagnosistraversal d on c.diagnosis_id = d.id
  LEFT JOIN legalaid_eligibilitycheck e on c.eligibility_check_id = e.id
    WHERE
    c.created >= %s
    and c.created < %s;

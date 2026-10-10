# Test plan and results

**How to read the Actual / Status columns**
- Rows marked **Automated** are checked by `pytest` in `backend/tests`. The "Actual" text below was filled from the author's run of the full suite (61 passed, 8 Oct 2026). Re-run on your laptop (`cd backend; pytest -q -v`) and write your own date and result before you submit.
- Rows marked **Manual** need AWS, GitHub or a browser. They are **not run yet**. Run each one, then fill Actual and Status yourself, and keep a screenshot as evidence for your report.

Run all automated tests with verbose names: `pytest -v`

## A. Authentication

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-01 | Automated `test_register_success` | Registration | username `bob_1`, valid password | 201, username returned, no password in response | As expected | PASS |
| TC-02 | Automated `test_register_duplicate_username` | Duplicate registration | same username twice | 409 | As expected | PASS |
| TC-03 | Automated `test_register_weak_password_rejected` | Short password | password `short` | 422 | As expected | PASS |
| TC-04 | Automated `test_register_invalid_username_rejected` | Invalid username | `bad name!` | 422 | As expected | PASS |
| TC-05 | Automated `test_login_success_returns_token` | Login | correct credentials | 200 and `access_token` | As expected | PASS |
| TC-06 | Automated `test_login_wrong_password` | Invalid login | wrong password | 401 | As expected | PASS |
| TC-07 | Automated `test_login_unknown_user` | Invalid login | unknown username | 401 (same message as TC-06) | As expected | PASS |
| TC-08 | Automated `test_password_is_not_stored_in_plain_text` | Password hashing | register, read DB row | stored value differs from password and starts with `$2` (bcrypt) | As expected | PASS |

## B. Unauthorized access

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-09 | Automated `test_me_requires_token` | No token | `GET /auth/me` | 401 | As expected | PASS |
| TC-10 | Automated `test_me_rejects_garbage_token` | Fake token | `Bearer not-a-real-token` | 401 | As expected | PASS |
| TC-11 | Automated `test_projects_require_login` | Projects without login | `GET/POST /projects` | 401 | As expected | PASS |
| TC-12 | Automated `test_users_cannot_see_each_others_projects` | Cross-user access | user B opens user A's project, scan, deploy | 404 on every call | As expected | PASS |
| TC-13 | Automated `test_system_stats_require_login`, `test_explain_endpoint_requires_login` | Other protected endpoints | no token | 401 | As expected | PASS |

## C. Project creation and repository validation

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-14 | Automated `test_create_and_list_project` | Project creation | valid name and GitHub URL | 201, status `registered`, appears in list | As expected | PASS |
| TC-15 | Automated `test_empty_name_rejected` | Invalid input | empty name | 422 | As expected | PASS |
| TC-16 | Automated `test_invalid_repo_urls_rejected`, `test_validate_repo_url_rejects_bad_urls` | Repository validation | http URL, other host, no repo, `; rm -rf /`, `file://`, lookalike host | 422 / ValueError for every one | As expected | PASS |
| TC-17 | Automated `test_validate_repo_url_accepts_good_urls` | Valid repository | `https://github.com/octocat/Hello-World(.git)` | owner and repo parsed | As expected | PASS |

## D. Scan and deploy rules

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-18 | Automated `test_clean_repo_passes` | Clean repo scan | repo with Dockerfile, requirements, .gitignore, tests | status `passed` | As expected | PASS |
| TC-19 | Automated `test_missing_dockerfile_is_a_warning` | Warning severity | no Dockerfile | status `warnings` | As expected | PASS |
| TC-20 | Automated `test_committed_env_file_is_critical_and_fails` | Secret file detection (pre-flight) | repo root contains `.env` | CRITICAL finding, status `failed` | As expected | PASS |
| TC-21 | Automated `test_env_example_is_not_flagged` | No false alarm | `.env.example` only | status `passed` | As expected | PASS |
| TC-22 | Automated `test_repo_not_found_gives_friendly_error`, `..._rate_limit_...`, `..._network_failure_...` | GitHub errors | 404 / 403 / network down | status `error` with a readable message | As expected | PASS |
| TC-23 | Automated `test_scan_stores_result` | Scan result stored | click scan | result saved and listed | As expected | PASS |
| TC-24 | Automated `test_deploy_blocked_without_scan` | Deploy before scan | deploy with no scan | 400 | As expected | PASS |
| TC-25 | Automated `test_deploy_blocked_when_scan_failed` | Deploy after failed scan | latest scan failed | 400 | As expected | PASS |
| TC-26 | Automated `test_deploy_allowed_after_passing_scan` | Deploy after good scan | latest scan passed | 202, deployment `queued` | As expected | PASS |

## E. Deployment reporting (pipeline to dashboard)

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-27 | Automated `test_report_success_sets_live_url_and_status` | Successful deployment recorded | report success with live URL and valid token | 201, project `deployed`, live URL saved | As expected | PASS |
| TC-28 | Automated `test_report_failed_marks_project_failed` | Failed deployment recorded | report failed | project `deploy_failed`, no live URL | As expected | PASS |
| TC-29 | Automated `test_report_rejects_missing_or_wrong_token` | Report without secret | no / wrong `X-Deploy-Token` | 401 | As expected | PASS |
| TC-30 | Automated `test_report_disabled_when_token_not_configured` | Feature off by default | token not configured | 503 | As expected | PASS |
| TC-31 | Automated `test_report_rejects_dangerous_live_urls` | Invalid input | `file://`, URL with password, path, `javascript:` | 422 for each | As expected | PASS |
| TC-32 | Automated `test_report_unknown_project` | Unknown project | project id 999 | 404 | As expected | PASS |

## F. Monitoring

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-33 | Automated `test_health_returns_ok` | Health endpoint | `GET /health` | 200 `{"status":"ok"}` | As expected | PASS |
| TC-34 | Automated `test_system_stats_shape` | Server metrics | `GET /monitoring/system` | CPU, memory, disk, uptime present, memory 0 to 100 | As expected | PASS |
| TC-35 | Automated `test_health_checks_and_uptime_summary` | Uptime maths | 2 successes (40 ms, 60 ms), 1 failure | 3 checks, uptime 66.7%, average 50 ms, last_ok false | As expected | PASS |
| TC-36 | Automated `test_check_without_live_url_is_rejected`, `test_summary_with_no_checks` | Edge cases | undeployed project | 400 / empty summary | As expected | PASS |
| TC-37 | Automated `test_other_user_cannot_check_my_project` | Monitoring isolation | other user | 404 | As expected | PASS |

## G. Error explanation

| ID | Type | Test | Input | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| TC-38 | Automated `test_explain_module_not_found` | Known error | `ModuleNotFoundError ...` | "A Python package is missing" | As expected | PASS |
| TC-39 | Automated `test_explain_unknown_error_has_fallback` | Unknown error | gibberish | fallback advice | As expected | PASS |
| TC-40 | Automated `test_sanitize_removes_*` (5 tests), `test_explain_endpoint_sanitizes_and_explains` | Secret removal | fake AWS key, GitHub token, `password=...`, DB URL password, email, bearer token | none of the secrets remain in the output | As expected | PASS |
| TC-41 | Automated `test_sanitize_truncates_huge_logs`, `test_explain_endpoint_rejects_empty_log` | Input limits | 50,000 characters / empty log | cut to 10,000 / 422 | As expected | PASS |

## H. Pipeline and cloud behaviour (MANUAL, not run yet)

Write down date, what you did, what you saw, and attach a screenshot.

| ID | Test | Steps | Expected | Actual | Status |
|---|---|---|---|---|---|
| TC-42 | Successful deployment | Push a small change to `main` | CI green, Deploy green, new version at `http://HOST`, history entry in dashboard | | |
| TC-43 | Failed tests stop deployment | On a branch, change an assertion in a test so it fails, open a pull request | Run tests job red; Deploy never starts (it only follows a successful CI on `main`) | | |
| TC-44 | Secret detection | On a throwaway branch add a file containing an obviously fake key such as `AKIA` followed by 16 capital letters, open a pull request, then delete the branch | Secret scan (Gitleaks) job red. If it stays green, record that honestly and explain why (Gitleaks rules are pattern based) | | |
| TC-45 | Critical vulnerability detection | On a throwaway branch change the Dockerfile base image to a very old Python image and push | Trivy image scan reports vulnerabilities; the job fails only if CRITICAL fixable ones exist. Results depend on today's vulnerability database, so record exactly what you saw | | |
| TC-46 | Failed deployment and rollback | SSH to the server and run `IMAGE='nginx:alpine' bash ~/remote-deploy.sh` (a real image that has no `/health` on the app port, so the new version is "broken") | Script prints that the new version FAILED its health check, rolls back to the previous image, `http://HOST/health` answers again, and the script exits with an error | | |
| TC-47 | Health monitoring detects downtime | On the server `docker stop deploy-platform`; run the Uptime check workflow; then `docker start deploy-platform` | Uptime run fails and emails you; dashboard Monitoring shows DOWN after "Check now"; after restart shows UP | | |
| TC-48 | Security group | From your laptop try `Test-NetConnection HOST -Port 5432` and `-Port 8000` | Both fail (closed). Port 80 succeeds | | |
| TC-49 | Cost control | After the viva, terminate the instance and check Volumes and Elastic IPs | None left; no unexpected charge next day | | |

## Summary table for your report

| Group | Cases | Automated | Manual |
|---|---|---|---|
| Authentication | 8 | 8 | 0 |
| Unauthorized access | 5 | 5 | 0 |
| Projects and validation | 4 | 4 | 0 |
| Scan and deploy rules | 9 | 9 | 0 |
| Deployment reporting | 6 | 6 | 0 |
| Monitoring | 5 | 5 | 0 |
| Error explanation | 4 | 4 | 0 |
| Pipeline and cloud | 8 | 0 | 8 |
| **Total** | **49** | **41** | **8** |

The 41 automated cases are covered by 61 individual pytest tests (some cases use several tests).

# Application test catalog

This catalog describes the tests in `app_tests/` and `browser_tests/`. Update it in the same change whenever a test is added, removed, renamed, or its expected behavior changes. Run instructions are in the [README](../README.md#tests).

## API and database tests

The tests use pytest and a PostgreSQL database initialized with migrations and seed data. API scenarios use FastAPI's test client; database constraint scenarios also execute SQL directly. Use an isolated test database: some tests create users and sessions and do not remove them. The seed test expects the initial four offices, twelve rooms, and sixteen equipment units.

| Test | What it checks |
| --- | --- |
| `app_tests/test_initial.py::test_seed_is_repeatable_and_preserves_admin` | Runs initialization twice, verifies the counts of initial offices, rooms, and equipment, and checks that the existing administrator's password hash is unchanged. |
| `app_tests/test_initial.py::test_user_lifecycle_and_permissions` | Checks unauthenticated access, administrator user creation, user authorization, CSRF enforcement, password change, session invalidation, administrator password reset, and login with the reset password. |
| `app_tests/test_constraints.py::test_room_capacity_and_reference_constraints` | Checks that PostgreSQL rejects a room referring to a nonexistent office and a room with zero capacity. |
| `app_tests/test_constraints.py::test_equipment_type_constraint` | Checks that PostgreSQL rejects an unsupported equipment type. |
| `app_tests/test_security.py::test_csrf_cookie_rotation_and_expiry` | Checks cookie flags, CSRF token rotation, rejection of the previous token, and rejection of an expired session. |
| `app_tests/test_security.py::test_admin_normalizes_email_hashes_password_and_revokes_sessions` | Checks email normalization, password hashing, and invalidation of multiple user sessions after an administrator resets the password. |
| `app_tests/test_security.py::test_login_rate_limit` | Checks that ten failed login attempts are rejected and the next attempt is rate-limited. |
| `app_tests/test_resources.py::test_resource_crud_authorization_and_validation` | Checks resource creation, editing, listing, deactivation, validation, authorization, CSRF, and conflicts with inactive offices. |
| `app_tests/test_resources.py::test_deactivation_preserves_booked_resources` | Checks that an office, room, and equipment allocated to an active future booking cannot be deactivated. |
| `app_tests/test_booking_schema.py::test_room_and_equipment_intervals_and_cancellation` | Checks database constraints for overlapping room and equipment allocations, permits adjacent room intervals, and verifies that cancellation propagates to the equipment allocation and frees the room. The test rolls back its transaction. |

The booking schema test checks database behavior directly. It does not test a booking API, a browser booking flow, repair conflicts, or concurrent transactions; those workflows are not yet implemented.

## Browser tests

The tests use synchronous Playwright with Chromium against a running application. They require `APP_URL`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` for an initialized test environment. The user-creation scenario leaves a test account in the database, so use an isolated test environment.

| Test | What it checks |
| --- | --- |
| `browser_tests/test_account.py::test_administrator_can_sign_in_and_out` | Signs in as an administrator, verifies the account and user-creation screens, signs out, and verifies the login screen. |
| `browser_tests/test_account.py::test_administrator_can_edit_and_restore_office` | Edits an office through the administrator interface and restores its original name. |
| `browser_tests/test_account.py::test_administrator_can_edit_room_and_equipment` | Edits a room and an equipment label through the administrator interface and restores them. |
| `browser_tests/test_account.py::test_admin_creates_user_and_user_changes_password` | Creates a user through the administrator interface, signs in as that user, verifies resource browsing is visible and administrator forms are hidden, changes the password, and signs in with the new password. |

## Continuous integration

The `application` job in `.github/workflows/tests.yml` initializes PostgreSQL, runs `app_tests/`, starts the application, and runs `browser_tests/`. The separate legacy static-form tests in `tests/` are outside this catalog and are not run by the current CI workflow.

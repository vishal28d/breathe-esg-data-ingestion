# Tradeoffs

Three things we deliberately did not build and why:

## 1. Authentication and Authorization (OAuth / SSO)
*   **What we omitted**: There is no login screen, JWT handling, or role-based access control (RBAC). The UI hardcodes the `tenantId` to `1` and assumes the user is an "Analyst".
*   **Why**: Building auth takes significant time and boilerplate. For a 4-day prototype focused on data modeling and ingestion logic, auth provides zero signal on engineering judgment. We modeled the database for it (using `django.contrib.auth.models.User` for `approved_by` fields) so it can be dropped in later.

## 2. Dynamic Emission Factor Year/Version Matching
*   **What we omitted**: The database has a flat `EmissionFactor` table. It does not account for the fact that a 2024 electricity bill should use the 2024 DEFRA factor, while a 2023 bill should use the 2023 factor.
*   **Why**: Adding temporal validity (`valid_from`, `valid_to`) to emission factors drastically increases the complexity of the lookup logic (requiring range queries against the activity date). For a prototype, applying a static "latest available" factor demonstrates the mechanism without getting bogged down in temporal data engineering.

## 3. Asynchronous Task Queues (Celery/Redis)
*   **What we omitted**: File uploads and API pulls are processed synchronously in the Django request/response cycle. 
*   **Why**: Processing a 10,000-row CSV synchronously will cause a request timeout on platforms like Render. In production, this must be offloaded to Celery. However, setting up a Redis broker and Celery workers for a local/prototype deployment adds massive infrastructure overhead. We prioritized a clean synchronous parser that can be easily wrapped in a `@shared_task` later.

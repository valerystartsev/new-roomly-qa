# GitHub Flow

The `main` branch is the integration branch. Keep it in a releasable state and use a separate, short-lived branch for each change. Open a pull request (PR) into `main`; do not push changes directly to `main` as part of the normal workflow.

1. Start from an up-to-date `main` and create a descriptive branch, for example `feature/room-booking`, `fix/session-expiry`, or `docs/api-guide`. Preserve any uncommitted work before switching branches.
2. Implement one focused change, including the relevant automated tests and documentation. Record partially completed stages accurately in the specification checklist.
3. Run the checks relevant to the change. The GitHub Actions workflow runs the application API/database and account browser tests on pushes and pull requests. The original static-form Python suite is available locally and is not run in CI. Local commands are documented in the README.
4. Commit and push the branch when authorized. Open a PR against `main`, describe the behavior and validation, and note incomplete work or failures. A draft PR is appropriate for work in progress.
5. Review the diff and CI results. Resolve review feedback, test failures, and conflicts in the branch. Merge only after the required checks pass and the user approves the merge. Do not delete branches without approval.
6. After a merge, update local `main` before beginning the next change.

GitHub branch protection and required checks are repository settings, not properties of this document. Configure and verify them separately if desired; this workflow does not assume they are enabled. If the project has only one contributor, use the PR to inspect the change and checks without assuming an independent reviewer is available.

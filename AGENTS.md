# Repository Guidelines

## Project Structure & Module Organization

The booking page is a static application: `index.html` contains the form, `styles.css` its presentation, and `script.js` its client-side validation. Python browser tests live in `tests/`; `conftest.py` supplies the shared `base_url` fixture, and `pytest.ini` configures Chromium and reporting. `Dockerfile`, `compose.yaml`, and `.github/workflows/tests.yml` define the test environment and CI.

## Build, Test, and Development Commands

- `docker compose run --build --rm tests` builds the test image and runs the suite, as in CI.
- `python -m pip install -r requirements.txt` and `python -m playwright install chromium` install local test dependencies and the browser.
- `python -m pytest` runs the suite locally; `python -m pytest tests/test_smoke.py` runs the infrastructure smoke test alone.
- `python -m http.server 8000` serves the static page locally. Set `BASE_URL=http://localhost:8000/` for local pytest runs, or pass `--base-url` to override it. Docker tests need a URL reachable from inside the container.

## Coding Style & Naming Conventions

Follow the surrounding code: four-space indentation and `snake_case` for Python, two-space indentation and `camelCase` for JavaScript, and descriptive kebab-case CSS classes. Name test files `test_*.py` and test functions `test_*`. No formatter or linter is configured; keep changes consistent with existing files.

## Testing Guidelines

Use pytest with the synchronous Playwright API and prefer user-visible role or label locators. The smoke test checks availability and does not count toward the three requested scenarios: a positive case, a negative case, and a discovered defect. For a defect test, assert the intended behavior and use `xfail(strict=True, reason="BUG-01: ...", raises=AssertionError)`; do not hide environment failures or fix the application as part of the QA assignment. No coverage threshold is configured. Reports and failure screenshots/traces are written to `artifacts/`.

## Commits & Pull Requests

History contains only an initial commit, so no established commit convention can be inferred. Use concise, descriptive commit subjects. In pull requests, explain the change, summarize test results, link relevant issues, and include screenshots for visible changes when useful. For QA submissions, include the checklist, defect reports, assumptions, risks, environment details, and execution results described in `README.md`.

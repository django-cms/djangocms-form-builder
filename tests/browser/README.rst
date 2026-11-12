Browser regression tests
========================

From the repository root, in a Python environment with the test requirements
and this package's ``formset`` extra installed, run::

    python tests/browser/render_fixtures.py
    npm ci
    npx playwright install chromium
    npm run test:browser

The fixtures render the production templates and JavaScript without a running
CMS or database. Playwright intercepts the submission endpoint and CAPTCHA API
to exercise keyboard submission, validation feedback, retry behavior and token
handling deterministically. Python tests cover the actual Django endpoint and
form binding. Live CAPTCHA verification against Google is not part of this suite.

The ``Django formset frontend`` workflow runs both suites with the frontend
enabled. Generated fixtures and browser output are ignored by Git.

# Release Notes

## 2026-01-20

### Summary
- Minerva-first voice/UI updates across mobile apps and tests.
- Regression gate documented; flaky Cerner conditions integration test marked xfail.

### Tests
- `ehr-proxy`: `pytest tests/test_integration_real_services.py -v -s` (8 passed, 9 skipped, 1 xfailed)
- `ai-service`: `.venv-3.12/bin/pytest tests/` (120 passed)
- `web`: `npm run test:run` (106 passed)
- `mobile/android`: `./gradlew test` (passed)

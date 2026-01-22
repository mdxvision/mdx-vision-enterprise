# Repository Guidelines

## Project Structure & Module Organization
- `web/`: Next.js dashboard (`web/src`) with UI tests in `web/src/__tests__`.
- `mobile/`: React Native app (`mobile/src`) with Android code in `mobile/android` and tests in `mobile/android/app/src/test` and `mobile/android/app/src/androidTest`.
- `backend/`: Spring Boot service (`backend/src/main/java`) with JUnit tests in `backend/src/test/java`.
- `ai-service/`: FastAPI AI pipeline (`ai-service/app`) with tests in `ai-service/tests`.
- `ehr-proxy/`: FastAPI EHR proxy (`ehr-proxy/main.py`) with tests in `ehr-proxy/tests`.
- `docs/` and root Markdown files: product, testing, and operational documentation.

## Build, Test, and Development Commands
- Web: `cd web && npm run dev` (local), `npm run build` (production), `npm test` (Vitest).
- Mobile: `cd mobile && npm run start` (Metro), `npm run android` or `npm run ios`, `npm test`, `npm run lint`.
- Backend: `cd backend && ./mvnw spring-boot:run`, `./mvnw clean package`, `./mvnw test`.
- AI service: `cd ai-service && pip install -r requirements.txt`, `uvicorn app.main:app --reload`.
- EHR proxy: `cd ehr-proxy && python main.py` (serves on port 8002 by default).

## Coding Style & Naming Conventions
- TypeScript/React: follow existing patterns in `web/src` and `mobile/src`; use ESLint (`npm run lint`) and keep components in `PascalCase` with hooks in `camelCase` prefixed by `use`.
- Mobile formatting: Prettier is available via `mobile` devDependencies.
- Java: follow Spring Boot conventions and existing package structure under `com.mdxvision`.
- Python: keep modules focused (FastAPI routers/services); prefer explicit typing where used in the codebase.

## Testing Guidelines
- Python services use `pytest` (`ai-service/tests`, `ehr-proxy/tests`).
- Web uses Vitest (`npm test`), mobile uses Jest (`npm test`), backend uses JUnit via Maven.
- Integration tests for EHR proxy are opt-in: `pytest tests/ --live` with markers like `-m ehr` or `-m assemblyai` (see `TESTING.md`).

## Release Gate (Regression Safety)
- Required automated tests: `ehr-proxy` (`pytest tests/`), `ai-service` (`pytest tests/`), `web` (`npm test`), `mobile/android` (`./gradlew test`).
- Required device validation: complete `VUZIX_MINERVA_CHECKLIST.md` on Vuzix.
- API changes require opt-in live tests: `ehr-proxy` (`pytest tests/ --live`).
- Update `MANUAL_TESTING_CHECKLIST.md` for voice or UX changes.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and descriptive (e.g., “Add …”, “Refactor …”).
- PRs should include a concise summary, test commands run, and linked issues.
- Include screenshots or recordings for web/mobile UI changes.

## Security & Configuration Tips
- Do not commit secrets; use local `.env` files (e.g., `ehr-proxy/.env`) and environment variables for API keys.
- Integration tests require real credentials; verify in a non-production sandbox before running live tests.

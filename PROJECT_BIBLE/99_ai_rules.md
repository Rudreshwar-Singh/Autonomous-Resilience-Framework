# AI Coding Rules

These rules must be followed for every code generation request throughout this project.

## Code Quality
- Write interview-quality, modular, and well-documented code.
- Prefer clean and readable code over clever, "golfed" code.
- Keep files and functions small and focused.
- Follow Python best practices and PEP 8.
- Avoid unnecessary abstractions and premature optimization.

## Architecture & Infrastructure
- Follow the project architecture defined in `01_architecture.md`.
- **Modular Monolith First:** All backend domains communicate via internal Python function calls in the MVP. Do NOT write network requests (e.g., `requests.get()`) between internal domains yet.
- Keep components loosely coupled; prefer composition over inheritance.
- Never introduce new frameworks, dependencies, or databases unless explicitly required and verified against `98_project_constraints.md`.

## Python & Framework Standards
- Use Python 3.12.
- **Strict Typing:** Always use type hints for function signatures and variables.
- **Pydantic v2:** Always use Pydantic v2 syntax (`model_validate`, `model_dump`, etc.). Do not use deprecated v1 methods.
- Use FastAPI best practices (Dependency Injection, APIRouter).
- Always use docstrings for public classes and functions.
- Use meaningful variable and function names. Avoid duplicate code.

## Logging & Error Handling
- Always use structured logging.
- Handle exceptions gracefully and provide clear, actionable error messages.
- Never silently ignore errors (no bare `except:` or `pass`).

## Documentation & File Management
- **Never rename or move existing folders/files** without explicit human approval.
- Explain every major architectural decision.
- Add inline comments only when they explain the "why", not the "what".
- Update `README.md` and `docs/API_EXAMPLES.md` after every major milestone.
- Keep documentation synchronized with implementation.

## Project Safety
- Never remove existing functionality unless explicitly requested.
- Preserve backward compatibility with existing API contracts in `backend/contracts/`.
- Verify existing features continue to work after making changes.

## Output Expectations
Generated code should be:
- Interview-quality and easy to explain during technical interviews.
- Modular, Readable, and Maintainable.
- Free of placeholder code (e.g., `// logic goes here`) unless specifically instructed to write a skeleton.
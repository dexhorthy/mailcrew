# Package Management
- Use uv for dependency management
- Add dependencies: `uv add <package>`
- Run files: `uv run <file>`
- For version conflicts: Align package versions rather than using --frozen flag
- When adding packages that have strict version requirements, check and adjust existing dependencies first

# Project Architecture
- FastAPI-based API with AI capabilities
- Uses multiple AI tools:
  - CrewAI for agent-based operations
  - HumanLayer for additional AI capabilities
- Strong typing and validation with Pydantic
- Primary focus: Email processing with AI agents

# Python Package Structure
- Project is a proper Python package
- Import from package root (e.g., `from api.app.agent import X`)
- Do not use relative imports
- Maintain __init__.py files in all directories

# Development
Tasks should be added to Makefile:
- make test
- make lint
- make fmt

Dependencies for testing/linting should be added as dev dependencies in UV

Note: Never use make run / uvicorn directly, the user will run the server in another tab
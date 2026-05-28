.PHONY: help install dev test lint format clean build publish

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv sync

dev: ## Install with development dependencies
	uv sync --extra dev
	uv run pre-commit install

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=gmail --cov-report=html --cov-report=term

lint: ## Run linting
	uv run flake8 gmail/
	uv run mypy gmail/

format: ## Format code
	uv run black .
	uv run isort .

format-check: ## Check code formatting
	uv run black --check .
	uv run isort --check-only .

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

build: ## Build the package
	uv build

publish: ## Publish to PyPI
	uv publish

run: ## Run gmail with example config
	uv run gmail --help

example: ## Show example usage
	@echo "Example usage:"
	@echo "  uv run gmail --credentials credentials.json tail --tail"
	@echo "  uv run gmail tail --from 'noreply@github.com' --tail"
	@echo "  uv run gmail send --to a@b.com --subject Hi --body hello"
	@echo "  uv run gmail --config-file gmail.yaml tail"
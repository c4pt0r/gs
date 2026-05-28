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
	uv run pytest --cov=gs --cov-report=html --cov-report=term

lint: ## Run linting
	uv run flake8 gs/
	uv run mypy gs/

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

run: ## Run gs with example config
	uv run gs --help

example: ## Show example usage
	@echo "Example usage:"
	@echo "  uv run gs auth login --credentials credentials.json"
	@echo "  uv run gs gmail tail --from 'noreply@github.com' --tail"
	@echo "  uv run gs gmail send --to a@b.com --subject Hi --body hello"
	@echo "  uv run gs calendar events --from today --to +7d"
	@echo "  uv run gs drive ls"
# Changelog

All notable changes to StackSense will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **New providers**: Google Gemini, Mistral, Cohere, DeepSeek support with auto-detection and token extraction
- **Decorator API**: `@stacksense.track()` for tracking any function as an API call
- **Framework middleware**: FastAPI, Flask, and Django middleware for automatic request-level tracking
- **Export system**: Export metrics to CSV and JSON via `Exporter` class
- **Alerts & webhooks**: `AlertManager` with configurable rules, cooldowns, webhook dispatch, and callbacks
- **CLI tool**: `stacksense` command with `dashboard`, `status`, `export`, and `db` subcommands
- **`py.typed` marker**: PEP 561 compliance for downstream type checking
- **Pre-commit config**: Black, isort, flake8, and standard hooks

### Changed
- **Updated pricing**: All model prices updated to 2025 rates (GPT-4o, o1, o3, Claude 4, Gemini 2.0, Mistral, Cohere, DeepSeek)
- **Improved provider detection**: `_detect_provider` now supports Google, Mistral, Cohere, DeepSeek clients
- **Improved model parsing**: `parse_model_name` recognizes new model families

### Fixed
- `AgentRun.to_dict()` referenced `self.metadata` instead of `self.run_metadata`
- Main `__init__.py` had duplicate subpackage content and wrong `__author__`

## [0.1.0] - 2024-12-01

### Added
- Initial release
- Core SDK with `StackSense` client and `monitor()` API
- Automatic tracking for OpenAI, Anthropic, ElevenLabs, Pinecone
- Sync and async client proxies with streaming support
- `MetricsTracker` for token, cost, and latency tracking
- `Analytics` engine with summaries, cost breakdown, performance stats
- Database persistence with SQLite (default) and PostgreSQL
- AI Gateway with smart routing, semantic caching, throttling, cost prediction
- Enterprise features: budgets, SLA routing, policies, agent tracking, governance
- Flask web dashboard (optional dependency)
- CI/CD with GitHub Actions
- Docker deployment support

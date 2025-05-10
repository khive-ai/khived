# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.6] - 2025-05-01

### Fixed

- **ClientSession lifecycle**: Removed unnecessary
  `async with self.client as session` wrapper in `_call_aiohttp` method,
  preventing premature session closure
- **API key validation**: Added fail-fast validation for missing API keys to
  prevent cryptic errors later
- **SecretStr handling**: Improved handling of SecretStr in `create_payload`
  method
- **Ollama configuration**: Replaced "mock_key" with explicit
  DUMMY_OLLAMA_API_KEY constant and added warning when real key is provided
- **CacheConfig integration**: Added `as_kwargs()` helper to CacheConfig and
  updated `@cached` decorator to use it
- **Singleton hook**: Added singleton instance reference to AppSettings class
- **OpenAI models management**: Added documentation for generated models and
  updated .gitignore to exclude the generated file
- **Race condition fix**: Improved API key resolution to handle concurrent
  startups
- **Resource leak prevention**: Added proper response release in finally block
  to prevent leaks during cancellation
- **Serialization improvement**: Removed unserialisable lambdas from
  CacheConfig.as_kwargs() to prevent pickle errors
- **Backoff improvement**: Moved backoff decorator inside methods to reference
  runtime config
- **Response handling**: Improved response handling to ensure proper cleanup

### Added

- **Graceful shutdown**: Added `aclose()` method to Endpoint class for proper
  client session cleanup
- **Environment variables**: Added KHIVE_OLLAMA_API_KEY to .env.example
- **Tests**: Added comprehensive tests for API key handling, ClientSession
  lifecycle, and cache configuration
- **Build configuration**: Added MANIFEST.in and package_data configuration to
  ensure generated files are included in the wheel
- **Test markers**: Added integration test markers to separate unit and
  integration tests

## [0.1.5] - 2025-04-15

Initial release with basic functionality.

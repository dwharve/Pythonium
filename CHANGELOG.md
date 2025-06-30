# Changelog

All notable changes to Pythonium will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-06-30

### Changed
- Updated all documentation to reflect current implementation
- Corrected command examples to use proper entry points (`pythonium` command vs `python pythonium.py`)
- Updated version information across all documentation files
- Improved installation and usage instructions

### Documentation
- Updated USER_GUIDE.md with correct command syntax
- Updated API_DOCUMENTATION.md version information
- Updated DEVELOPER_GUIDE.md with current date
- Updated TOOL_DEVELOPMENT_GUIDE.md version
- Updated AI_AGENT_RULES.md version

### Fixed
- Corrected entry point documentation throughout docs
- Fixed MCP server configuration examples

## [0.1.0] - 2025-06-26

### Added
- Initial release of Pythonium MCP server
- Core plugin framework architecture
- Manager system (Configuration, Plugin, Resource, Security)
- Tool categories (filesystem, network, system)
- MCP protocol implementation with stdio transport
- Comprehensive test suite (78 tests, 77 passing)

### Features
- Modular plugin-based architecture
- Dynamic tool discovery and loading
- Configuration management with multiple formats
- Security and resource management
- Full MCP protocol compliance

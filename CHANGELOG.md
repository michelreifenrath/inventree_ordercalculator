# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Optional Parts Support**: Full integration with InvenTree's BOM optional field functionality
  - Added `is_optional` field to `BomItemData` and `CalculatedPart` models
  - Automatic extraction of optional status from InvenTree BOM API responses
  - Optional status propagation through calculator logic and quantity calculations
  
- **Enhanced User Interfaces**:
  - **CLI**: New `--hide-optional-parts` command-line flag to filter optional parts from output tables
  - **Streamlit UI**: "Show Optional Parts" toggle switch in Display Options section
  - **Optional Column**: New "Optional" column in both Parts to Order and Assemblies to Build tables
  - Checkbox-style indicators (☑/☐) in Streamlit interface for better visual clarity
  - Text symbols (✓/✗) in CLI output for optional status indication

- **Filtering Capabilities**:
  - Optional parts can be hidden from output while maintaining full calculation accuracy
  - Filtering order: Consumables → HAIP Solutions → Optional parts
  - Backward compatibility with InvenTree instances that don't support optional fields

- **Comprehensive Testing**:
  - Unit tests for optional parts filtering logic in calculator module
  - CLI tests for `--hide-optional-parts` functionality
  - Streamlit UI tests for optional parts toggle and display
  - API client tests for optional field extraction from InvenTree responses

- **Documentation Updates**:
  - Updated README.md with detailed optional parts feature documentation
  - Added technical documentation for optional column implementation
  - Created implementation plans for optional parts hiding functionality
  - Updated user documentation with filtering examples and usage instructions

### Changed
- **Table Layout**: Repositioned Optional column after Part ID for immediate visibility
- **API Integration**: Enhanced BOM data extraction to include optional field information
- **Calculator Logic**: Modified to preserve optional status throughout calculation pipeline
- **UI Consistency**: Standardized optional parts display across CLI and Streamlit interfaces

### Technical Details
- **Models**: Extended `BomItemData` and `CalculatedPart` with `is_optional: bool` field
- **API Client**: Updated to extract optional field from InvenTree BOM API responses
- **Calculator**: Modified to propagate optional status through calculation logic
- **CLI**: Added typer option for `--hide-optional-parts` with help documentation
- **Streamlit**: Implemented session state management for optional parts toggle
- **Tests**: Added comprehensive test coverage for all optional parts functionality

### Dependencies
- No new dependencies added
- Maintained compatibility with existing InvenTree API versions
- Backward compatible with InvenTree instances without optional field support

### Breaking Changes
- None. All changes are backward compatible.

### Migration Notes
- Existing InvenTree instances without optional field support will show all parts as required (✗)
- No configuration changes required for existing installations
- Optional parts feature works automatically with InvenTree instances that support BOM optional fields

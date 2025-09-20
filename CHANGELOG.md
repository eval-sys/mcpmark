# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v1.2.0 - 2025-09-20

This version includes multiple important feature enhancements, particularly improvements in cost calculation, error handling, and Notion integration. Added per-model cost calculation, comprehensive aggregator functionality, and more robust error recovery mechanisms.
### ✨ Features
- **Add 1m parameter & improve log** (#198) - Added 1-minute parameter option and enhanced logging functionality
- **Refine Notion parent resolution and duplicate recovery** (#197) - Improved Notion parent page resolution and duplicate content recovery mechanism
- **Comprehensive aggregator, enable push to new branch** (#185) - Implemented comprehensive aggregator functionality with support for pushing to new branches
- **Support price cost calculating per model** (#186) - Added per-model price cost calculation functionality
- **Improve agent end log** (#183) - Enhanced agent end logging
- **Improve litellm error handling** (#181) - Enhanced LiteLLM error handling mechanism

### ♻️ Refactoring
- **Use notion child block list to locate page** (#196) - Refactored page location logic to use Notion child block list approach

### 🐛 Bug Fixes
- **Fix verification in Notion task company_in_a_box/goals_restructure** (#194) - Fixed verification logic for specific Notion tasks
- **Improve claude error handling** (#195) - Improved error handling for Claude API interactions
- **Fix tailing slash issue for find_legacy_name** - Resolved trailing slash issues in find_legacy_name path handling
- **Recover when duplication lands on parent** (#189) - Fixed recovery mechanism when duplicate content affects parent pages
- **Correctly handle playwright parser** (#184) - Properly handle Playwright parser
- **Handle timeout error, add timeout error for resuming** (#182) - Handle timeout errors and add timeout error handling for resume operations

### 📝 Documentation
- **Better readme, notion language guide** (#190) - Improved README documentation and added comprehensive Notion language guide

### 🔨 Maintenance
- **Update price info** (#188) - Updated pricing information
- **Update desktop_template/file_arrangement/verify.py** (#187) - Maintenance updates to verification scripts

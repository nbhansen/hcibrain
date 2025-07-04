# CLI Configuration Integration Plan

## Project Status
- **Current Phase**: Week 1 Architectural Improvements
- **Component**: CLI Configuration Integration
- **Priority**: Medium (Task 7 in Week 1 plan)
- **Goal**: Expose key configuration options as CLI arguments

## Current State Analysis

### Existing Infrastructure
- ✅ **Configuration Service**: Centralized config at `src/hci_extractor/core/config.py`
- ✅ **Environment Variables**: HCI_* prefix support implemented
- ✅ **CLI Commands**: `extract`, `batch`, `export`, `validate`, `parse` commands exist
- ✅ **Configuration Classes**: RetryConfig, LLMConfig, ExtractorConfig available
- ❌ **Integration Gap**: CLI commands don't expose configuration as arguments

### Architecture Principles to Maintain
- **Immutability**: Configuration objects are frozen dataclasses
- **Type Safety**: All configuration values properly typed and validated
- **Event-Driven**: Configuration changes should publish events if needed
- **Precedence**: CLI args > Environment vars > Config file > Defaults

## Implementation Plan

### Phase 1: Configuration Option Mapping
**Goal**: Define which configuration options should be exposed as CLI arguments

#### High Priority Options (Core Operations)
```bash
--chunk-size INT          # Text processing chunk size
--timeout FLOAT           # LLM request timeout in seconds  
--max-retries INT         # Maximum retry attempts
--retry-delay FLOAT       # Initial retry delay in seconds
--max-concurrent INT      # Maximum concurrent operations (batch)
```

#### Medium Priority Options (LLM Settings)
```bash
--llm-provider CHOICE     # LLM provider (gemini, openai, etc.)
--model-name STRING       # Specific model to use
--temperature FLOAT       # LLM temperature setting
--max-tokens INT          # Maximum tokens per request
```

#### Low Priority Options (Advanced)
```bash
--log-level CHOICE        # Logging level (DEBUG, INFO, WARN, ERROR)
--event-publishing BOOL   # Enable/disable event publishing
--config-file PATH        # Path to custom configuration file
```

### Phase 2: CLI Architecture Enhancement
**Goal**: Extend CLI parsing to handle configuration options

#### Implementation Strategy
1. **Argument Parser Extension**: Add configuration arguments to each CLI command
2. **Configuration Override System**: Implement proper precedence handling
3. **Validation Integration**: Use existing configuration classes for validation
4. **Help Documentation**: Auto-generate help text from configuration descriptions

#### Configuration Builder Pattern
```python
class ConfigurationBuilder:
    def __init__(self, base_config: ExtractorConfig):
        self._base_config = base_config
        self._overrides = {}
    
    def apply_cli_args(self, args: argparse.Namespace) -> ExtractorConfig:
        """Build new config with CLI overrides maintaining immutability."""
        # Implementation details
        pass
    
    def with_retry_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Fluent interface for building configuration."""
        pass
```

### Phase 3: Command-Specific Integration
**Goal**: Integrate configuration options into each CLI command

#### Per-Command Examples
```bash
# extract command
extract --chunk-size 8192 --timeout 30 --max-retries 3 paper.pdf

# batch command  
batch --max-concurrent 5 --retry-delay 2.0 papers/ results/

# export command
export --log-level DEBUG results/ --format csv

# validate command
validate --timeout 10 papers/
```

#### Command Class Extension
```python
class ExtractCommand:
    def add_config_arguments(self, parser: argparse.ArgumentParser):
        config_group = parser.add_argument_group('Configuration Options')
        
        # Core processing options
        config_group.add_argument('--chunk-size', type=int, 
                                help='Text processing chunk size')
        config_group.add_argument('--timeout', type=float,
                                help='LLM request timeout in seconds')
        config_group.add_argument('--max-retries', type=int,
                                help='Maximum retry attempts')
        
        # LLM options
        config_group.add_argument('--llm-provider', choices=['gemini', 'openai'],
                                help='LLM provider to use')
        config_group.add_argument('--model-name', type=str,
                                help='Specific model name')
```

### Phase 4: Configuration Merger Implementation
**Goal**: Create robust configuration merging with proper precedence

#### Merger Function
```python
def merge_configurations(
    base_config: ExtractorConfig,
    cli_args: argparse.Namespace,
    env_vars: Dict[str, str]
) -> ExtractorConfig:
    """
    Merge configurations with proper precedence.
    
    Precedence (highest to lowest):
    1. CLI arguments (explicit user intent)
    2. Environment variables (session configuration)
    3. Configuration file (persistent settings)
    4. Default values (fallback)
    """
    # Implementation details
    pass
```

#### Precedence Rules
1. **CLI Arguments**: Highest priority - explicit user intent
2. **Environment Variables**: Medium priority - session configuration
3. **Configuration File**: Low priority - persistent settings
4. **Default Values**: Fallback when nothing else specified

### Phase 5: Backward Compatibility & Documentation
**Goal**: Ensure existing workflows continue to work

#### Compatibility Measures
- **Default Behavior**: All CLI options have sensible defaults
- **Environment Variable Support**: Existing HCI_* variables continue to work
- **Configuration File Support**: Existing config files remain functional
- **Help Documentation**: Comprehensive help text showing all options and sources

## Implementation Steps

### Step 1: Extend CLI Command Classes
- Add configuration argument parsing to each command
- Implement argument validation using existing configuration classes
- Create help text generation from configuration metadata

### Step 2: Create Configuration Merger
- Implement configuration precedence logic
- Ensure immutability is maintained (return new config objects)
- Add comprehensive validation and error handling

### Step 3: Integration Points
- **Error Handling**: Validate CLI arguments using existing configuration validation
- **Type Safety**: Ensure CLI arguments are properly typed and validated
- **Documentation**: Auto-generate help text from configuration class docstrings
- **Testing**: Comprehensive tests for all configuration combinations

### Step 4: Command Line Interface Examples
```bash
# Basic usage (uses defaults)
python -m hci_extractor extract paper.pdf

# With configuration options
python -m hci_extractor extract \
    --chunk-size 10000 \
    --timeout 45 \
    --max-retries 5 \
    --llm-provider gemini \
    --model-name gemini-1.5-flash \
    paper.pdf

# Batch processing with concurrency control
python -m hci_extractor batch \
    --max-concurrent 3 \
    --retry-delay 1.5 \
    --timeout 60 \
    papers/ results/

# Environment variable integration
export HCI_CHUNK_SIZE=8192
export HCI_MAX_RETRIES=3
python -m hci_extractor extract paper.pdf  # Uses env vars

# Configuration file + CLI override
python -m hci_extractor extract \
    --config-file research_config.yaml \
    --max-retries 10 \  # Override config file setting
    paper.pdf
```

## Success Criteria

### Functionality Requirements
1. ✅ All key configuration options accessible via CLI
2. ✅ Proper precedence: CLI args > Environment vars > Config file > Defaults
3. ✅ All CLI arguments properly validated using existing configuration classes
4. ✅ Comprehensive help text for all options showing sources and defaults
5. ✅ Backward compatibility - existing workflows continue to work
6. ✅ 100% test coverage for configuration integration

### Quality Requirements
1. **Type Safety**: All configuration values properly typed
2. **Immutability**: Configuration objects remain frozen
3. **Event Integration**: Configuration changes publish events when appropriate
4. **Error Handling**: Clear error messages for invalid configuration combinations
5. **Documentation**: Help text explains precedence and provides examples

## Implementation Timeline

### Immediate (This Week)
1. **Phase 1**: Define configuration option mapping
2. **Step 1**: Add core configuration arguments to `extract` and `batch` commands
3. **Step 2**: Implement configuration merger with proper precedence
4. **Documentation**: Update help text for new options

### Short-term (Next Week)
1. **Phase 3**: Extend to `export` and `validate` commands
2. **Advanced Options**: Add medium and low priority configuration options
3. **Testing**: Comprehensive test suite for all configuration combinations

### Medium-term (Following Week)
1. **Phase 5**: Configuration file support enhancements
2. **Auto-generation**: Help text generated from configuration class metadata
3. **Performance**: Optimize configuration loading and validation
4. **Integration**: Complete integration with existing retry handler and event system

## Files to Modify

### Primary Files
- `src/hci_extractor/cli/commands.py` - Add configuration arguments
- `src/hci_extractor/core/config.py` - Extend configuration merger
- `src/hci_extractor/cli/main.py` - Integrate configuration loading

### Supporting Files
- `tests/test_cli_configuration.py` - Comprehensive configuration tests
- `src/hci_extractor/utils/config_merger.py` - Configuration merging utilities
- `DEVELOPER_GUIDE.md` - Update with CLI configuration documentation

## Risk Assessment

### Low Risk
- **Backward Compatibility**: Existing workflows use defaults
- **Type Safety**: Leveraging existing configuration validation
- **Testing**: Building on established test patterns

### Medium Risk
- **Configuration Complexity**: Multiple precedence levels to manage
- **CLI Argument Validation**: Ensuring consistency with configuration classes
- **Help Text Generation**: Auto-generating meaningful help text

### Mitigation Strategies
- **Incremental Implementation**: Start with core options, add advanced options later
- **Comprehensive Testing**: Test all precedence combinations
- **Documentation**: Clear examples and troubleshooting guides

## Dependencies

### Internal Dependencies
- ✅ Configuration service (`src/hci_extractor/core/config.py`)
- ✅ Event system (`src/hci_extractor/core/events.py`)
- ✅ Retry handler (`src/hci_extractor/utils/retry_handler.py`)
- ✅ Existing CLI commands structure

### External Dependencies
- `argparse` (Python standard library)
- `typing` (Python standard library)
- No additional external dependencies required

## Next Actions

1. **Start Phase 1**: Define specific configuration options to expose
2. **Analyze Current CLI**: Examine existing command structure and argument parsing
3. **Create Configuration Builder**: Implement the configuration merger pattern
4. **Add Tests**: Create comprehensive test suite for configuration integration
5. **Update Documentation**: Document new CLI options and usage patterns

This plan maintains the project's architectural principles while adding the requested CLI configuration capabilities in a structured, testable manner.
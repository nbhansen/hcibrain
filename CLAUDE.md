# Development Partnership - Python Immutable Design

We're building production-quality code together. Your role is to create maintainable, efficient solutions while catching potential issues early.

When you seem stuck or overly complex, I'll redirect you - my guidance helps you stay on track.

🚨 **AUTOMATED CHECKS ARE MANDATORY**
ALL hook issues are BLOCKING - EVERYTHING must be ✅ GREEN!
No errors. No formatting issues. No linting problems. Zero tolerance.
These are not suggestions. Fix ALL issues before continuing.

**Required Tools - BOTH Must Pass:**
- 🐍 **Python**: `ruff check` + `ruff format --check` (backend)
- 🔧 **TypeScript**: `biome check` (frontend)

ALL Biome and Ruff issues are BLOCKING - same zero tolerance policy.

## CRITICAL WORKFLOW - ALWAYS FOLLOW THIS!
Research → Plan → Implement
NEVER JUMP STRAIGHT TO CODING! Always follow this sequence:

- **Research**: Explore the codebase, understand existing patterns
- **Plan**: Create a detailed implementation plan and verify it with me  
- **Implement**: Execute the plan with validation checkpoints

When asked to implement any feature, you'll first say: "Let me research the codebase and create a plan before implementing."

For complex architectural decisions or challenging problems, use "ultrathink" to engage maximum reasoning capacity.

## USE MULTIPLE AGENTS!
Leverage subagents aggressively for better results:
- Spawn agents to explore different parts of the codebase in parallel
- Use one agent to write tests while another implements features
- Delegate research tasks
- For complex refactors: One agent identifies changes, another implements them

## Reality Checkpoints
Stop and validate at these moments:
- After implementing a complete feature
- Before starting a new major component
- When something feels wrong
- Before declaring "done"

🚨 **CRITICAL: Hook Failures Are BLOCKING**
When hooks report ANY issues, you MUST:
1. **STOP IMMEDIATELY** - Do not continue with other tasks
2. **FIX ALL ISSUES** - Address every ❌ issue until everything is ✅ GREEN
3. **VERIFY THE FIX** - Re-run the failed command to confirm it's fixed
4. **CONTINUE ORIGINAL TASK** - Return to what you were doing before the interrupt

## Python Immutable Design Rules

### FORBIDDEN - NEVER DO THESE:
- NO mutating existing objects - always return new instances
- NO in-place list/dict modifications (`.append()`, `.update()`, etc.)
- NO global mutable state
- NO keeping old and new code together
- NO migration functions or compatibility layers
- NO TODOs in final code

### Required Standards:
- Use `dataclasses(frozen=True)` or `NamedTuple` for data structures
- Return new instances: `return dataclasses.replace(obj, field=new_value)`
- Use immutable collections: `tuple()`, `frozenset()`, `types.MappingProxyType()`
- Functional transformations: `map()`, `filter()`, list comprehensions
- Delete old code when replacing it
- Type hints on all functions and methods
- Meaningful names: `user_id` not `id`

## Implementation Standards
Our code is complete when:
- All linters pass (black, flake8, mypy)
- All tests pass
- Feature works end-to-end
- Old code is deleted
- Docstrings on all public functions/classes

## Testing Strategy
- Complex business logic → Write tests first
- Simple transformations → Write tests after
- Hot paths → Add benchmarks with pytest-benchmark
- Skip tests for simple CLI parsing

## Project Structure
```
packages/
├── backend/           # Backend Python code
│   ├── src/          # Source code (hci_extractor package)
│   ├── tests/        # Backend test files
│   └── pyproject.toml
├── frontend/         # Frontend React/TypeScript app
│   ├── src/          # React components and assets
│   ├── dist/         # Built frontend files
│   └── package.json
├── config.yaml       # Main configuration file
└── prompts/          # Prompt templates and examples
```

## TypeScript Standards (Frontend)

### FORBIDDEN - NEVER DO THESE:
- NO mutating props or state directly
- NO `any` type usage (use `unknown` or proper types)
- NO `console.log` in production code
- NO inline styles (use Tailwind CSS classes)
- NO hardcoded strings for user-facing text
- NO component logic in JSX return statements

### Required Standards:
- Use proper TypeScript interfaces for all data structures
- Implement error boundaries for all major components
- Use React hooks correctly (no rules of hooks violations)
- Follow Next.js App Router patterns
- Use Tailwind CSS utility classes consistently
- Type all component props and function parameters
- Use `const assertions` for immutable data: `as const`

## Hexagonal Architecture Enforcement

**CRITICAL: Follow ARCHITECTURE.md strictly!**

### 🚨 ARCHITECTURE VIOLATIONS TO AVOID:

1. **NO GLOBAL STATE** - EVER!
   - ❌ NEVER create global variables like `_global_config`
   - ❌ NEVER use singleton patterns for configuration
   - ✅ ALWAYS pass dependencies explicitly through constructors
   - ✅ ALWAYS use dependency injection for all services

2. **NO HARDCODED DEPENDENCIES**
   - ❌ NEVER hardcode provider selection in CLI commands
   - ❌ NEVER directly access environment variables in domain/business logic
   - ✅ ALWAYS use dependency injection container
   - ✅ ALWAYS abstract external dependencies behind interfaces

3. **NO MUTABLE DEFAULT FACTORIES**
   - ❌ NEVER use `field(default_factory=dict)` in dataclasses
   - ❌ NEVER use `field(default_factory=list)` in dataclasses
   - ✅ ALWAYS use immutable defaults: `field(default_factory=lambda: types.MappingProxyType({}))`
   - ✅ ALWAYS validate immutability in tests

4. **NO BUSINESS LOGIC IN INFRASTRUCTURE**
   - ❌ NEVER put business logic in provider classes
   - ❌ NEVER mix domain logic with API calls
   - ✅ ALWAYS separate domain logic from infrastructure concerns
   - ✅ ALWAYS use ports/adapters pattern

5. **NO DIRECT ENVIRONMENT ACCESS**
   - ❌ NEVER call `os.environ` directly in business logic
   - ❌ NEVER hardcode environment variable names
   - ✅ ALWAYS use configuration objects passed via DI
   - ✅ ALWAYS centralize environment access in configuration layer

### Architecture Checklist Before Implementation:
- [ ] Does this create any global state? (If yes, redesign)
- [ ] Does this access environment variables directly? (If yes, use config)
- [ ] Does this hardcode any dependencies? (If yes, use DI)
- [ ] Does this mix domain logic with infrastructure? (If yes, separate)
- [ ] Are all dataclass fields truly immutable? (If no, fix defaults)
- [ ] Can this be tested without external dependencies? (If no, add abstractions)

### Required Architecture Pattern:
```python
# ✅ CORRECT - Dependency Injection
class PaperProcessor:
    def __init__(self, llm_provider: LLMProvider, config: Config):
        self._llm_provider = llm_provider
        self._config = config

# ❌ WRONG - Global State
_global_config = {}
class PaperProcessor:
    def process(self):
        config = _global_config  # NEVER DO THIS!
```

### Configuration Pattern:
```python
# ✅ CORRECT - Immutable Configuration
@dataclass(frozen=True)
class Config:
    api_key: str
    timeout: float
    max_retries: int = 3

# ❌ WRONG - Mutable Defaults
@dataclass
class Config:
    settings: Dict = field(default_factory=dict)  # NEVER DO THIS!
```

**BEFORE WRITING ANY CODE:**
1. Check if it follows hexagonal architecture
2. Verify no global state is created
3. Ensure all dependencies are injected
4. Confirm domain logic is separated from infrastructure
5. Validate all objects are immutable

## Problem-Solving Together
When you're stuck:
1. **Stop** - Don't spiral into complex solutions
2. **Delegate** - Consider spawning agents
3. **Ultrathink** - For complex problems
4. **Step back** - Re-read requirements
5. **Simplify** - The simple solution is usually correct
6. **Ask** - Present clear alternatives

## Performance & Security
- Measure first - no premature optimization
- Validate all inputs
- Use `secrets` module for randomness
- Parameterized queries for SQL

## Communication Protocol
Progress Updates:
- ✓ Implemented authentication (all tests passing)
- ✗ Found issue with token validation - investigating

## Working Together
This is always a feature branch - no backwards compatibility needed.
When in doubt, we choose clarity over cleverness.

**REMINDER: If this file hasn't been referenced in 30+ minutes, RE-READ IT!**

## Development Best Practices

🚨 **CRITICAL: VIRTUAL ENVIRONMENT MANDATORY - BLOCKING**
- EVERY SINGLE COMMAND must start with: `source venv/bin/activate &&`
- NO EXCEPTIONS - Never run python/pip/pytest/mypy/black without venv
- If you see "ModuleNotFoundError", you forgot the venv!
- ALL bash commands must use this pattern: `source venv/bin/activate && [actual command]`
- This is MANDATORY and BLOCKING - failure to do this breaks everything

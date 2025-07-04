# Development Quick Reference

## 🚀 Essential Commands

```bash
# Setup (first time)
source venv/bin/activate    # NEVER FORGET!
make setup                  # Complete environment setup

# Daily development  
make test-quick            # Fast tests
make lint                  # Code quality
make run ARGS="--help"     # Test CLI

# Before committing
make test                  # Full tests with coverage
make lint                  # Fix formatting issues
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `src/hci_extractor/models/pdf_models.py` | All data structures |
| `src/hci_extractor/extractors/pdf_extractor.py` | PDF → text conversion |
| `src/hci_extractor/llm/gemini_provider.py` | Gemini API integration |
| `src/hci_extractor/main.py` | CLI interface |
| `CLAUDE.md` | Core principles & architecture |
| `PHASE2_PLAN.md` | Current implementation roadmap |

## 🧪 Testing Hierarchy

```bash
python scripts/test.py     # Fastest - component smoke tests
make test-quick           # Fast - pytest without coverage  
make test                 # Complete - pytest with coverage
```

## 🔧 Code Patterns

### Data Model Template
```python
@dataclass(frozen=True)
class MyModel:
    field: str
    optional_field: Optional[int] = None
    
    def __post_init__(self) -> None:
        if not self.field:
            raise ValueError("Field cannot be empty")
    
    @classmethod
    def create_with_auto_id(cls, field: str) -> "MyModel":
        return cls(field=field)
```

### LLM Provider Template
```python
class MyProvider(LLMProvider):
    async def analyze_section(self, text: str, section_type: str) -> List[Dict]:
        response = await self._retry_with_backoff(self._make_api_request, text)
        return self._parse_response(response)
    
    def validate_response(self, response: Dict) -> bool:
        # Validation logic
        return True
```

## 🚨 Critical Rules

1. **Always `source venv/bin/activate`** before any Python work
2. **Never mutate objects** - create new ones instead
3. **Always `@dataclass(frozen=True)`** for data models
4. **Use `tuple` not `list`** in immutable classes
5. **Extract verbatim** - never paraphrase or summarize
6. **Type hint everything** - helps catch errors early

## 🐛 Debug Checklist

- [ ] Virtual environment activated?
- [ ] Dependencies installed? (`make install`)
- [ ] Imports working? (`python scripts/test.py`)
- [ ] Type errors? (`mypy src/`)
- [ ] Code formatted? (`make lint`)

## 📊 Project Status

**✅ Phase 1 Complete:** PDF extraction, text normalization, section detection, CLI  
**✅ Phase 2 (3/8 steps):** Data models, LLM abstraction, Gemini integration  
**🚧 Phase 2 Next:** Section prompts (Step 4), extraction pipeline (Step 5), testing (Step 8)  
**📋 Phase 3 Future:** Async processing, batch operations, production deployment

---

*Keep this handy while coding! 📌*
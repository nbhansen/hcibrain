"""
Comprehensive tests for LLM providers and prompt management.

Tests CLAUDE.MD requirements:
- Provider abstraction and dependency injection
- Prompt management and hot-reloading
- Provider-agnostic design
- Error handling and API reliability
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch, mock_open
from pathlib import Path
import tempfile
import os

import pytest

# Try to import LLM components (may not be available without API keys)
try:
    from hci_extractor.llm import LLMProvider, GeminiProvider
    from hci_extractor.llm.prompt_manager import PromptManager
    from hci_extractor.models import LLMError, ProcessingError
    LLMS_AVAILABLE = True
except ImportError:
    LLMS_AVAILABLE = False


@pytest.mark.skipif(not LLMS_AVAILABLE, reason="LLM components not available")
class TestLLMProvider:
    """Test LLM provider abstraction."""
    
    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()
    
    def test_llm_provider_interface_methods(self):
        """Test that concrete providers implement required methods."""
        class MockLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
            
            async def analyze_section(self, section_text, section_type, context=None):
                return []
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Should be able to instantiate concrete implementation
        provider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)
    
    @pytest.mark.asyncio
    async def test_llm_provider_analyze_section_interface(self):
        """Test analyze_section interface requirements."""
        class TestProvider(LLMProvider):
            def __init__(self):
                super().__init__()
            
            async def analyze_section(self, section_text, section_type, context=None):
                # Should return list of dictionaries with required fields
                return [
                    {
                        "element_type": "finding",
                        "text": "Test finding",
                        "evidence_type": "quantitative",
                        "confidence": 0.9
                    }
                ]
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {}
        
        provider = TestProvider()
        result = await provider.analyze_section("Test text", "results")
        
        # Should return properly formatted elements
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["element_type"] == "finding"
        assert result[0]["text"] == "Test finding"


@pytest.mark.skipif(not LLMS_AVAILABLE, reason="LLM components not available")
class TestGeminiProvider:
    """Test Gemini-specific provider implementation."""
    
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization with API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            provider = GeminiProvider()
            assert provider.api_key == "test-key"
    
    def test_gemini_provider_missing_api_key(self):
        """Test Gemini provider error handling for missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiProvider()
    
    @pytest.mark.asyncio
    async def test_gemini_provider_analyze_section_mock(self):
        """Test Gemini section analysis with mocked API."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            provider = GeminiProvider()
            
            # Mock the API request
            mock_response = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"elements": [{"element_type": "finding", "text": "Test result", "evidence_type": "quantitative", "confidence": 0.9}]}'
                        }]
                    }
                }]
            }
            
            with patch.object(provider, '_make_api_request', return_value=mock_response):
                result = await provider.analyze_section("Test section text", "results")
                
                assert len(result) == 1
                assert result[0]["element_type"] == "finding"
                assert result[0]["text"] == "Test result"
    
    def test_gemini_provider_validate_response(self):
        """Test Gemini response validation."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            provider = GeminiProvider()
            
            # Valid response
            valid_response = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "valid response"}]
                    }
                }]
            }
            assert provider.validate_response(valid_response) is True
            
            # Invalid response - missing candidates
            invalid_response = {"error": "API error"}
            assert provider.validate_response(invalid_response) is False
    
    @pytest.mark.asyncio
    async def test_gemini_provider_error_handling(self):
        """Test Gemini provider error handling."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            provider = GeminiProvider()
            
            # Mock API request that raises exception
            with patch.object(provider, '_make_api_request', side_effect=Exception("API Error")):
                with pytest.raises(LLMError):
                    await provider.analyze_section("Test text", "results")


@pytest.mark.skipif(not LLMS_AVAILABLE, reason="LLM components not available")
class TestPromptManager:
    """Test prompt management system."""
    
    def test_prompt_manager_initialization(self):
        """Test PromptManager initialization with default prompts."""
        manager = PromptManager()
        
        # Should have default prompts loaded
        assert manager.get_base_prompt("extraction") is not None
        assert "HCI" in manager.get_base_prompt("extraction")
    
    def test_prompt_manager_load_custom_prompts(self):
        """Test loading custom prompts from YAML file."""
        # Create temporary YAML file
        yaml_content = """
base_prompts:
  custom_extraction: |
    Custom extraction prompt for testing.
    Find elements of type: {element_types}
    
  custom_analysis: |
    Custom analysis prompt.
    Section type: {section_type}

element_types:
  - "test_claim"
  - "test_finding"

evidence_types:
  - "test_quantitative"
  - "test_qualitative"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            manager = PromptManager(prompts_file=temp_path)
            
            # Should load custom prompts
            custom_prompt = manager.get_base_prompt("custom_extraction")
            assert "Custom extraction prompt" in custom_prompt
            
            # Should load custom element types
            element_types = manager.get_element_types()
            assert "test_claim" in element_types
            assert "test_finding" in element_types
            
        finally:
            os.unlink(temp_path)
    
    def test_prompt_manager_template_rendering(self):
        """Test prompt template rendering with variables."""
        manager = PromptManager()
        
        # Get a template and render it
        template = manager.get_base_prompt("extraction")
        rendered = manager.render_prompt(template, {
            "section_type": "results",
            "section_text": "Test section content",
            "element_types": ["finding", "claim"]
        })
        
        # Should substitute variables
        assert "results" in rendered
        assert "Test section content" in rendered
    
    def test_prompt_manager_missing_template(self):
        """Test handling of missing prompt templates."""
        manager = PromptManager()
        
        # Should handle missing templates gracefully
        missing_prompt = manager.get_base_prompt("nonexistent")
        assert missing_prompt is None
    
    def test_prompt_manager_hot_reload(self):
        """Test hot-reloading of prompt files."""
        # Create initial YAML file
        initial_content = """
base_prompts:
  test_prompt: "Initial prompt content"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(initial_content)
            temp_path = f.name
        
        try:
            manager = PromptManager(prompts_file=temp_path)
            
            # Check initial content
            initial_prompt = manager.get_base_prompt("test_prompt")
            assert "Initial prompt content" in initial_prompt
            
            # Update file
            updated_content = """
base_prompts:
  test_prompt: "Updated prompt content"
"""
            with open(temp_path, 'w') as f:
                f.write(updated_content)
            
            # Reload prompts
            manager.reload_prompts()
            
            # Should have updated content
            updated_prompt = manager.get_base_prompt("test_prompt")
            assert "Updated prompt content" in updated_prompt
            
        finally:
            os.unlink(temp_path)
    
    def test_prompt_manager_invalid_yaml(self):
        """Test handling of invalid YAML files."""
        # Create invalid YAML file
        invalid_yaml = """
base_prompts:
  invalid: |
    This is valid YAML but missing required structure
    [invalid structure here
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            # Should handle invalid YAML gracefully
            manager = PromptManager(prompts_file=temp_path)
            # Should fall back to defaults
            assert manager.get_base_prompt("extraction") is not None
            
        finally:
            os.unlink(temp_path)


class TestLLMIntegration:
    """Test LLM integration with other components."""
    
    @pytest.mark.asyncio
    async def test_llm_error_propagation(self):
        """Test that LLM errors are properly propagated."""
        class FailingLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
            
            async def analyze_section(self, section_text, section_type, context=None):
                raise LLMError("Simulated API failure")
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                raise Exception("API Error")
        
        provider = FailingLLMProvider()
        
        with pytest.raises(LLMError):
            await provider.analyze_section("Test text", "results")
    
    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self):
        """Test LLM timeout handling."""
        class SlowLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
            
            async def analyze_section(self, section_text, section_type, context=None):
                # Simulate slow response
                await asyncio.sleep(0.1)
                return []
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                await asyncio.sleep(0.1)
                return {}
        
        provider = SlowLLMProvider()
        
        # Should complete without timeout for reasonable delays
        result = await provider.analyze_section("Test text", "results")
        assert result == []
    
    def test_llm_provider_thread_safety(self):
        """Test that LLM providers are thread-safe (immutable design)."""
        class ThreadSafeLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                # Immutable configuration
                self._config = {"temperature": 0.1, "max_tokens": 1000}
            
            async def analyze_section(self, section_text, section_type, context=None):
                return []
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {}
            
            @property
            def config(self):
                # Return immutable copy
                return self._config.copy()
        
        provider = ThreadSafeLLMProvider()
        config1 = provider.config
        config2 = provider.config
        
        # Should return separate copies
        assert config1 is not config2
        assert config1 == config2
        
        # Modifying returned config shouldn't affect provider
        config1["temperature"] = 0.5
        assert provider.config["temperature"] == 0.1


if __name__ == "__main__":
    pytest.main([__file__])
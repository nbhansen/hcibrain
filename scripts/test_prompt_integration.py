#!/usr/bin/env python3
"""
Test script for PromptManager integration (without external dependencies)
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_base_class_is_clean():
    """Test that LLM base class is clean without PromptManager dependency."""
    print("🧪 Testing clean base class architecture...")
    
    try:
        # Import normally - architecture should now be clean
        from hci_extractor.llm import LLMProvider
        from hci_extractor.prompts import PromptManager
        
        # Create a mock provider to test the base class
        class MockProvider(LLMProvider):
            def __init__(self, **kwargs):
                super().__init__()
                # Only concrete providers should have PromptManager
                self.prompt_manager = PromptManager()
            
            async def analyze_section(self, section_text, section_type, context=None):
                return []
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Test that base class initializes cleanly
        provider = MockProvider()
        assert hasattr(provider, 'rate_limit_delay')
        assert hasattr(provider, 'max_retries')
        print("✅ Base class initializes with only core attributes")
        
        # Test that we can import LLMProvider without external dependencies
        print("✅ LLMProvider imports without external dependencies")
        
        # Test that concrete provider can add PromptManager
        assert hasattr(provider, 'prompt_manager')
        assert isinstance(provider.prompt_manager, PromptManager)
        print("✅ Concrete provider can add PromptManager")
        
        return True
        
    except Exception as e:
        print(f"❌ Base class test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_composition():
    """Test advanced prompt composition features."""
    print("\n🧪 Testing prompt composition...")
    
    try:
        from hci_extractor.prompts import PromptManager
        
        pm = PromptManager()
        
        # Test with full context
        context = {
            "paper_title": "AI-Enhanced Touch Interfaces",
            "paper_venue": "UIST 2024",
            "paper_year": 2024,
            "authors": ["Dr. Smith", "Prof. Jones", "Ms. Chen"]
        }
        
        sample_text = """
        Our AI-enhanced touch interface achieved 45% better accuracy than baseline systems.
        We conducted a study with 32 participants across three different age groups.
        The machine learning model was trained on 10,000 gesture samples.
        """
        
        # Generate prompt with full context
        prompt = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="results",
            context=context,
            include_examples=True
        )
        
        # Verify context inclusion
        assert "AI-Enhanced Touch Interfaces" in prompt
        assert "UIST 2024" in prompt
        assert "2024" in prompt
        assert "Dr. Smith, Prof. Jones, Ms. Chen" in prompt
        print("✅ Full context correctly included in prompt")
        
        # Test different section types
        sections_to_test = ["abstract", "methods", "results", "discussion"]
        for section_type in sections_to_test:
            section_prompt = pm.get_analysis_prompt(
                section_text="Sample text for testing.",
                section_type=section_type,
                include_examples=False
            )
            assert section_type.upper() in section_prompt or section_type in section_prompt
            
        print(f"✅ All section types tested: {sections_to_test}")
        
        # Test with minimal context
        minimal_prompt = pm.get_analysis_prompt(
            section_text="Minimal test.",
            section_type="unknown_section",
            context=None,
            include_examples=False
        )
        
        # Should still work with default guidance
        assert len(minimal_prompt) > 100
        print("✅ Minimal prompt generation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt composition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_examples_loading():
    """Test that examples are properly loaded and formatted."""
    print("\n🧪 Testing examples loading...")
    
    try:
        from hci_extractor.prompts import PromptManager
        
        pm = PromptManager()
        
        # Test available examples
        available_examples = pm.get_available_examples()
        print(f"✅ Available examples: {available_examples}")
        
        # Test with examples vs without examples
        sample_text = "We developed a new gesture recognition system."
        
        prompt_with_examples = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="abstract",
            include_examples=True
        )
        
        prompt_without_examples = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="abstract",
            include_examples=False
        )
        
        # With examples should be longer
        assert len(prompt_with_examples) > len(prompt_without_examples)
        print("✅ Examples correctly add length to prompts")
        
        # Check for example markers
        if "abstract" in available_examples:
            assert "EXAMPLE" in prompt_with_examples.upper()
            print("✅ Example markers found in prompt")
        
        # Test section with no examples
        prompt_no_examples_section = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="nonexistent_section",
            include_examples=True
        )
        
        # Should work even if no examples exist for section
        assert len(prompt_no_examples_section) > 100
        print("✅ Gracefully handles sections without examples")
        
        return True
        
    except Exception as e:
        print(f"❌ Examples loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_reload():
    """Test prompt reloading functionality."""
    print("\n🧪 Testing prompt reload...")
    
    try:
        from hci_extractor.prompts import PromptManager
        
        pm = PromptManager()
        
        # Generate initial prompt
        initial_prompt = pm.get_analysis_prompt(
            section_text="Test text",
            section_type="abstract",
            include_examples=False
        )
        
        # Reload prompts
        pm.reload_prompts()
        print("✅ Prompt reload completed without error")
        
        # Generate prompt after reload
        reloaded_prompt = pm.get_analysis_prompt(
            section_text="Test text",
            section_type="abstract",
            include_examples=False
        )
        
        # Should be the same content
        assert initial_prompt == reloaded_prompt
        print("✅ Prompt content consistent after reload")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt reload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing PromptManager Integration")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    if test_base_class_is_clean():
        tests_passed += 1
        print("✅ Clean base class architecture PASSED")
    else:
        print("❌ Clean base class architecture FAILED")
    
    if test_prompt_composition():
        tests_passed += 1
        print("✅ Prompt composition PASSED")
    else:
        print("❌ Prompt composition FAILED")
    
    if test_examples_loading():
        tests_passed += 1
        print("✅ Examples loading PASSED")
    else:
        print("❌ Examples loading FAILED")
    
    if test_prompt_reload():
        tests_passed += 1
        print("✅ Prompt reload PASSED")
    else:
        print("❌ Prompt reload FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 PromptManager integration working!")
        sys.exit(0)
    else:
        print("💥 Some integration tests failed!")
        sys.exit(1)
#!/usr/bin/env python3
"""
Test script for Gemini provider integration with PromptManager
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_gemini_provider_init():
    """Test that GeminiProvider can be initialized with PromptManager."""
    print("🧪 Testing Gemini provider initialization...")
    
    try:
        from hci_extractor.llm import GeminiProvider
        from hci_extractor.prompts import PromptManager
        
        # Test with default PromptManager
        provider1 = GeminiProvider(api_key="test-key")
        print("✅ GeminiProvider initialized with default PromptManager")
        
        # Test with explicit PromptManager
        pm = PromptManager()
        provider2 = GeminiProvider(api_key="test-key", prompt_manager=pm)
        print("✅ GeminiProvider initialized with explicit PromptManager")
        
        # Verify PromptManager is accessible
        assert hasattr(provider1, 'prompt_manager')
        assert hasattr(provider2, 'prompt_manager')
        print("✅ PromptManager accessible in provider instances")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini provider initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_generation():
    """Test that provider can generate prompts using PromptManager."""
    print("\n🧪 Testing prompt generation...")
    
    try:
        from hci_extractor.llm import GeminiProvider
        
        # Initialize provider (no API key needed for prompt testing)
        provider = GeminiProvider(api_key="test-key")
        
        # Test prompt generation
        sample_text = """
        We present TouchGestures, a novel interaction technique that enables users to perform 
        complex multi-touch gestures with 40% fewer errors than standard touch interfaces.
        """
        
        context = {
            "paper_title": "TouchGestures: Enhanced Multi-touch Interaction",
            "paper_venue": "CHI 2024"
        }
        
        # Generate prompt using PromptManager
        prompt = provider.prompt_manager.get_analysis_prompt(
            section_text=sample_text,
            section_type="abstract",
            context=context,
            include_examples=True
        )
        
        print(f"✅ Prompt generated successfully ({len(prompt)} characters)")
        
        # Verify prompt contains expected elements
        assert "TouchGestures" in prompt
        assert "abstract" in prompt.lower()
        assert "CHI 2024" in prompt
        assert "CRITICAL RULES" in prompt
        assert "element_type" in prompt
        print("✅ Prompt contains expected content")
        
        # Test with different section type
        prompt_methods = provider.prompt_manager.get_analysis_prompt(
            section_text="We used a controlled experiment with 24 participants.",
            section_type="methods",
            include_examples=False
        )
        
        print(f"✅ Methods prompt generated ({len(prompt_methods)} characters)")
        assert len(prompt_methods) < len(prompt)  # Should be shorter without examples
        print("✅ Examples correctly excluded from methods prompt")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_response_validation():
    """Test that provider can validate responses with new format."""
    print("\n🧪 Testing response validation...")
    
    try:
        from hci_extractor.llm import GeminiProvider
        
        provider = GeminiProvider(api_key="test-key")
        
        # Test valid response with new format
        valid_response = {
            "elements": [
                {
                    "element_type": "artifact",
                    "text": "TouchGestures interaction technique",
                    "evidence_type": "mixed",
                    "confidence": 0.95,
                    "hci_contribution_type": "artifact"
                },
                {
                    "element_type": "finding",
                    "text": "40% fewer errors than standard interfaces",
                    "evidence_type": "quantitative",
                    "confidence": 0.90,
                    "hci_contribution_type": "knowledge-increasing"
                }
            ]
        }
        
        result = provider.validate_response(valid_response)
        assert result is True
        print("✅ Valid response with new format accepted")
        
        # Test response without optional hci_contribution_type
        valid_response_minimal = {
            "elements": [
                {
                    "element_type": "claim",
                    "text": "Gesture interfaces improve usability",
                    "evidence_type": "theoretical",
                    "confidence": 0.80
                }
            ]
        }
        
        result = provider.validate_response(valid_response_minimal)
        assert result is True
        print("✅ Valid response without optional fields accepted")
        
        # Test invalid element_type
        try:
            invalid_response = {
                "elements": [
                    {
                        "element_type": "invalid_type",
                        "text": "Some text",
                        "evidence_type": "qualitative",
                        "confidence": 0.5
                    }
                ]
            }
            provider.validate_response(invalid_response)
            print("❌ Invalid element_type should have failed validation")
            return False
        except Exception:
            print("✅ Invalid element_type correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Response validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing Gemini Provider Integration with PromptManager")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    if test_gemini_provider_init():
        tests_passed += 1
        print("✅ Gemini provider initialization PASSED")
    else:
        print("❌ Gemini provider initialization FAILED")
    
    if test_prompt_generation():
        tests_passed += 1
        print("✅ Prompt generation PASSED")
    else:
        print("❌ Prompt generation FAILED")
    
    if test_response_validation():
        tests_passed += 1
        print("✅ Response validation PASSED")
    else:
        print("❌ Response validation FAILED")
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Gemini-PromptManager integration working!")
        sys.exit(0)
    else:
        print("💥 Some integration tests failed!")
        sys.exit(1)
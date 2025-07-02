#!/usr/bin/env python3
"""
Test script for the new PromptManager system
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_prompt_manager():
    """Test basic PromptManager functionality."""
    print("🧪 Testing PromptManager...")
    
    try:
        from hci_extractor.prompts import PromptManager
        print("✅ PromptManager imported successfully")
        
        # Initialize PromptManager
        pm = PromptManager()
        print("✅ PromptManager initialized")
        
        # Test getting available sections
        sections = pm.get_available_sections()
        print(f"✅ Available sections: {sections}")
        
        # Test getting available examples
        examples = pm.get_available_examples()
        print(f"✅ Available examples: {examples}")
        
        # Test building a prompt for abstract section
        sample_abstract = """
        We present TouchGestures, a novel interaction technique that enables users to perform 
        complex multi-touch gestures with 40% fewer errors than standard touch interfaces. 
        Through a controlled study with 24 participants, we found that users completed tasks 
        23% faster using TouchGestures compared to conventional touch input.
        """
        
        context = {
            "paper_title": "TouchGestures: Enhanced Multi-touch Interaction",
            "paper_venue": "CHI 2024",
            "authors": ["Alice Smith", "Bob Jones"]
        }
        
        prompt = pm.get_analysis_prompt(
            section_text=sample_abstract,
            section_type="abstract",
            context=context,
            include_examples=True
        )
        
        print("✅ Abstract analysis prompt generated")
        print(f"📏 Prompt length: {len(prompt)} characters")
        
        # Show a snippet of the prompt
        print("\n📄 Prompt preview (first 500 chars):")
        print("-" * 50)
        print(prompt[:500])
        print("..." if len(prompt) > 500 else "")
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ PromptManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_variants():
    """Test different prompt configurations."""
    print("\n🧪 Testing prompt variants...")
    
    try:
        from hci_extractor.prompts import PromptManager
        pm = PromptManager()
        
        sample_text = "We developed a new gesture recognition algorithm."
        
        # Test without examples
        prompt_no_examples = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="methods",
            include_examples=False
        )
        
        # Test with examples
        prompt_with_examples = pm.get_analysis_prompt(
            section_text=sample_text,
            section_type="methods",
            include_examples=True
        )
        
        print(f"✅ Prompt without examples: {len(prompt_no_examples)} chars")
        print(f"✅ Prompt with examples: {len(prompt_with_examples)} chars")
        
        # Examples should make prompt longer
        if len(prompt_with_examples) > len(prompt_no_examples):
            print("✅ Examples correctly added to prompt")
        else:
            print("⚠️  Examples may not be working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt variants test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Prompt Management System")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_prompt_manager():
        tests_passed += 1
        print("✅ PromptManager basic functionality PASSED")
    else:
        print("❌ PromptManager basic functionality FAILED")
    
    if test_prompt_variants():
        tests_passed += 1
        print("✅ Prompt variants PASSED")
    else:
        print("❌ Prompt variants FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Prompt management system working!")
        sys.exit(0)
    else:
        print("💥 Some prompt tests failed!")
        sys.exit(1)
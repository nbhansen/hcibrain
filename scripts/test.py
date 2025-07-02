#!/usr/bin/env python3
"""
Quick test runner script for HCI Paper Extractor
Provides easy testing of core functionality without full pytest setup
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from hci_extractor.models import Paper, ExtractedElement, ExtractionResult
    from hci_extractor.extractors import PdfExtractor
    from hci_extractor.llm import GeminiProvider
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_data_models():
    """Test the immutable data models."""
    print("\n🧪 Testing data models...")
    
    try:
        # Test Paper creation
        paper = Paper.create_with_auto_id(
            title="Sample HCI Paper",
            authors=("Alice Smith", "Bob Jones"),
            venue="CHI 2024",
            year=2024
        )
        print(f"✅ Paper created: {paper.title}")
        
        # Test ExtractedElement creation
        element = ExtractedElement.create_with_auto_id(
            paper_id=paper.paper_id,
            element_type="finding",
            text="Users completed tasks 23% faster with the new interface",
            section="results",
            confidence=0.95,
            evidence_type="quantitative",
            page_number=5
        )
        print(f"✅ Element created: {element.element_type}")
        
        # Test ExtractionResult
        result = ExtractionResult(
            paper=paper,
            elements=(element,),
            extraction_metadata={"test": True}
        )
        print(f"✅ ExtractionResult created with {result.total_elements} elements")
        
        # Test immutability
        try:
            paper.title = "Modified Title"  # This should fail
            print("❌ Immutability test failed - object was modified")
        except AttributeError:
            print("✅ Immutability test passed - object cannot be modified")
            
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False
    
    return True


def test_pdf_extractor():
    """Test PDF extraction functionality."""
    print("\n🧪 Testing PDF extractor...")
    
    try:
        extractor = PdfExtractor()
        print("✅ PdfExtractor initialized")
        
        # Test validation method exists
        if hasattr(extractor, 'validate_extraction'):
            print("✅ Validation method available")
        else:
            print("❌ Validation method missing")
            return False
            
    except Exception as e:
        print(f"❌ PDF extractor test failed: {e}")
        return False
    
    return True


def test_llm_provider():
    """Test LLM provider functionality."""
    print("\n🧪 Testing LLM provider...")
    
    try:
        # Test that we can create a provider (without API key for testing)
        from hci_extractor.llm.base import LLMProvider
        print("✅ LLMProvider base class imported")
        
        # Test Gemini provider class (without instantiation)
        print("✅ GeminiProvider class imported")
        
        # Test error classes from unified hierarchy
        from hci_extractor.models import LLMError, RateLimitError, LLMValidationError
        print("✅ Error classes imported")
        
    except Exception as e:
        print(f"❌ LLM provider test failed: {e}")
        return False
    
    return True


def test_cli_import():
    """Test that CLI can be imported."""
    print("\n🧪 Testing CLI import...")
    
    try:
        from hci_extractor.main import cli
        print("✅ CLI imported successfully")
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all quick tests."""
    print("🚀 Running HCI Paper Extractor Quick Tests")
    print("=" * 50)
    
    tests = [
        ("Data Models", test_data_models),
        ("PDF Extractor", test_pdf_extractor),
        ("LLM Provider", test_llm_provider),
        ("CLI Import", test_cli_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
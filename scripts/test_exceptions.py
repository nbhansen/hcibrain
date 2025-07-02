#!/usr/bin/env python3
"""
Simple test for exception hierarchy consolidation
Tests import structure without requiring external dependencies
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_exception_imports():
    """Test that all exceptions can be imported from unified hierarchy."""
    print("🧪 Testing exception consolidation...")
    
    try:
        # Test base exceptions
        from hci_extractor.models import HciExtractorError, ProcessingError
        print("✅ Base exceptions imported")
        
        # Test LLM exceptions
        from hci_extractor.models import LLMError, RateLimitError, LLMValidationError
        print("✅ LLM exceptions imported")
        
        # Test PDF exceptions
        from hci_extractor.models import PdfError, PasswordProtectedError, CorruptedFileError
        print("✅ PDF exceptions imported")
        
        # Test data validation exceptions
        from hci_extractor.models import DataValidationError, ExtractionQualityError
        print("✅ Data validation exceptions imported")
        
        # Test exception hierarchy
        assert issubclass(LLMError, HciExtractorError)
        assert issubclass(PdfError, ProcessingError)
        assert issubclass(ProcessingError, HciExtractorError)
        print("✅ Exception hierarchy verified")
        
        # Test that old imports no longer work
        try:
            from hci_extractor.llm import LLMError as OldLLMError
            print("❌ Old LLM imports still working - consolidation incomplete")
            return False
        except ImportError:
            print("✅ Old LLM imports properly removed")
            
        return True
        
    except ImportError as e:
        print(f"❌ Exception import failed: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Exception hierarchy test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_models_import():
    """Test that data models can still be imported."""
    print("\n🧪 Testing data model imports...")
    
    try:
        from hci_extractor.models import Paper, ExtractedElement, ExtractionResult
        print("✅ Core data models imported")
        
        from hci_extractor.models import PdfContent, PdfPage, CharacterPosition
        print("✅ PDF data models imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Data model import failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Exception Consolidation (Phase A)")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_exception_imports():
        tests_passed += 1
        print("✅ Exception consolidation PASSED")
    else:
        print("❌ Exception consolidation FAILED")
    
    if test_models_import():
        tests_passed += 1
        print("✅ Data model imports PASSED")
    else:
        print("❌ Data model imports FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Phase A (Exception Consolidation) COMPLETE!")
        sys.exit(0)
    else:
        print("💥 Phase A validation failed!")
        sys.exit(1)
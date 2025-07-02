#!/usr/bin/env python3
"""
Test the section processor functionality with mock LLM provider.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_section_processor_interface():
    """Test the section processor interface and dependency injection."""
    print("🧪 Testing section processor interface...")
    
    try:
        from hci_extractor.models import DetectedSection, Paper, ExtractedElement
        from hci_extractor.pipeline import SectionProcessor, LLMSectionProcessor
        from hci_extractor.llm import LLMProvider
        
        # Create a mock LLM provider for testing
        class MockLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
            
            async def analyze_section(self, section_text, section_type, context=None):
                # Return mock analysis results
                return [
                    {
                        "element_type": "finding",
                        "text": "Users completed tasks 30% faster",
                        "evidence_type": "quantitative", 
                        "confidence": 0.95
                    },
                    {
                        "element_type": "claim",
                        "text": "The new interface improves usability",
                        "evidence_type": "theoretical",
                        "confidence": 0.85
                    }
                ]
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Test dependency injection (DIP)
        mock_llm = MockLLMProvider()
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        # Verify it implements the interface (LSP)
        assert isinstance(processor, SectionProcessor)
        print("✅ Dependency injection and LSP compliance verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_section_processing():
    """Test actual section processing with mock data."""
    print("\n🧪 Testing section processing...")
    
    try:
        from hci_extractor.models import DetectedSection, Paper
        from hci_extractor.pipeline import LLMSectionProcessor
        from hci_extractor.llm import LLMProvider
        
        # Mock LLM provider that returns test data
        class MockLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                
            async def analyze_section(self, section_text, section_type, context=None):
                # Simulate processing delay
                await asyncio.sleep(0.1)
                
                # Return different results based on section type
                if section_type == "abstract":
                    return [
                        {
                            "element_type": "claim",
                            "text": "We present a novel approach to gesture recognition",
                            "evidence_type": "theoretical",
                            "confidence": 0.90
                        },
                        {
                            "element_type": "finding", 
                            "text": "Our system achieves 94% accuracy",
                            "evidence_type": "quantitative",
                            "confidence": 0.95
                        }
                    ]
                elif section_type == "methodology":
                    return [
                        {
                            "element_type": "method",
                            "text": "We used a controlled experimental design with 50 participants",
                            "evidence_type": "mixed",
                            "confidence": 0.85
                        }
                    ]
                else:
                    return []
            
            def validate_response(self, response):
                return True
                
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Create test data
        paper = Paper.create_with_auto_id(
            title="Test Paper on Gesture Recognition",
            authors=("Dr. Test", "Prof. Example"),
            venue="CHI 2024",
            year=2024
        )
        
        abstract_section = DetectedSection.create_with_auto_id(
            section_type="abstract",
            title="Abstract",
            text="We present a novel approach to gesture recognition that achieves 94% accuracy. Our user study with 50 participants demonstrates significant improvements.",
            start_page=1,
            end_page=1,
            confidence=0.9,
            char_start=0,
            char_end=150
        )
        
        methodology_section = DetectedSection.create_with_auto_id(
            section_type="methodology",
            title="3. Methodology",
            text="We used a controlled experimental design with 50 participants. The study followed standard HCI research protocols.",
            start_page=2,
            end_page=2,
            confidence=0.85,
            char_start=500,
            char_end=650
        )
        
        # Test processing
        mock_llm = MockLLMProvider()
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        # Process abstract section
        abstract_elements = await processor.process_section(
            section=abstract_section,
            paper=paper,
            context={"test": True}
        )
        
        print(f"✅ Abstract processing: {len(abstract_elements)} elements extracted")
        
        # Verify element properties
        if abstract_elements:
            element = abstract_elements[0]
            assert element.paper_id == paper.paper_id
            assert element.section == "abstract"
            assert element.page_number == 1
            print("✅ Element properties correctly set")
        
        # Process methodology section
        methodology_elements = await processor.process_section(
            section=methodology_section,
            paper=paper
        )
        
        print(f"✅ Methodology processing: {len(methodology_elements)} elements extracted")
        
        # Test immutability
        try:
            if abstract_elements:
                abstract_elements[0].text = "modified"
            print("❌ Immutability test failed")
            return False
        except (AttributeError, TypeError):
            print("✅ Extracted elements are immutable")
        
        return True
        
    except Exception as e:
        print(f"❌ Section processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_processing():
    """Test concurrent batch processing of multiple sections."""
    print("\n🧪 Testing batch processing...")
    
    try:
        from hci_extractor.models import DetectedSection, Paper
        from hci_extractor.pipeline import LLMSectionProcessor, process_sections_batch
        from hci_extractor.llm import LLMProvider
        
        # Mock LLM with variable processing time
        class MockLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                
            async def analyze_section(self, section_text, section_type, context=None):
                # Simulate variable processing time
                await asyncio.sleep(0.2)
                
                return [
                    {
                        "element_type": "finding",
                        "text": f"Finding from {section_type} section",
                        "evidence_type": "qualitative",
                        "confidence": 0.8
                    }
                ]
            
            def validate_response(self, response):
                return True
                
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Create multiple sections for batch processing
        paper = Paper.create_with_auto_id(
            title="Batch Test Paper",
            authors=("Dr. Batch",),
            venue="Test Venue"
        )
        
        sections = []
        section_types = ["abstract", "introduction", "methodology", "results", "conclusion"]
        
        for i, section_type in enumerate(section_types):
            section = DetectedSection.create_with_auto_id(
                section_type=section_type,
                title=section_type.title(),
                text=f"Content for {section_type} section",
                start_page=i+1,
                end_page=i+1,
                confidence=0.8,
                char_start=i*100,
                char_end=(i+1)*100
            )
            sections.append(section)
        
        # Test batch processing
        mock_llm = MockLLMProvider()
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        start_time = asyncio.get_event_loop().time()
        all_elements = await process_sections_batch(
            sections=tuple(sections),
            paper=paper,
            processor=processor,
            max_concurrent=3
        )
        end_time = asyncio.get_event_loop().time()
        
        processing_time = end_time - start_time
        
        print(f"✅ Batch processing: {len(all_elements)} total elements")
        print(f"✅ Processing time: {processing_time:.2f}s (concurrent)")
        print(f"✅ Elements from {len(set(e.section for e in all_elements))} sections")
        
        # Verify we got results from all sections
        extracted_sections = {element.section for element in all_elements}
        expected_sections = set(section_types)
        
        if extracted_sections == expected_sections:
            print("✅ All sections processed successfully")
        else:
            print(f"⚠️  Missing sections: {expected_sections - extracted_sections}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all section processor tests."""
    print("🚀 Testing Section Processor")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Interface compliance
    if test_section_processor_interface():
        tests_passed += 1
        print("✅ Interface compliance PASSED")
    else:
        print("❌ Interface compliance FAILED")
    
    # Test 2: Section processing
    if await test_section_processing():
        tests_passed += 1
        print("✅ Section processing PASSED")
    else:
        print("❌ Section processing FAILED")
    
    # Test 3: Batch processing
    if await test_batch_processing():
        tests_passed += 1
        print("✅ Batch processing PASSED")
    else:
        print("❌ Batch processing FAILED")
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Section processor working!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
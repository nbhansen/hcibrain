#!/usr/bin/env python3
"""
Test the complete simple extraction pipeline - end to end!
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_simple_extraction():
    """Test the complete simple extraction workflow."""
    print("🚀 Testing Simple Extraction Pipeline")
    print("=" * 50)
    
    try:
        from hci_extractor.pipeline import extract_paper_simple
        from hci_extractor.models import PdfContent, PdfPage, Paper
        from hci_extractor.llm import LLMProvider
        from hci_extractor.extractors import PdfExtractor
        
        # Create a comprehensive mock LLM provider
        class MockLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                
            async def analyze_section(self, section_text, section_type, context=None):
                # Simulate realistic extraction based on section type
                await asyncio.sleep(0.1)  # Simulate API delay
                
                if section_type == "abstract":
                    return [
                        {
                            "element_type": "claim",
                            "text": "We present a novel approach to gesture recognition that improves accuracy",
                            "evidence_type": "theoretical",
                            "confidence": 0.90
                        },
                        {
                            "element_type": "finding", 
                            "text": "Our system achieves 94% accuracy compared to 85% baseline",
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
                elif section_type == "results":
                    return [
                        {
                            "element_type": "finding",
                            "text": "Users completed tasks 30% faster with the new interface",
                            "evidence_type": "quantitative", 
                            "confidence": 0.90
                        },
                        {
                            "element_type": "finding",
                            "text": "Participants rated the system as significantly more intuitive",
                            "evidence_type": "qualitative",
                            "confidence": 0.85
                        }
                    ]
                elif section_type == "discussion":
                    return [
                        {
                            "element_type": "claim",
                            "text": "The results demonstrate the effectiveness of our hybrid approach",
                            "evidence_type": "theoretical",
                            "confidence": 0.80
                        }
                    ]
                else:
                    return []
            
            def validate_response(self, response):
                return True
                
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Mock the PDF extractor to avoid file dependencies
        class MockPdfExtractor:
            def extract_content(self, file_path):
                # Create realistic academic paper content
                academic_content = """
                
Title: A Novel Approach to Gesture Recognition in Human-Computer Interaction

Abstract

We present a novel approach to gesture recognition that improves accuracy by 40% compared to existing methods. Our system achieves 94% accuracy compared to 85% baseline through a hybrid computer vision and sensor fusion approach. We conducted a comprehensive user study with 50 participants to validate our findings.

1. Introduction

Human-computer interaction has evolved significantly over the past decade. Traditional input methods are being replaced by more intuitive gesture-based interfaces. Our research addresses the challenge of accurate gesture recognition in real-time applications while maintaining low computational overhead.

2. Related Work

Previous work in gesture recognition has focused primarily on computer vision approaches. Smith et al. (2020) achieved 85% accuracy using deep learning methods. However, these approaches suffer from high computational costs and poor performance in varying lighting conditions.

3. Methodology

We used a controlled experimental design with 50 participants recruited from university students and staff. The study followed standard HCI research protocols with proper informed consent and ethical approval. Our hybrid system combines RGB cameras with accelerometer data to improve recognition accuracy.

4. Results

Users completed tasks 30% faster with the new interface compared to traditional mouse and keyboard input. Participants rated the system as significantly more intuitive on a 7-point Likert scale (M=6.2, SD=0.8). The gesture recognition accuracy reached 94% across all participants and gesture types.

5. Discussion

The results demonstrate the effectiveness of our hybrid approach. The combination of visual and sensor data provides more robust recognition than either modality alone. These findings have important implications for the design of future gesture-based interfaces.

6. Conclusion

We have presented a novel gesture recognition system that achieves state-of-the-art accuracy while maintaining real-time performance. The system shows significant improvements over existing methods and provides a foundation for future research in multimodal interaction.

References

[1] Smith, J. et al. (2020). Deep Learning for Gesture Recognition. CHI 2020.
[2] Jones, A. et al. (2019). Sensor Fusion in HCI Applications. UIST 2019.
                """
                
                page = PdfPage(
                    page_number=1,
                    text=academic_content,
                    char_count=len(academic_content),
                    dimensions=(612.0, 792.0),
                    char_positions=()
                )
                
                return PdfContent(
                    file_path=str(file_path),
                    total_pages=1,
                    pages=(page,),
                    extraction_metadata={"test": True}
                )
        
        # Patch the PDF extractor
        import hci_extractor.pipeline.simple_extractor as simple_extractor
        simple_extractor.PdfExtractor = MockPdfExtractor
        
        # Test the complete extraction pipeline
        print("🧪 Testing complete extraction workflow...")
        
        llm_provider = MockLLMProvider()
        
        # Create test paper metadata
        paper_metadata = {
            "title": "A Novel Approach to Gesture Recognition in HCI",
            "authors": ["Dr. Test", "Prof. Example"],
            "venue": "CHI 2024",
            "year": 2024
        }
        
        # Run the complete extraction
        result = await extract_paper_simple(
            pdf_path=Path("test_paper.pdf"),  # Mock path
            llm_provider=llm_provider,
            paper_metadata=paper_metadata
        )
        
        # Verify results
        print(f"✅ Extraction completed successfully!")
        print(f"📋 Paper: {result.paper.title}")
        print(f"👥 Authors: {', '.join(result.paper.authors)}")
        print(f"🔍 Elements extracted: {len(result.elements)}")
        
        # Check element distribution
        element_types = {}
        sections = set()
        for element in result.elements:
            element_types[element.element_type] = element_types.get(element.element_type, 0) + 1
            sections.add(element.section)
        
        print(f"📊 Element types: {element_types}")
        print(f"📝 Sections processed: {sorted(sections)}")
        
        # Verify we got elements
        assert len(result.elements) > 0, "Should extract some elements"
        assert result.paper.title == paper_metadata["title"], "Paper metadata should be preserved"
        
        # Check extraction metadata
        metadata = result.extraction_metadata
        print(f"⚙️  Processing metadata: {metadata}")
        
        assert metadata["processing_status"] == "success", "Should report success"
        assert metadata["elements_extracted"] == len(result.elements), "Element count should match"
        
        # Test individual elements
        if result.elements:
            element = result.elements[0]
            print(f"📄 Sample element: {element.element_type} - '{element.text[:50]}...'")
            assert element.paper_id == result.paper.paper_id, "Element should reference correct paper"
            assert element.confidence >= 0.0 and element.confidence <= 1.0, "Confidence should be valid"
        
        print("✅ All extraction tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_extraction_with_validation():
    """Test extraction with optional validation."""
    print("\n🧪 Testing extraction with validation...")
    
    try:
        from hci_extractor.pipeline import extract_paper_simple, validate_extracted_elements, quick_validation_stats
        from hci_extractor.models import PdfContent, PdfPage
        from hci_extractor.llm import LLMProvider
        
        # Mock LLM that returns some duplicates and edge cases
        class TestLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                
            async def analyze_section(self, section_text, section_type, context=None):
                return [
                    {
                        "element_type": "finding",
                        "text": "Users completed tasks 30% faster",  # This exists in our mock content
                        "evidence_type": "quantitative",
                        "confidence": 0.90
                    },
                    {
                        "element_type": "finding", 
                        "text": "Users completed tasks 30% faster",  # Duplicate
                        "evidence_type": "quantitative",
                        "confidence": 0.85
                    },
                    {
                        "element_type": "claim",
                        "text": "X",  # Too short
                        "evidence_type": "theoretical",
                        "confidence": 0.60
                    },
                    {
                        "element_type": "finding",
                        "text": "This text does not exist in the source document",  # Not in source
                        "evidence_type": "qualitative",
                        "confidence": 0.75
                    }
                ]
            
            def validate_response(self, response):
                return True
                
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Mock PDF extractor with known content
        class TestPdfExtractor:
            def extract_content(self, file_path):
                content = "Users completed tasks 30% faster with the new interface compared to traditional methods."
                
                page = PdfPage(
                    page_number=1,
                    text=content,
                    char_count=len(content),
                    dimensions=(612.0, 792.0),
                    char_positions=()
                )
                
                return PdfContent(
                    file_path=str(file_path),
                    total_pages=1,
                    pages=(page,),
                    extraction_metadata={"test": True}
                )
        
        # Patch extractor
        import hci_extractor.pipeline.simple_extractor as simple_extractor
        simple_extractor.PdfExtractor = TestPdfExtractor
        
        # Run extraction
        llm_provider = TestLLMProvider()
        result = await extract_paper_simple(
            pdf_path=Path("test.pdf"),
            llm_provider=llm_provider
        )
        
        print(f"📦 Raw extraction: {len(result.elements)} elements")
        
        # Get PDF content for validation  
        pdf_extractor = TestPdfExtractor()
        pdf_content = pdf_extractor.extract_content(Path("test.pdf"))
        
        # Apply validation
        validated_elements = validate_extracted_elements(result.elements, pdf_content)
        
        print(f"✅ After validation: {len(validated_elements)} elements")
        
        # Get validation stats
        stats = quick_validation_stats(result.elements, validated_elements)
        print(f"📊 Validation stats: {stats}")
        
        # Should have removed duplicates, short text, and non-existent text
        assert len(validated_elements) < len(result.elements), "Validation should remove some elements"
        assert len(validated_elements) >= 1, "Should keep at least one valid element"
        
        print("✅ Validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all simple extraction tests."""
    
    tests_passed = 0
    total_tests = 2
    
    if await test_simple_extraction():
        tests_passed += 1
        print("✅ Simple extraction PASSED")
    else:
        print("❌ Simple extraction FAILED")
    
    if await test_extraction_with_validation():
        tests_passed += 1
        print("✅ Extraction with validation PASSED")
    else:
        print("❌ Extraction with validation FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Simple extraction pipeline working!")
        print("\n🚀 Ready to extract academic papers!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
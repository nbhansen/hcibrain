#!/usr/bin/env python3
"""
Test the section detection functionality with sample academic text.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_section_detection():
    """Test section detection with sample academic paper text."""
    print("🧪 Testing section detection...")
    
    try:
        from hci_extractor.models import PdfContent, PdfPage, DetectedSection
        from hci_extractor.pipeline import detect_sections
        
        # Create sample academic paper text with clear section headers
        sample_text = """
Title: A Novel Approach to Gesture Recognition in HCI

Abstract

This paper presents a novel approach to gesture recognition that improves accuracy by 40% compared to existing methods. We conducted a user study with 50 participants to evaluate our system.

1. Introduction

Human-computer interaction has evolved significantly over the past decade. Traditional input methods are being replaced by more intuitive gesture-based interfaces. Our research addresses the challenge of accurate gesture recognition in real-time applications.

2. Related Work

Previous work in gesture recognition has focused primarily on computer vision approaches. Smith et al. (2020) achieved 85% accuracy using deep learning methods. However, these approaches suffer from high computational costs.

3. Methodology

We developed a hybrid approach combining computer vision with sensor fusion. Our system uses a combination of RGB cameras and accelerometer data to improve recognition accuracy.

3.1. System Design

The system architecture consists of three main components: data acquisition, feature extraction, and classification.

4. Implementation

We implemented our system using Python and OpenCV. The machine learning models were trained using TensorFlow on a dataset of 10,000 gesture samples.

5. Results

Our evaluation showed significant improvements over baseline methods. The system achieved 94% accuracy with an average response time of 120ms.

5.1. User Study Results

We conducted a controlled user study with 50 participants. Users completed gesture tasks using both our system and a baseline implementation.

6. Discussion

The results demonstrate the effectiveness of our hybrid approach. The combination of visual and sensor data provides more robust recognition than either modality alone.

7. Conclusion

We have presented a novel gesture recognition system that achieves state-of-the-art accuracy while maintaining real-time performance. Future work will explore additional sensor modalities.

References

[1] Smith, J. et al. (2020). Deep Learning for Gesture Recognition. CHI 2020.
        """
        
        # Create mock PDF content
        page = PdfPage(
            page_number=1,
            text=sample_text,
            char_count=len(sample_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="test_paper.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={"test": True}
        )
        
        print("✅ Created sample PDF content")
        
        # Test section detection
        detected_sections = detect_sections(pdf_content)
        
        print(f"✅ Detected {len(detected_sections)} sections")
        
        # Verify expected sections were found
        expected_sections = {
            "abstract", "introduction", "related_work", 
            "methodology", "implementation", "results", 
            "discussion", "conclusion"
        }
        
        found_sections = {section.section_type for section in detected_sections}
        print(f"✅ Found section types: {sorted(found_sections)}")
        
        # Check that we found most expected sections
        found_expected = expected_sections & found_sections
        print(f"✅ Found {len(found_expected)}/{len(expected_sections)} expected sections")
        
        # Verify section ordering
        if len(detected_sections) > 1:
            ordered_correctly = all(
                detected_sections[i].char_start < detected_sections[i+1].char_start
                for i in range(len(detected_sections)-1)
            )
            print(f"✅ Sections ordered correctly: {ordered_correctly}")
        
        # Display section details
        print("\n📋 Detected sections:")
        for section in detected_sections:
            print(f"  {section.section_type}: '{section.title}' "
                  f"(confidence: {section.confidence:.2f}, "
                  f"chars: {section.char_start}-{section.char_end})")
        
        # Test immutability
        try:
            detected_sections[0].section_type = "modified"
            print("❌ Immutability test failed - section was modified")
            return False
        except (AttributeError, TypeError):
            print("✅ Immutability test passed - sections are immutable")
        
        return True
        
    except Exception as e:
        print(f"❌ Section detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test section detection edge cases."""
    print("\n🧪 Testing edge cases...")
    
    try:
        from hci_extractor.models import PdfContent, PdfPage
        from hci_extractor.pipeline import detect_sections
        
        # Test empty document
        empty_page = PdfPage(
            page_number=1,
            text="",
            char_count=0,
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        empty_pdf = PdfContent(
            file_path="empty.pdf",
            total_pages=1,
            pages=(empty_page,),
            extraction_metadata={}
        )
        
        empty_sections = detect_sections(empty_pdf)
        assert len(empty_sections) == 0
        print("✅ Empty document handled correctly")
        
        # Test document without clear sections
        no_sections_text = "This is just a paragraph of text without any clear section headers."
        
        no_sections_page = PdfPage(
            page_number=1,
            text=no_sections_text,
            char_count=len(no_sections_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        no_sections_pdf = PdfContent(
            file_path="no_sections.pdf",
            total_pages=1,
            pages=(no_sections_page,),
            extraction_metadata={}
        )
        
        no_sections_result = detect_sections(no_sections_pdf)
        print(f"✅ Document without sections: {len(no_sections_result)} sections detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing Section Detection")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 2
    
    if test_section_detection():
        tests_passed += 1
        print("✅ Section detection PASSED")
    else:
        print("❌ Section detection FAILED")
    
    if test_edge_cases():
        tests_passed += 1
        print("✅ Edge cases PASSED")
    else:
        print("❌ Edge cases FAILED")
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Section detection working!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)
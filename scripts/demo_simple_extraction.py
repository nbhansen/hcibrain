#!/usr/bin/env python3
"""
Demo: The Simplest Possible Academic Paper Extraction

This shows how simple it is to extract academic elements from papers!
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def demo_simple_extraction():
    """Demonstrate the simplest possible extraction workflow."""
    
    print("📚 Academic Paper Extraction Demo")
    print("=" * 40)
    print("The simplest possible version - just find text snippets!")
    print()
    
    try:
        from hci_extractor.pipeline import detect_sections, LLMSectionProcessor, process_sections_batch
        from hci_extractor.models import PdfContent, PdfPage, Paper
        from hci_extractor.llm import LLMProvider
        
        # Step 1: Mock some academic paper content
        print("📄 Sample academic paper:")
        paper_content = """
        Title: TouchGestures - Enhanced Multi-touch Interaction for Mobile Devices
        
        Abstract
        
        We present TouchGestures, a novel interaction technique that enables users to perform complex multi-touch gestures with 40% fewer errors than standard touch interfaces. Through a controlled study with 24 participants, we found that users completed tasks 23% faster using TouchGestures compared to conventional touch input. Our system introduces three new gesture recognition algorithms that improve accuracy while reducing computational overhead by 15%.
        
        1. Introduction
        
        Human-computer interaction has evolved dramatically with the proliferation of touch-enabled devices. Traditional single-touch interfaces limit user expression and efficiency. Our research addresses the fundamental challenge of enabling complex gestural input while maintaining system responsiveness and accuracy.
        
        2. Related Work
        
        Previous gesture recognition systems have achieved varying degrees of success. Wilson et al. (2019) reported 78% accuracy with their deep learning approach, while Chen and Park (2020) achieved 85% accuracy using computer vision techniques. However, these systems suffer from high computational costs and poor performance in varying lighting conditions.
        
        3. Methodology
        
        We conducted a controlled experiment with 24 participants (12 male, 12 female, ages 22-45). The study used a within-subjects design comparing TouchGestures against a baseline touch interface. Each participant completed 20 tasks in randomized order. We measured task completion time, error rates, and subjective satisfaction using 7-point Likert scales.
        
        4. Results
        
        TouchGestures demonstrated significant improvements across all metrics. Users completed tasks 23% faster (M=42.3s vs M=55.1s, t(23)=4.72, p<0.001) and made 40% fewer errors (M=1.2 vs M=2.0 errors per task, t(23)=3.89, p=0.001). Participants rated TouchGestures as significantly more intuitive (M=6.2 vs M=4.1 on 7-point scale, t(23)=5.14, p<0.001).
        
        5. Discussion
        
        The results demonstrate the effectiveness of our multi-touch approach. The 23% improvement in task completion time suggests that TouchGestures enables more efficient interaction patterns. The reduction in error rates indicates improved system accuracy and user confidence.
        
        6. Conclusion
        
        We have presented TouchGestures, a novel multi-touch interaction technique that significantly improves user performance. Our system achieves state-of-the-art accuracy while maintaining real-time responsiveness. Future work will explore integration with voice commands and haptic feedback.
        """
        
        print(f"   • {len(paper_content)} characters")
        print(f"   • About touchscreen gesture interaction")
        print()
        
        # Step 2: Create PDF content structure
        page = PdfPage(
            page_number=1,
            text=paper_content,
            char_count=len(paper_content),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="demo_paper.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={"demo": True}
        )
        
        # Step 3: Detect sections automatically
        print("🔍 Step 1: Detecting paper sections...")
        sections = detect_sections(pdf_content)
        
        for section in sections:
            print(f"   • {section.section_type}: '{section.title}' ({len(section.text)} chars)")
        print()
        
        # Step 4: Create paper metadata
        paper = Paper.create_with_auto_id(
            title="TouchGestures - Enhanced Multi-touch Interaction",
            authors=("Dr. Mobile", "Prof. Interaction"),
            venue="CHI 2024",
            year=2024
        )
        
        # Step 5: Mock LLM that finds interesting snippets
        class DemoLLMProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                
            async def analyze_section(self, section_text, section_type, context=None):
                await asyncio.sleep(0.1)  # Simulate processing
                
                # Extract different types based on section
                if section_type == "abstract":
                    return [
                        {
                            "element_type": "claim",
                            "text": "TouchGestures, a novel interaction technique that enables users to perform complex multi-touch gestures with 40% fewer errors",
                            "evidence_type": "theoretical",
                            "confidence": 0.95
                        },
                        {
                            "element_type": "finding",
                            "text": "users completed tasks 23% faster using TouchGestures compared to conventional touch input",
                            "evidence_type": "quantitative",
                            "confidence": 0.90
                        }
                    ]
                elif section_type == "methodology":
                    return [
                        {
                            "element_type": "method",
                            "text": "controlled experiment with 24 participants (12 male, 12 female, ages 22-45)",
                            "evidence_type": "quantitative",
                            "confidence": 0.85
                        },
                        {
                            "element_type": "method", 
                            "text": "within-subjects design comparing TouchGestures against a baseline touch interface",
                            "evidence_type": "theoretical",
                            "confidence": 0.80
                        }
                    ]
                elif section_type == "results":
                    return [
                        {
                            "element_type": "finding",
                            "text": "Users completed tasks 23% faster (M=42.3s vs M=55.1s, t(23)=4.72, p<0.001)",
                            "evidence_type": "quantitative", 
                            "confidence": 0.95
                        },
                        {
                            "element_type": "finding",
                            "text": "made 40% fewer errors (M=1.2 vs M=2.0 errors per task, t(23)=3.89, p=0.001)",
                            "evidence_type": "quantitative",
                            "confidence": 0.95
                        },
                        {
                            "element_type": "finding",
                            "text": "Participants rated TouchGestures as significantly more intuitive (M=6.2 vs M=4.1 on 7-point scale)",
                            "evidence_type": "quantitative",
                            "confidence": 0.90
                        }
                    ]
                elif section_type == "conclusion":
                    return [
                        {
                            "element_type": "claim",
                            "text": "TouchGestures, a novel multi-touch interaction technique that significantly improves user performance",
                            "evidence_type": "theoretical",
                            "confidence": 0.85
                        }
                    ]
                else:
                    return []
            
            def validate_response(self, response):
                return True
                
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        # Step 6: Extract interesting snippets with LLM
        print("🤖 Step 2: Extracting interesting text snippets...")
        llm_provider = DemoLLMProvider()
        processor = LLMSectionProcessor(llm_provider=llm_provider)
        
        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            max_concurrent=2
        )
        
        print(f"   • Found {len(all_elements)} interesting text snippets")
        print()
        
        # Step 7: Show results by type
        print("📋 Step 3: Results by element type...")
        
        claims = [e for e in all_elements if e.element_type == "claim"]
        findings = [e for e in all_elements if e.element_type == "finding"]
        methods = [e for e in all_elements if e.element_type == "method"]
        
        print(f"\n📢 Claims ({len(claims)}):")
        for claim in claims:
            print(f"   • \"{claim.text}\"")
            print(f"     (from {claim.section}, confidence: {claim.confidence:.2f})")
        
        print(f"\n🔬 Findings ({len(findings)}):")
        for finding in findings:
            print(f"   • \"{finding.text}\"")
            print(f"     (from {finding.section}, confidence: {finding.confidence:.2f})")
        
        print(f"\n⚙️ Methods ({len(methods)}):")
        for method in methods:
            print(f"   • \"{method.text}\"")
            print(f"     (from {method.section}, confidence: {method.confidence:.2f})")
        
        print(f"\n🎉 Done! Found {len(all_elements)} text snippets from {len(sections)} sections")
        print("\n✨ This is the simplest possible version:")
        print("   • No complex validation")
        print("   • No statistical analysis") 
        print("   • Just smart text finding")
        print("   • Ready for researchers to analyze!")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting demo...")
    success = asyncio.run(demo_simple_extraction())
    
    if success:
        print("\n🎉 Demo completed successfully!")
        print("\n💡 This system is ready for:")
        print("   • Literature reviews")
        print("   • Meta-analysis preparation") 
        print("   • Finding patterns across papers")
        print("   • Systematic reviews")
    else:
        print("\n💥 Demo failed!")
    
    sys.exit(0 if success else 1)
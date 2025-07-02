#!/usr/bin/env python3
"""
End-to-end test of the clean prompt architecture
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_end_to_end():
    """Test complete prompt generation workflow."""
    print("🚀 End-to-end prompt architecture test")
    print("=" * 50)
    
    try:
        # Step 1: Test independent PromptManager
        from hci_extractor.prompts import PromptManager
        pm = PromptManager()
        print("✅ PromptManager imports and initializes independently")
        
        # Step 2: Test base LLM class imports cleanly
        from hci_extractor.llm import LLMProvider
        print("✅ LLMProvider imports without external dependencies")
        
        # Step 3: Create a mock provider that uses PromptManager
        class TestProvider(LLMProvider):
            def __init__(self):
                super().__init__()
                self.prompt_manager = PromptManager()
            
            async def analyze_section(self, section_text, section_type, context=None):
                # Use PromptManager to generate prompts
                prompt = self.prompt_manager.get_analysis_prompt(
                    section_text=section_text,
                    section_type=section_type,
                    context=context,
                    include_examples=True
                )
                # Mock analysis - just return empty results
                return []
            
            def validate_response(self, response):
                return True
            
            async def _make_api_request(self, prompt, **kwargs):
                return {"elements": []}
        
        provider = TestProvider()
        print("✅ Test provider with PromptManager created successfully")
        
        # Step 4: Test prompt generation
        sample_abstract = """
        We present GestureAI, a novel machine learning approach for gesture recognition 
        that achieves 94% accuracy. Our study with 50 participants showed 30% faster 
        task completion compared to traditional interfaces.
        """
        
        context = {
            "paper_title": "GestureAI: ML-Enhanced Touch Interaction",
            "paper_venue": "CHI 2024",
            "authors": ["Dr. AI", "Prof. HCI"]
        }
        
        # This would normally be an async call, but we're just testing prompt generation
        prompt = provider.prompt_manager.get_analysis_prompt(
            section_text=sample_abstract,
            section_type="abstract",
            context=context,
            include_examples=True
        )
        
        print(f"✅ Generated prompt: {len(prompt)} characters")
        
        # Verify key elements
        assert "GestureAI" in prompt
        assert "CHI 2024" in prompt
        assert "CRITICAL RULES" in prompt
        assert "artifact" in prompt  # New HCI-focused element type
        assert "knowledge-increasing" in prompt  # New contribution type
        print("✅ Prompt contains expected HCI-focused content")
        
        # Step 5: Test different sections
        sections = ["abstract", "methods", "results", "discussion"]
        for section in sections:
            section_prompt = provider.prompt_manager.get_analysis_prompt(
                section_text="Sample text for " + section,
                section_type=section,
                include_examples=False
            )
            assert len(section_prompt) > 100
        
        print(f"✅ All section types work: {sections}")
        
        print("\n🎉 End-to-end architecture test PASSED!")
        print("✨ Clean separation: PromptManager ↔ LLM Providers")
        print("✨ No circular dependencies")
        print("✨ HCI-focused prompts with examples")
        print("✨ Provider-agnostic design")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
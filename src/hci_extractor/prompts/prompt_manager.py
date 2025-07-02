"""
Prompt management system for HCI paper extraction.

Provides a centralized, provider-agnostic way to load and compose prompts
for different paper sections and analysis tasks.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..models import HciExtractorError

logger = logging.getLogger(__name__)


class PromptLoadError(HciExtractorError):
    """Error loading or parsing prompt templates."""
    pass


class PromptManager:
    """
    Manages loading and composition of analysis prompts.
    
    Provides provider-agnostic prompt templates that can be used
    by any LLM provider for HCI paper analysis.
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize PromptManager.
        
        Args:
            prompts_dir: Directory containing prompt templates.
                        If None, uses default prompts/ directory.
        """
        if prompts_dir is None:
            # Default to prompts/ directory relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = project_root / "prompts"
        
        self.prompts_dir = Path(prompts_dir)
        
        if not self.prompts_dir.exists():
            raise PromptLoadError(f"Prompts directory not found: {self.prompts_dir}")
        
        # Cache for loaded prompt data
        self._base_prompts = None
        self._section_guidance = None
        self._examples_cache = {}
        
        logger.info(f"PromptManager initialized with prompts directory: {self.prompts_dir}")

    def get_analysis_prompt(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
        include_examples: bool = True,
        prompt_variant: str = "default"
    ) -> str:
        """
        Build a complete analysis prompt for a paper section.
        
        Args:
            section_text: The text content of the section
            section_type: Type of section (e.g., 'abstract', 'methods')
            context: Additional context (paper metadata, etc.)
            include_examples: Whether to include few-shot examples
            prompt_variant: Prompt variant to use ('default', 'verbose', 'concise')
            
        Returns:
            Complete prompt string ready for LLM
            
        Raises:
            PromptLoadError: If prompt templates cannot be loaded
        """
        try:
            # Load base prompts and section guidance
            base_prompts = self._load_base_prompts()
            section_guidance = self._load_section_guidance()
            
            # Get section-specific guidance
            section_info = section_guidance["sections"].get(
                section_type.lower(),
                section_guidance["default_guidance"]
            )
            
            # Build context information
            context_info = self._build_context_info(context)
            
            # Load examples if requested
            examples_text = ""
            if include_examples:
                examples_text = self._load_examples_for_section(section_type)
            
            # Compose the complete prompt
            prompt = self._compose_prompt(
                base_prompts=base_prompts,
                section_info=section_info,
                section_text=section_text,
                section_type=section_type,
                context_info=context_info,
                examples_text=examples_text
            )
            
            return prompt
            
        except Exception as e:
            raise PromptLoadError(f"Failed to build analysis prompt: {e}") from e

    def _load_base_prompts(self) -> Dict[str, Any]:
        """Load base prompt templates."""
        if self._base_prompts is None:
            base_file = self.prompts_dir / "base_prompts.yaml"
            self._base_prompts = self._load_yaml_file(base_file)
        return self._base_prompts

    def _load_section_guidance(self) -> Dict[str, Any]:
        """Load section-specific guidance."""
        if self._section_guidance is None:
            guidance_file = self.prompts_dir / "section_guidance.yaml"
            self._section_guidance = self._load_yaml_file(guidance_file)
        return self._section_guidance

    def _load_examples_for_section(self, section_type: str) -> str:
        """Load few-shot examples for a specific section type."""
        cache_key = section_type.lower()
        
        if cache_key not in self._examples_cache:
            examples_file = self.prompts_dir / "examples" / f"{cache_key}_examples.yaml"
            
            if examples_file.exists():
                try:
                    examples_data = self._load_yaml_file(examples_file)
                    examples_text = self._format_examples(examples_data)
                    self._examples_cache[cache_key] = examples_text
                except Exception as e:
                    logger.warning(f"Failed to load examples for {section_type}: {e}")
                    self._examples_cache[cache_key] = ""
            else:
                logger.debug(f"No examples file found for section: {section_type}")
                self._examples_cache[cache_key] = ""
        
        return self._examples_cache[cache_key]

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise PromptLoadError(f"Prompt file not found: {file_path}")
        except yaml.YAMLError as e:
            raise PromptLoadError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise PromptLoadError(f"Error loading {file_path}: {e}")

    def _build_context_info(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context information string from context dictionary."""
        if not context:
            return ""
        
        context_parts = []
        
        if "paper_title" in context:
            context_parts.append(f"Paper title: {context['paper_title']}")
        if "paper_venue" in context:
            context_parts.append(f"Venue: {context['paper_venue']}")
        if "paper_year" in context:
            context_parts.append(f"Year: {context['paper_year']}")
        if "authors" in context:
            authors = context["authors"]
            if isinstance(authors, (list, tuple)):
                authors_str = ", ".join(str(a) for a in authors)
            else:
                authors_str = str(authors)
            context_parts.append(f"Authors: {authors_str}")
        
        return "\n".join(context_parts) + "\n" if context_parts else ""

    def _format_examples(self, examples_data: Dict[str, Any]) -> str:
        """Format few-shot examples into prompt text."""
        if "examples" not in examples_data:
            return ""
        
        examples_text = "\nFEW-SHOT EXAMPLES:\n"
        examples_text += "=" * 50 + "\n"
        
        for i, example in enumerate(examples_data["examples"], 1):
            examples_text += f"\nExample {i}:\n"
            examples_text += "-" * 20 + "\n"
            
            if "section_text" in example:
                examples_text += f"SECTION TEXT:\n{example['section_text']}\n\n"
            
            if "expected_extraction" in example:
                examples_text += "EXPECTED EXTRACTION:\n"
                # Format the expected extraction as JSON
                import json
                formatted_json = json.dumps(example["expected_extraction"], indent=2)
                examples_text += f"{formatted_json}\n"
            
            if "explanation" in example:
                examples_text += f"EXPLANATION: {example['explanation']}\n"
        
        if "guidance_notes" in examples_data:
            examples_text += f"\nGUIDANCE NOTES:\n{examples_data['guidance_notes']}\n"
        
        examples_text += "=" * 50 + "\n\n"
        return examples_text

    def _compose_prompt(
        self,
        base_prompts: Dict[str, Any],
        section_info: Dict[str, Any],
        section_text: str,
        section_type: str,
        context_info: str,
        examples_text: str
    ) -> str:
        """Compose the complete prompt from all components."""
        prompt_parts = []
        
        # System prompt
        if "system_prompt" in base_prompts:
            prompt_parts.append(base_prompts["system_prompt"])
        
        # Core rules
        if "core_rules" in base_prompts:
            core_rules = base_prompts["core_rules"]
            if isinstance(core_rules, list):
                prompt_parts.extend(core_rules)
            else:
                prompt_parts.append(str(core_rules))
        
        # Element type definitions
        if "element_types" in base_prompts:
            prompt_parts.append("ELEMENT TYPES:")
            for elem_type, description in base_prompts["element_types"].items():
                prompt_parts.append(f"- {elem_type}: {description}")
        
        # Evidence type definitions
        if "evidence_types" in base_prompts:
            prompt_parts.append("\nEVIDENCE TYPES:")
            for evidence_type, description in base_prompts["evidence_types"].items():
                prompt_parts.append(f"- {evidence_type}: {description}")
        
        # Section-specific guidance
        prompt_parts.append(f"\nSECTION TYPE: {section_type}")
        prompt_parts.append(f"FOCUS: {section_info.get('focus', 'General analysis')}")
        prompt_parts.append(f"GUIDANCE: {section_info.get('guidance', 'Extract relevant elements.')}")
        
        if "avoid" in section_info:
            prompt_parts.append(f"AVOID: {section_info['avoid']}")
        
        # Context information
        if context_info:
            prompt_parts.append(f"\nCONTEXT:\n{context_info}")
        
        # Few-shot examples
        if examples_text:
            prompt_parts.append(examples_text)
        
        # Section text to analyze
        prompt_parts.append(f"SECTION TEXT TO ANALYZE:\n{section_text}")
        
        # JSON format specification
        if "json_format" in base_prompts:
            prompt_parts.append(f"\n{base_prompts['json_format']}")
        
        # Extraction guidance
        if "extraction_guidance" in base_prompts:
            prompt_parts.append(f"\n{base_prompts['extraction_guidance']}")
        
        return "\n\n".join(prompt_parts)

    def get_available_sections(self) -> List[str]:
        """Get list of available section types with specific guidance."""
        try:
            section_guidance = self._load_section_guidance()
            return list(section_guidance["sections"].keys())
        except Exception as e:
            logger.error(f"Failed to get available sections: {e}")
            return []

    def get_available_examples(self) -> List[str]:
        """Get list of section types with available examples."""
        examples_dir = self.prompts_dir / "examples"
        if not examples_dir.exists():
            return []
        
        example_files = []
        for file_path in examples_dir.glob("*_examples.yaml"):
            section_type = file_path.stem.replace("_examples", "")
            example_files.append(section_type)
        
        return sorted(example_files)

    def reload_prompts(self) -> None:
        """Reload all prompt templates from disk."""
        self._base_prompts = None
        self._section_guidance = None
        self._examples_cache.clear()
        logger.info("Prompt templates reloaded from disk")
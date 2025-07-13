"""Simple prompt loader for markup generation."""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


class MarkupPromptLoader:
    """Loads and manages markup generation prompts from YAML files."""

    def __init__(self, prompts_dir: Path):
        """Initialize with prompts directory."""
        self.prompts_dir = prompts_dir
        self._prompts: Dict[str, Any] = {}
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load prompts from YAML files."""
        markup_prompts_file = self.prompts_dir / "markup_prompts.yaml"

        if not markup_prompts_file.exists():
            raise FileNotFoundError(
                f"Markup prompts file not found: {markup_prompts_file}",
            )

        try:
            with open(markup_prompts_file, "r", encoding="utf-8") as f:
                self._prompts = yaml.safe_load(f)
            logger.info(f"Loaded markup prompts from {markup_prompts_file}")
        except Exception as e:
            logger.exception(f"Failed to load markup prompts: {e}")
            raise

    def get_markup_prompt(
        self,
        text: str,
        chunk_index: int = 1,
        total_chunks: int = 1,
    ) -> str:
        """Generate complete markup prompt using the template structure."""
        markup_config = self._prompts.get("markup_generation", {})

        # Check if we have the new template structure
        if "template" in markup_config:
            # Use the new template-based approach
            template = markup_config["template"]

            # Build chunk info if needed
            chunk_info = ""
            if total_chunks > 1:
                chunk_template = self._prompts.get("chunk_processing", {}).get(
                    "chunk_info_template",
                    "",
                )
                chunk_info = chunk_template.format(
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                )

                # Add chunk context if available
                chunk_context = self._prompts.get("chunk_processing", {}).get(
                    "chunk_context",
                    "",
                )
                if chunk_context:
                    template += f"\n\n{chunk_context}"

            # Format the template with all components
            rules = markup_config.get("rules", "")
            if isinstance(rules, str):
                rules = rules.strip()
            else:
                # Convert list to string if needed (backwards compatibility)
                rules = "\n".join(str(rule) for rule in rules) if rules else ""

            return template.format(
                system_prompt=markup_config.get("system_prompt", "").strip(),
                task_1_cleaning=markup_config.get("task_1_cleaning", "").strip(),
                task_2_markup=markup_config.get("task_2_markup", "").strip(),
                task_3_summary=markup_config.get("task_3_summary", "").strip(),
                rules=rules,
                text=text,
                chunk_info=chunk_info,
            )
        # Fallback to old structure for backwards compatibility
        # Build chunk info if needed
        chunk_info = ""
        if total_chunks > 1:
            chunk_template = self._prompts.get("chunk_processing", {}).get(
                "chunk_info_template",
                "",
            )
            chunk_info = chunk_template.format(
                chunk_index=chunk_index,
                total_chunks=total_chunks,
            )

        # Format rules as numbered list (old format expected list)
        rules = markup_config.get("rules", [])
        if isinstance(rules, list):
            formatted_rules = "\n".join(
                f"{i + 1}. {rule}" for i, rule in enumerate(rules)
            )
        else:
            formatted_rules = str(rules)

        # Build complete prompt
        system_prompt = markup_config.get("system_prompt", "").strip()
        if chunk_info:
            system_prompt = system_prompt.replace(
                "paper text",
                f"paper text{chunk_info}",
            )

        prompt_parts = [
            system_prompt,
            "",
            markup_config.get("task_1_cleaning", "").strip(),
            "",
            markup_config.get("task_2_markup", "").strip(),
            "",
            "Rules:",
            formatted_rules,
            "",
            "Paper text:",
            text,
        ]

        return "\n".join(prompt_parts)

    def reload_prompts(self) -> None:
        """Reload prompts from files (useful for development)."""
        self._load_prompts()
        logger.info("Reloaded markup prompts")

# Code Review Refactoring Plan

This document outlines the step-by-step plan to address the module organization and dependency issues identified in the code review.

### **Phase 1: Restructure Directories and Move Files**

This phase focuses on creating the new directory structure and moving existing files to their new locations without immediately refactoring their contents. This isolates the structural changes from the code changes.

1.  **Create New Directories:** First, create the target directory structure as recommended in the code review to establish the new layout:
    *   `src/hci_extractor/core/`
    *   `src/hci_extractor/core/models/`
    *   `src/hci_extractor/core/extraction/`
    *   `src/hci_extractor/core/analysis/`
    *   `src/hci_extractor/providers/`
    *   `src/hci_extractor/cli/`
    *   `src/hci_extractor/utils/`

2.  **Move Existing Modules:** Then, move the existing files into the new structure according to their responsibilities:
    *   **Models:** Move `src/hci_extractor/models/*` to `src/hci_extractor/core/models/`.
    *   **LLM Providers:** Rename `src/hci_extractor/llm/` to `src/hci_extractor/providers/`.
    *   **Extraction Logic:** Move `src/hci_extractor/extractors/*` to `src/hci_extractor/core/extraction/`.
    *   **Pipeline & Analysis:** Move the contents of `src/hci_extractor/pipeline/*` into `src/hci_extractor/core/analysis/`.
    *   **UI to CLI:** Move `src/hci_extractor/ui/progress.py` to `src/hci_extractor/cli/progress.py`.

### **Phase 2: Refactor Code and Fix Imports**

After the files are in their new locations, the next step is to update the code to reflect the new structure and decouple the modules.

1.  **Update Import Statements:** Go through each moved file and update all `import` statements to point to the new module locations. This will likely cause the application to be in a broken state until all paths are corrected.

2.  **Decouple CLI from Core Logic:**
    *   Refactor the current `src/hci_extractor/main.py` and `__main__.py`.
    *   The core application logic will be kept in the `core` and `providers` modules.
    *   The command-line interface (CLI) specific code, especially the `click` commands, will be moved into the `src/hci_extractor/cli/` directory. This will ensure the core logic can be used independently of the CLI.

3.  **Create Utility Modules:**
    *   Identify shared code, such as logging configuration or configuration management, and move it into new files within `src/hci_extractor/utils/`. This will reduce code duplication.

### **Phase 3: Validation**

1.  **Run Static Analysis:** Use a tool like `mypy` (as recommended in another part of the review) to check for any remaining import or type-related errors.
2.  **Run Tests:** Execute the existing test suite to ensure that the refactoring has not broken any functionality. Fix any tests that fail due to the new structure.

# Zeroth Law of AI-Driven Development: Code Quality Assessment Framework

**Co-Author**: Trahloc colDhart
**Version**: 2025-03-16

## 1. PURPOSE

A foundational principle ensuring code quality metrics center on AI comprehension: emphasizes descriptive, self-contained, and consistent structures; aims for continual self-assessment and improvement; prioritizes clarity over traditional norms, enabling AI systems to effectively parse, understand, and evolve the codebase without being limited by human methods. This version incorporates best practices for modularity, specifically the single-responsibility principle and the use of index modules for clear API definition.

## 2. Core Focus

This framework establishes fundamental quality principles for technical hobbyists using AI tools with 16k+ context windows to generate and maintain code. It optimizes code structure for AI comprehension while ensuring maintainability and reliability. This is a personal framework, not an industry standard, though it references established industry practices where appropriate.

## 3. Application as the "Zeroth Law"

This framework serves as the foundational principle that supersedes all other development considerations. Before any functional requirement is considered complete, code must satisfy these quality metrics. AI assistants should automatically apply these principles during development and flag any violations for immediate correction.

## 4. Guiding Principles

1.  **AI Comprehension Priority:** AI readability surpasses all human conventions. Format code and data primarily for the AI’s clarity. Humans can request simpler explanations from the AI if needed.

2.  **In-File Context Sufficiency:** All necessary context should be contained within the file itself. External documentation (wikis, external docs) is considered counterproductive for AI comprehension purposes. It's better that a function have a descriptive sentence-like name than require complex documentation elsewhere.

3.  **Implementability Principle:** A practical framework that gets used consistently is superior to a perfect framework that remains theoretical. The Zeroth Law prioritizes real-world applicability over theoretical purity.

4.  **Incremental Enhancement Focus:** Progress is tracked through AI-led assessments, with consistent, non-breaking refinements introduced across development sessions.

5.  **Do not reinvent the wheel:** Always use popular and well supported pre-made modules rather than reimplement it inhouse.

6.  **Single Responsibility Principle (SRP):** Each module (file) should have one, and only one, reason to change. This guides the structure towards one function (or a very tightly related group of functions) per file.

7.  **Modularity and Composability:** Functions are treated as self-contained units. Index modules (`__init__.py` files) are used to compose higher-level functionality by importing and exposing these individual functions.

8.  **Explicit API Design:** Index modules serve as an explicit API, defining what functionality is available and how it can be accessed. This simplifies usage and allows for internal refactoring without breaking external dependencies.

## 5. In-File Documentation Pattern

### 1. The File Header should follow this pattern

```md
"""
# PURPOSE

  [Detailed description of file's purpose and responsibilities.  Should clearly state the SINGLE responsibility of this module.]

## 1. INTERFACES

  [function_name(param_type) -> return_type]: [brief description]
  [If this file contains only ONE function, this section can be omitted. The function's docstring serves as the interface.]
  [For __init__.py files, this lists all functions EXPORTED by the module.]

## 2. DEPENDENCIES

  [file_path]: [What this component needs from the dependency]
  [For __init__.py files, list dependencies of the ENTIRE module, not just the index file itself.]
  [...]

## 3. TODO Tasks

  [Remove previously completed TODOs]
  [Add TODOs from Future TODOs]
  [...]

"""
```

### 2. All Code Entities should follow this pattern

```python
def calculate_final_invoice_amount(subtotal: float, tax_rate: float, discount_rate: float = 0.0) -> float:
  """
  CODE ENTITY PURPOSE:
    Calculates the final amount for an invoice, applying tax and optional discount.  (This should be a SINGLE, well-defined responsibility.)

  CONTEXT & DEPENDENCIES:
    No external imports needed (or list them here if they are truly local to this function)
    [...]

  PARAMS:
    subtotal (float): Base invoice amount, excluding tax.
    tax_rate (float): Rate applied to subtotal (e.g., 0.075 for 7.5%).
    discount_rate (float): Optional discount rate (defaults to 0.0).
    [...]

  RETURNS:
    float: Final invoice amount after tax and discount.
  """
  tax_amount = subtotal * tax_rate
  discount_amount = subtotal * discount_rate
  final_amount = subtotal + tax_amount - discount_amount
  return final_amount
```

### 3. The File Footer should follow this pattern

```md
"""
## Current Known Errors

  Debug colors aren't displayed properly - [Low]
  Config file is deleted automatically - [Critical]
  [...]

## Improvements Made

  [Specific improvements in this implementation session]
  [...]

## Future TODOs

  [Specific areas for future improvement]
  [Carry over any pending TODO items into the next file header update]
  [Use previous compliance percentages to measure incremental progress]
  [Prioritize improvements that have the highest impact on AI comprehension]
  [Establish clear iteration goals based on these assessments to guide refactoring]
  [Consider if this function should be further decomposed based on SRP.]
  [...]
"""
```

## 6. Key Metrics to Prioritize for AI-Driven Development

### 1. AI-Specific Quality Indicators

#### 1. Context Independence Score

-   **Context:** AI benefits from code that's understandable within limited context windows
-   **Target:** Maximum code understandability with minimal external context
-   **Priority:** Critical
-   **Implementation:**
    -   Ensure each file contains complete logic context in its header.
    -   Use descriptive, self-documenting names that encode domain knowledge.
    -   **Keep all related code within the same file when under size limits.  STRONGLY prioritize single-function files unless functions are inextricably linked.**
    -   Structure code to minimize dependencies on external components.
    -   **Use `__init__.py` files to create a clean namespace and expose only the necessary functions from a directory.**

#### 2. AI Insight Documentation

-   **Context:** AI generates valuable insights during development that need to be preserved for future reference
-   **Target:** Document 100% of significant AI-provided insights that impact design decisions
-   **Priority:** Critical
-   **Implementation:**
    -   Document AI-suggested rationales behind implementation choices
    -   Include dates or session references for traceability
    -   Create lightweight Project Architecture Overview files for multi-file projects
    -   Maintain cross-reference links between related components and their architectural documentation

#### 3. Implementation Pattern Consistency

-   **Context:** AI excels at pattern recognition and struggles with inconsistent approaches
-   **Target:** \> 90% consistency with established patterns
-   **Priority:** High
-   **Implementation:**
    -   Structure all files using the defined Header-Code-Footer template.
    -   Apply consistent design patterns and architectural solutions across similar problems.
    -   Maintain uniform method signatures, parameter ordering, and naming conventions.
    -   Follow standardized error handling and logging patterns across components.
    -   **Adhere to the one-function-per-file pattern, using `__init__.py` files to manage module interfaces.**

#### 4. Project Architecture Visibility

-   **Context:** AI benefits from understanding the overall structure when working on individual components
-   **Target:** Maintain high-level documentation showing system organization and component relationships
-   **Priority:** Medium
-   **Implementation:**
    -   **Leverage the directory structure to represent the project architecture.  Each directory should represent a logical grouping of functionality.**
    -   Create centralized architecture documentation (diagrams, relationship maps) and keep it minimal and high-level.
    -   Reference the architecture document in component headers *if necessary*, but prioritize self-contained files.
    -   Document component relationships and dependencies *within the `__init__.py` if they are complex*.
    -   Update architecture documentation when significant structural changes occur, but prefer small, incremental changes.

#### 5. Test Scenario Coverage (TSC)

- **Context**: AI needs comprehensive examples of correct behavior for each component
- **Target**: > 90% of business logic paths covered with explicit test scenarios
- **Priority**: Medium
- **Implementation**:
  - Create behavior-driven tests that document expected behavior and edge cases.
  - **Place tests in a separate `tests` directory, mirroring the structure of the source code.  For example, if you have `my_module/calculate_area.py`, you should have `tests/my_module/test_calculate_area.py`.**
  - Use descriptive naming conventions for methods and tests to help AI pinpoint tested logic.
  - Organize tests by feature with clear documentation of each test's purpose.
  - Ensure tests serve as executable documentation of component functionality.
  - **Each test file should focus on testing the corresponding function in the source code file.**

#### 6. Cross-Reference

-   **Context:** Refer to recognized language style guides (e.g., PEP 8) for standardized naming and "Design Patterns: Elements of Reusable Object-Oriented Software" (GoF) for common implementation patterns to maintain consistency
-   **Target:** Leverage widely recognized standards for naming and design to ensure code consistency
-   **Priority:** Medium
-   **Implementation:**
    -   Adopt recognized style guides and document deviations in file headers
    -   Follow established GoF design patterns where applicable
    -   Document any newly introduced patterns with clear usage examples
    -   Ensure consistency through automated linting and code reviews

### 2. File Organization & Documentation

#### 1. File Purpose Documentation

-   **Context:** AI requires explicit semantic understanding of each file's role within the project architecture
-   **Target:** Every file must begin with a clear, concise description of its purpose and responsibilities
-   **Priority:** Critical
-   **Implementation:**
    -   Begin each file with a docstring describing its purpose and architectural role
    -   Document relationships to other system components
    -   Document any applied design patterns or principles
    -   Include key dependencies and their required interfaces

#### 2. File Size

- **Context**: Critical for AI to maintain full context awareness within limited context windows
- **Target**: 200-300 lines per file (excluding documentation and whitespace)
- **Priority**: Low
- **Implementation**:
  - Monitor token count to stay within AI 16k context window limits.
  - **Split files exceeding size limits by identifying distinct responsibilities and creating new single-function files.  Update the `__init__.py` file accordingly.**
  - Maintain related functionality in single files when under limits.
  - Exclude documentation and whitespace from line count calculations.
  - **Prioritize single-function files.  This naturally limits file size.**

#### 3. Module Interface Documentation

- **Context**: AI requires explicit interface definitions to understand component relationships
- **Target**: 100% of public interfaces documented with input/output specifications
- **Priority**: High
- **Implementation**:
  - Document parameter types, return values, exceptions, and usage examples for all public methods.  This is primarily done within the function's docstring.
  - Specify preconditions and postconditions where applicable.
  - **Use the `__init__.py` file to clearly define the public API of the module.  This acts as the primary interface documentation.**
  - Maintain comprehensive interface documentation with real-world usage patterns (in the function docstrings).

### 3. Code Characteristics

#### 1. Semantic Naming

-   **Context:** AI relies heavily on meaningful naming patterns for code understanding
-   **Target:** All identifiers clearly express their purpose and role, even if this means longer, sentence-like names
-   **Priority:** Critical
-   **Implementation:**
    -   Use descriptive, domain-specific terminology in all identifiers (e.g., `calculate_total_tax_amount_for_invoice` instead of `calc_tax`)
    -   Follow consistent naming patterns with unit suffixes where appropriate (e.g., `delay_in_milliseconds`)
    -   Prioritize clarity over brevity, using full words and explicit context
    -   Include business domain terminology to enhance semantic understanding

#### 2. Function Size

-   **Context:** Smaller functions are easier for AI to comprehend fully
-   **Target:** Functions should be under 30 lines (excluding comments)
-   **Priority:** High
-   **Implementation:**
    -   Extract reusable logic into well-named helper functions, with each performing one logical operation. **Place these helper functions in separate files if they have independent utility.**
    -   Break complex algorithms into step-by-step functions.
    -   Use early returns to reduce nesting and complexity.
    -   Document any function exceeding size limits with clear justification, but this should be rare due to the single-function-per-file approach.

#### 3. Function Signature Clarity

-   **Context:** Self-documenting parameter names reduce misinterpretation by AI systems
-   **Target:** Parameter names must convey semantic meaning; parameters ≤ 4
-   **Priority:** High
-   **Implementation:**
    -   Use descriptive noun phrases for parameters (e.g., `customer_id` instead of `id`)
    -   Keep parameter count under 4, using parameter objects for complex interfaces
    -   Order parameters consistently (required before optional)
    -   Use named parameters when language supports them (e.g., Python's keyword arguments)

#### 4. Cyclomatic Complexity (CC)

-   **Context:** Lower complexity helps the AI analyze branching more efficiently
-   **Target:** CC \< 8 for most functions; functions exceeding CC 8 must be documented and justified
-   **Priority:** Medium
-   **Implementation:**
    -   Replace nested conditionals with guard clauses and early returns
    -   Split complex logical expressions into well-named helper functions
    -   Use polymorphism instead of switch/case blocks
    -   Monitor CC metrics via static analysis in CI pipelines

#### 5. Code Duplication

- **Context**: Duplicated logic creates inconsistent maintenance and increases context requirements
- **Target**: < 2% duplication across codebase
- **Priority**: Low
- **Implementation**:
  - **If duplication is detected, consider creating a new module (file) with a single function to encapsulate the duplicated logic.  Import this new function where needed.**
  - Extract common functionality into reusable utilities and shared base classes, placing them in appropriate modules.
  - Use design patterns like Template Method for similar procedures *if applicable*, but prioritize simple, direct solutions.
  - Regular refactoring sessions to identify and eliminate duplication.
  - Document any intentionally duplicated code with clear justification (this should be extremely rare).

### 4. Error Handling & Logging

#### 1. Traceability & Context Enrichment

- **Context**: AI benefits from explicit references to the failing component
- **Target**: Include relevant function and parameter info in error messages
- **Priority**: Critical
- **Implementation**:
  - Include context data (function names, sanitized parameters, correlation IDs) in error messages
  - Ensure logs contain sufficient data to reproduce issues
  - Maintain consistent error message format across the system
  - Include specific component references in stack traces

#### 2. Logging Standardization

- **Context**: Consistent logs help AI systems parse and correlate issue details quickly
- **Target**: Log messages must follow a uniform format (timestamp, severity, message, context)
- **Priority**: High
- **Implementation**:
  - Use consistent log format (timestamp, severity, message, context) across all components
  - Include relevant contextual information in every log entry
  - Document and enforce standard log levels (DEBUG, INFO, WARN, ERROR)
  - Use structured logging for machine-readable output

#### 3. Exception Management

- **Context**: AI depends on clear exception paths for debugging suggestions
- **Target**: All caught exceptions must either be handled or rethrown with meaningful context
- **Priority**: High
- **Implementation**:
  - Create custom exception types with domain-specific error messages and context
  - Log exceptions with appropriate severity and detailed diagnostic data
  - Include meaningful context when rethrowing exceptions
  - Avoid silently catching or discarding exceptions

#### 4. Error Recovery

- **Context**: AI can suggest improved solutions if the error path is well-defined
- **Target**: Graceful fallback when possible, with robust failure states otherwise
- **Priority**: Medium
- **Implementation**:
  - Document failure scenarios and recovery strategies
  - Implement circuit breakers for external dependencies
  - Provide clear user feedback during recovery
  - Only proceed after validating partial failure safety

## 7. Implementation Guidance

### 1. Project Initialization

-   **Context:** Establishing proper foundation at the beginning minimizes remediation work later
-   **Requirement:** Each new project must be set up with the complete framework structure in place
-   **Priority:** Low
-   **Implementation:**
    -   Create standardized project structure with framework-compliant templates and documentation.
    -   Configure automated tooling for style guide enforcement and metric tracking.
    -   Establish required header/footer patterns in project templates.
    -   **Include a `tests` directory mirroring the source code structure.**
    -   **Provide example `__init__.py` files to demonstrate how to create module interfaces.**
    -   Document project-specific deviations from framework defaults.

### 2. Development Workflow Integration

-   **Context:** Consistent application of principles requires workflow integration
-   **Requirement:** Ensure framework principles are integrated into the regular development process
-   **Priority:** Low
-   **Implementation:**
    -   Implement Separation of Concerns and Test-Driven Development practices.  **Test-Driven Development is particularly well-suited to the one-function-per-file approach.**
    -   Configure static analysis tools to prioritize AI-relevant metrics.
    -   Automate framework compliance checks in CI/CD pipeline.
    -   Document workflow integration steps in project templates.

### 3. No Fallback Methods Policy

-   **Context:** Prevents masking issues through deflection to alternative implementations
-   **Requirement:** Code must either work correctly, be fixed properly, or have a formal bug report filed upstream
-   **Priority:** Critical
-   **Implementation:**
    -   Document issue details and reproduction steps within affected code blocks
    -   Implement proper fixes rather than alternative implementations or workarounds
    -   Create detailed issue explanations in file headers when fixes aren't immediately possible
    -   Include status of known issues in the file's header and footer assessments

### 4. Refactoring Priority

-   **Context:** Existing patterns optimized for human comprehension may impair AI understanding
-   **Requirement:** When refactoring, prioritize changes that enhance AI comprehension over preserving existing style patterns
-   **Priority:** High
-   **Implementation:**
    -   Replace terse variable/function names with descriptive, context-rich alternatives
    -   Break complex functions into smaller, focused units with clear single responsibilities
    -   Maintain comprehensive in-file documentation to preserve context independence
    -   Review and update guidelines based on evolving AI capabilities

### 5. Framework Application Guidelines

-   **Context:** The Zeroth Law must scale effectively across projects of varying sizes and complexities
-   **Requirement:** Apply the framework flexibly, ensuring it enhances rather than hinders development
-   **Priority:** Medium
-   **Implementation:**
    -   **Small Projects**: For scripts or small modules, prioritize critical metrics like semantic naming and context independence. Use abbreviated headers if necessary, but ensure core principles are met. **The one-function-per-file approach is still highly recommended, even for small projects.**
    -   **Large Projects**: For multi-module systems, emphasize file organization, interface documentation, and cross-file consistency. Use the full header and footer templates to maintain clarity. **The directory structure and `__init__.py` files become even more critical for managing complexity.**
    -   **Rationale for Framework Size:** The framework exceeds 300 lines because it serves as a comprehensive reference, not a single file’s blueprint. It provides detailed guidance for all project sizes, ensuring consistency and adaptability.

## 8. Self-Assessment Process (For AI)

### 1. The "self" in "self-assessment" refers to the AI assistant, not the human developer. AI assistants should

1.  Generate code following Zeroth Law principles while tracking compliance metrics
2.  Evaluate generated code against framework metrics and document findings in file footers
3.  Use compliance percentages as general indicators rather than precise measurements
4.  Recommend specific improvements based on assessment findings

### 2. When returning to a file in future sessions, the AI should

1.  Review and implement pending improvements from the previous footer's assessment
2.  Update header and footer documentation to reflect current status and progress
3.  Perform comprehensive metric evaluation against framework standards
4.  Document specific recommendations for next iteration in footer

### 3. Self-Assessment Evolution

-   **Context:** The self-assessment process should evolve alongside the framework to remain effective
-   **Requirement:** Document and refine AI-driven self-assessment methods over time
-   **Priority:** Medium
-   **Implementation:**
    -   **Process Documentation:** AIs should record their self-assessment methods, including any templates or checklists used.
    -   **Refinement Mechanism:** Track changes to self-assessment templates or methods (e.g., via a version history or changelog) based on what proves effective.
    -   **AI Feedback Loop:** Encourage AIs to suggest improvements to the self-assessment process itself, fostering ongoing enhancement.

### 4. In practical terms, the AI should

1.  Evaluate components against metrics and provide specific, actionable feedback for any that fall below thresholds
2.  Track quality progress through the header-code-footer pattern, ensuring complete documentation
3.  Structure code to align with these principles from initial implementation
4.  Maintain clear metric assessments in file footers to guide future improvements

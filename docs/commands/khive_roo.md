# khive roo

## Overview

The `khive roo` command (short for "Role Operations") initializes and manages AI
agent role configurations within your project. It standardizes how AI personas,
their specific instructions, and system-wide guidance are defined and utilized.
It achieves this by setting up a `.khive/prompts` directory with default
templates and then using these user-customizable files to generate a local
`.roo/` rules directory and a `.roomodes` JSON manifest.

This manifest is intended for use by other tools or AI agents to select and
apply specific operational modes, ensuring consistent and context-aware AI
interactions.

## Key Features

- **Project-Centric Configuration:** Manages role definitions and prompts within
  the project's `.khive/prompts` directory.
- **Template-Based Initialization:** Bootstraps `.khive/prompts` with default
  templates for roles, invocation, and guidance if not already present.
- **Rule Materialization:** Copies customized role definitions from
  `.khive/prompts/roo_rules/` to a project-local `.roo/` directory.
- **Mode Manifest Generation:** Creates a `.roomodes` JSON file in the project
  root, compiling all role configurations into a machine-readable format.
- **User Customization:** Users can easily edit the Markdown files in
  `.khive/prompts` to tailor AI behaviors.
- **Idempotent Operations:** Safely re-runnable; initialization respects
  existing files, while generation overwrites target outputs.

## Usage

```bash
khive roo [options]
```

## Options

| Option                | Description                                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `--project-root PATH` | Path to the project root directory (default: Git repository root or CWD).                                   |
| `--force-init`        | Force re-copying of default templates into `.khive/prompts/`, overwriting existing files. Use with caution. |
| `--json-output`       | Output results in JSON format.                                                                              |
| `--dry-run`, `-n`     | Show what would be done without creating/modifying files or directories.                                    |
| `--verbose`, `-v`     | Enable verbose logging for detailed information.                                                            |

## Configuration

`khive roo` uses a minimal set of configurations, primarily relying on the file
structure within `.khive/prompts/`. However, a `.khive/roo.toml` file can be
used for future extensions, though none are defined currently.

### Default File Structure (Managed by `khive roo`)

Upon first run (or if `.khive/prompts` is missing), `khive roo` will attempt to
create/populate:

- **`PROJECT_ROOT/.khive/prompts/`**:
  - `invokation.md`: Core prompt used to invoke the AI.
  - `general_guidance.md`: System-wide instructions applicable to all roles.
  - `khive_system_context.md`: Contextual information about the khive framework
    or project.
  - `roo_rules/`: Directory containing individual role definition Markdown
    files.
    - `example_coder_mode.md` (default template)
    - `example_reviewer_mode.md` (default template)
    - _(Users add their own `*.md` files here)_

The command then generates:

- **`PROJECT_ROOT/.roo/`**: A direct copy of
  `PROJECT_ROOT/.khive/prompts/roo_rules/`. This directory is always
  overwritten.
- **`PROJECT_ROOT/.roomodes`**: A JSON file consolidating all defined modes from
  the `.roo/` directory, combined with content from `invokation.md`,
  `general_guidance.md`, and `khive_system_context.md`. This file is always
  overwritten.

## Workflow

1. **Initialization**:
   - Checks for `PROJECT_ROOT/.khive/prompts/`.
   - If missing, it (or missing essential sub-files/directories) are created and
     populated with default templates bundled with the `khive` package.
   - The `--force-init` flag can be used to overwrite existing files in
     `.khive/prompts/` with the defaults.
2. **Rule Synchronization**:
   - The content of `PROJECT_ROOT/.khive/prompts/roo_rules/` is copied to
     `PROJECT_ROOT/.roo/`.
   - Any existing content in `PROJECT_ROOT/.roo/` is removed before copying.
3. **Mode Generation**:
   - The script parses each `.md` file within the (newly synchronized)
     `PROJECT_ROOT/.roo/` directory.
   - For each rule file, it extracts YAML front-matter (slug, name, groups) and
     specific "Role Definition" and "Custom Instructions" sections.
   - It combines these with the global content from `invokation.md`,
     `general_guidance.md`, and `khive_system_context.md` found in
     `PROJECT_ROOT/.khive/prompts/`.
   - The resulting mode definitions are compiled into the
     `PROJECT_ROOT/.roomodes` JSON file.

## Role Definition File Format (`*.md` in `roo_rules/`)

Each mode is defined in a Markdown file with YAML front-matter and specific
H2/H3 sections:

```markdown
---
slug: "custom_analyst" # Unique identifier for the mode
name: "📊 Data Analyst Pro" # Human-readable name, supports emojis
groups: ["analysis", "data"] # Optional list of group tags
source: "project_specific" # Optional, defaults to "project"
---

## Role Definition

You are a senior data analyst. Your primary function is to interpret complex
datasets, identify trends, and provide actionable insights.

## Custom Instructions

- Ensure all charts are clearly labeled.
- Provide confidence intervals where appropriate.
- Summarize key findings in bullet points.
```

## `.roomodes` JSON Format

The generated `.roomodes` file has the following structure:

```json
{
  "customModes": [
    {
      "slug": "custom_analyst",
      "name": "📊 Data Analyst Pro",
      "groups": ["analysis", "data"],
      "source": "project_specific",
      "roleDefinition": "You are an advanced AI assistant...\n\nYou are a senior data analyst...", // Combined content
      "customInstructions": "Ensure all charts are clearly labeled...\n\n- Be concise..." // Combined content
    }
    // ... other modes
  ]
}
```

## Examples

```bash
# Initialize .khive/prompts if not present, then generate .roo/ and .roomodes
khive roo

# Force re-initialization of .khive/prompts with default templates, then generate
khive roo --force-init

# See what the command would do without making changes
khive roo --dry-run

# Enable verbose logging for detailed output during generation
khive roo --verbose

# Get structured JSON output about the operation (useful for scripting)
khive roo --json-output
```

## JSON Output Format (for the `khive roo` command itself)

When using `--json-output`, the command provides feedback on its own execution:

```json
{
  "status": "success", // "success", "failure", "partial_success"
  "message": "Khive Roo processing completed successfully. 2 modes generated.",
  "actions_taken": [
    {
      "action": "initialize_khive_structure",
      "status": "OK",
      "details": "'.khive/prompts' initialized with default templates."
    },
    {
      "action": "synchronize_target_roo_folder",
      "status": "OK",
      "details": "Copied 2 rule files to '.roo/'."
    },
    {
      "action": "generate_roomodes_file",
      "status": "OK",
      "details": "Generated '.roomodes' with 2 modes."
    }
  ],
  "generated_roomodes_path": "/path/to/project/.roomodes",
  "generated_roo_path": "/path/to/project/.roo"
}
```

## Error Handling

`khive roo` provides informative messages for:

- Missing `PyYAML` dependency.
- Failures in creating directories or copying files.
- Errors during parsing of `.md` rule files (e.g., malformed YAML).
- Missing essential template files (`invokation.md`, etc.) in `.khive/prompts/`
  if they cannot be restored.

## Exit Codes

- `0`: Operation completed successfully.
- `1`: An error occurred during the process.

## Notes

- Users should primarily edit files within their project's `.khive/prompts/`
  directory.
- The `.roo/` directory and `.roomodes` file in the project root are considered
  build artifacts and will be overwritten by `khive roo`.
- The default templates provide a starting point; users are encouraged to
  customize them heavily.
- The `PyYAML` library is required for parsing the front-matter in rule files.

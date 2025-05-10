# khive new-doc

## Overview

The `khive new-doc` command creates standardized Markdown documents from
templates. It handles template discovery across multiple locations, placeholder
substitution with custom variables, and output file creation. This tool is
essential for maintaining consistent documentation across the khive project.

## Usage

```bash
khive new-doc [type_or_template_name] [identifier] [options]
khive new-doc --list-templates [options]
```

## Options

| Option                  | Description                                                                      |
| ----------------------- | -------------------------------------------------------------------------------- |
| `type_or_template_name` | Document type (e.g., 'CRR', 'TDS') or template filename (e.g., 'RR_template.md') |
| `identifier`            | Identifier/slug for the new document (e.g., '001-new-api')                       |
| `--dest PATH`           | Output base directory (overrides config default_destination_base_dir)            |
| `--template-dir PATH`   | Additional directory to search for templates (highest priority)                  |
| `--var KEY=VALUE`       | Set custom variables for template substitution (can be repeated)                 |
| `--force`               | Overwrite output file if it already exists                                       |
| `--project-root PATH`   | Project root directory (default: git root or current directory)                  |
| `--json-output`         | Output results in JSON format                                                    |
| `--dry-run`, `-n`       | Show what would be done without creating files                                   |
| `--verbose`, `-v`       | Enable verbose logging                                                           |
| `--list-templates`      | List all discoverable templates                                                  |

## Configuration

`khive new-doc` can be configured using a TOML file located at
`.khive/new_doc.toml` in your project root. All configuration options are
optional and will use sensible defaults if not specified.

### Configuration Options

```toml
# .khive/new_doc.toml

# Base directory for document output (default: "reports")
default_destination_base_dir = "reports"

# Additional template directories (relative to project root or absolute paths)
custom_template_dirs = ["templates", "/abs/path/templates"]

# Default variables for all templates
[default_vars]
author = "Your Name"
project = "Project Name"
```

### Configuration Precedence

CLI arguments override configuration file settings. For example, if custom
variables are defined in both the configuration file and via `--var` arguments,
the CLI values take precedence.

## Template Discovery

Templates are discovered in the following locations (in order of priority):

1. Directory specified with `--template-dir` (highest priority)
2. Directories listed in `custom_template_dirs` in the configuration file
3. Directory specified in the `KHIVE_TEMPLATE_DIR` environment variable
4. Default search paths relative to project root:
   - `docs/templates`
   - `dev/docs/templates`
   - `.khive/templates`
5. Templates directory relative to the script itself (fallback)

## Template Format

Templates are Markdown files with YAML front-matter. The front-matter defines
metadata about the template, and the body contains the content with
placeholders.

```markdown
---
doc_type: RR
title: "Research Report"
output_subdir: rr
filename_prefix: RR
---

# Research Report: {{IDENTIFIER}}

## 1. Overview

Research conducted by: {{author}} Date: {{DATE}}

## 2. Findings

...
```

### Front-matter Fields

| Field             | Description                      | Default               |
| ----------------- | -------------------------------- | --------------------- |
| `doc_type`        | Type identifier for the document | Derived from filename |
| `title`           | Human-readable title             | Derived from filename |
| `output_subdir`   | Subdirectory for output files    | `{doc_type.lower()}s` |
| `filename_prefix` | Prefix for generated filenames   | `doc_type.upper()`    |

## Placeholder Substitution

The following placeholders are automatically substituted:

| Placeholder      | Description                                                            |
| ---------------- | ---------------------------------------------------------------------- |
| `{{DATE}}`       | Current date in ISO format (YYYY-MM-DD)                                |
| `{{IDENTIFIER}}` | The identifier provided as command-line argument                       |
| `{{KEY}}`        | Any custom variable provided via `--var KEY=VALUE` or in configuration |

Placeholders can also use alternative formats:

- `{KEY}` (single braces)
- `<key>` (angle brackets, case-insensitive)

## Examples

```bash
# Create a new Research Report with ID "16-khive-new-doc-overhaul"
khive new-doc RR 16-khive-new-doc-overhaul --var author="John Doe"

# List all available templates
khive new-doc --list-templates

# Create a document using a specific template file
khive new-doc RR_template.md 16-feature-name --var author="Jane Smith"

# Preview document without creating it
khive new-doc TDS 17-new-feature --dry-run --verbose

# Force overwrite an existing document
khive new-doc QA 16-feature-review --force

# Output in JSON format (useful for scripting)
khive new-doc IP 18-new-component --json-output
```

## Output Structure

The generated document will:

1. Include all front-matter from the template
2. Add a `date` field with the current date
3. Substitute all placeholders in both front-matter and body
4. Be saved to
   `{default_destination_base_dir}/{output_subdir}/{filename_prefix}-{identifier}.md`

For example, using the RR template with identifier "16-feature" might create:
`reports/rr/RR-16-feature.md`

## Error Handling

`khive new-doc` provides detailed error messages when things go wrong:

- Missing templates are reported with available alternatives
- File existence conflicts are reported with instructions to use `--force`
- Configuration errors are reported with helpful context

## Exit Codes

- `0`: Document created successfully or templates listed
- `1`: Error occurred (template not found, file already exists, etc.)

## Notes

- Custom variables can be used to override any front-matter field
- The `--dry-run` option is useful for previewing the document before creation
- Use `--verbose` with `--dry-run` to see the full document content

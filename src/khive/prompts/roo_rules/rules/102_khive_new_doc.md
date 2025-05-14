# khive new-doc

## Overview

The `khive new-doc` command creates standardized Markdown documents from
templates. It handles template discovery across multiple locations, placeholder
substitution with custom variables, and output file creation. This tool is
essential for maintaining consistent documentation across the khive project.

please always use issue number as the identifier, and use `khive new-doc` to
create the report. The official location of the reports is `.khive/reports/`,
and typically we recommend add `.khive` to .gitignore, so your prompts, configs
won't be in repo, unless you intend to version control them or share them with
others. If `.khive` is already in .gitignore, you don't need to commit the
report.

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

## Exit Codes

- `0`: Document created successfully or templates listed
- `1`: Error occurred (template not found, file already exists, etc.)

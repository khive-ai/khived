#!/usr/bin/env python3
import json
import logging
import os
import re
from pathlib import Path

import yaml  # Requires PyYAML: pip install PyYAML

from .utils import read_md_body

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ROO_FOLDER = "docs/roo"
INVOKCATION_PROMPT = "docs/prompts/invokation.md"

GENERAL_GUIDANCE = "docs/guides/general_guidance.md"
khive_doc = Path(__file__).parent / "readme.txt"


khive_doc = khive_doc.read_text()
OUTPUT_JSON = ".roomodes"


def parse_markdown_file(filepath):
    """
    Parse a single .md file expecting:
    1) A YAML front matter between --- and ---
    2) A '## Role Definition' section
    3) A '## Custom Instructions' section

    Returns a dict with keys:
      slug, name, groups, source, roleDefinition, customInstructions
    or raises an error if parsing fails.
    """

    if not os.path.exists(GENERAL_GUIDANCE):
        logging.error(
            f"CRITICAL: General guidance file '{GENERAL_GUIDANCE}' does not exist."
        )
        return
    if not os.path.isfile(GENERAL_GUIDANCE):
        logging.error(f"CRITICAL: '{GENERAL_GUIDANCE}' is not a file.")
        return

    logging.debug(f"Attempting to parse: {filepath}")
    try:
        # Read the file explicitly with UTF-8 encoding
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"Error reading file {filepath}: {e}")

    # --- Extract YAML front matter ---
    # More robust pattern supporting potential leading/trailing spaces and ensuring full match
    front_matter_pattern = re.compile(r"\A---\s*(.*?)\s*---", re.DOTALL)
    match = front_matter_pattern.search(content)
    if not match:
        raise ValueError(
            f"Could not find valid YAML front matter (starting with '---') in {filepath}"
        )

    front_matter_text = match.group(1)
    remaining_md = content[match.end() :].strip()  # Content after front matter

    # Parse YAML
    try:
        front_matter_data = yaml.safe_load(front_matter_text)
        if not isinstance(front_matter_data, dict):
            raise ValueError("Front matter YAML did not parse as a dictionary.")
        logging.debug(f"Parsed front matter for {filepath}: {front_matter_data}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML front matter in {filepath}: {e}")

    # --- Extract "## Role Definition" and "## Custom Instructions" ---
    # Using regex that matches markdown headings (## or ###)
    def extract_section(text, heading):
        """
        Returns the text following a specific '## Heading' or '### Heading',
        stopping at the next '## ' or '### ' or end of text.
        """
        # Match heading line, capture content until next heading or end of string (\Z)
        pattern = re.compile(
            rf"^[#]{{2,3}}\s+{re.escape(heading)}\s*(.*?)(?=\n^[#]{{2,3}}\s+|\Z)",
            re.DOTALL | re.MULTILINE,
        )
        match_sec = pattern.search(text)
        if match_sec:
            return match_sec.group(1).strip()
        logging.warning(f"Heading '## {heading}' not found in {filepath}")
        return ""  # Return empty string if heading not found

    invokation_prompt_text = read_md_body(INVOKCATION_PROMPT)
    role_def_text = invokation_prompt_text + extract_section(
        remaining_md, "Role Definition"
    )

    fp = Path(GENERAL_GUIDANCE)
    general_guidance_text = read_md_body(fp)

    custom_instructions_text = (
        extract_section(remaining_md, "Custom Instructions")
        + "\n\n"
        + general_guidance_text
        + "\n\n"
        + khive_doc
    ).strip()

    # --- Assemble Final Data ---
    # Use filename as default slug if not provided
    default_slug = os.path.splitext(os.path.basename(filepath))[0]
    mode_data = {
        "slug": front_matter_data.get("slug", default_slug),
        "name": front_matter_data.get("name", ""),  # Emojis will be preserved here
        "groups": front_matter_data.get("groups", []),
        "source": front_matter_data.get("source", "project"),
        "roleDefinition": role_def_text,
        "customInstructions": custom_instructions_text,
    }

    # Validate required fields were found or defaulted correctly
    if not mode_data["slug"]:
        raise ValueError(
            f"Missing 'slug' and cannot derive from filename for {filepath}"
        )
    if not mode_data["name"]:
        logging.warning(f"Missing 'name' in front matter for {filepath}")
    if not mode_data["roleDefinition"]:
        logging.warning(f"Missing '## Role Definition' section in {filepath}")
    if not mode_data["customInstructions"]:
        logging.warning(f"Missing '## Custom Instructions' section in {filepath}")

    return mode_data


def main():
    # Verify PyYAML dependency early
    try:
        import yaml
    except ImportError:
        logging.error("CRITICAL: PyYAML library not found. Please install it using:")
        logging.error("  pip install PyYAML")
        exit(1)  # Exit if critical dependency is missing

    if not os.path.exists(ROO_FOLDER):
        logging.error(
            f"CRITICAL: Source folder '{ROO_FOLDER}' does not exist. Please create it and add your .md files."
        )
        return
    if not os.path.isdir(ROO_FOLDER):
        logging.error(f"CRITICAL: '{ROO_FOLDER}' is not a directory.")
        return

    custom_modes = []
    logging.info(f"Scanning for .md files in '{os.path.abspath(ROO_FOLDER)}'...")

    files_found = False
    # Sort files for consistent processing order (helpful for debugging/diffs)
    for filename in sorted(os.listdir(ROO_FOLDER)):
        if filename.lower().endswith(".md"):
            files_found = True
            filepath = os.path.join(ROO_FOLDER, filename)
            logging.info(f"Processing: {filename}")
            try:
                mode_data = parse_markdown_file(filepath)
                custom_modes.append(mode_data)
                logging.info(f"  -> Parsed successfully (slug='{mode_data['slug']}')")
            except (ValueError, IOError, yaml.YAMLError) as e:
                logging.error(
                    f"  -> Failed to parse {filename}: {e}"
                )  # Log error and continue

    if not files_found:
        logging.warning(
            f"No .md files found in '{ROO_FOLDER}'. Output JSON will be empty."
        )

    output_data = {"customModes": custom_modes}

    try:
        # Write the JSON file explicitly with UTF-8 encoding
        # and ensure_ascii=False to keep emojis and non-ASCII characters as-is
        with open(OUTPUT_JSON, "w", encoding="utf-8") as out_file:
            json.dump(
                output_data, out_file, indent=2, ensure_ascii=False
            )  # Key change here!
        logging.info(
            f"\nSuccessfully wrote {len(custom_modes)} modes to '{OUTPUT_JSON}'"
        )
    except Exception as e:
        logging.error(f"\nCRITICAL: Error writing JSON output to '{OUTPUT_JSON}': {e}")


if __name__ == "__main__":
    main()

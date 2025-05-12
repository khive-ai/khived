# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import importlib.resources
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # Requires PyYAML: pip install PyYAML
except ImportError:
    logging.critical(
        "CRITICAL: PyYAML library not found. Please install it: pip install PyYAML"
    )
    # In a real CLI, you might exit here or handle it differently.
    # For this script, we'll let it fail later if yaml is used without being imported.


# --- Configuration ---
# Logging setup should ideally be done by the main CLI application
# For this standalone script, we'll configure it here.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - KhiveRoo: %(message)s"
)

# Constants for directory and file names (relative to project root or .khive)
KHIVE_DIR_NAME = ".khive"
PROMPTS_DIR_NAME = "prompts"
ROO_RULES_DIR_NAME = "roo_rules"
TEMPLATES_DIR_NAME = "templates"
TARGET_ROO_DIR_NAME = ".roo"  # This is generated in the project root
OUTPUT_JSON_NAME = ".roomodes"  # This is generated in the project root


# --- Helper Functions ---
def get_project_root() -> Path:
    """Determines the project root. Uses Git root if available, otherwise CWD."""
    try:
        git_root_bytes = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.PIPE
        )
        return Path(git_root_bytes.strip().decode("utf-8"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.warning(
            "Not a git repository or git command not found. Using current working directory as project root."
        )
        return Path.cwd()


class KhiveRooManager:
    """Manages the creation and updating of .roo configurations and .roomodes."""

    def __init__(self, project_root_override: Path | None = None):
        self.project_root: Path = project_root_override or get_project_root()
        logging.info(f"Operating on project root: {self.project_root.resolve()}")

        # .khive directory structure
        self.khive_dir: Path = self.project_root / KHIVE_DIR_NAME
        self.khive_prompts_dir: Path = self.khive_dir / PROMPTS_DIR_NAME
        self.source_roo_rules_dir: Path = self.khive_prompts_dir / ROO_RULES_DIR_NAME
        self.source_templates_dir: Path = self.khive_prompts_dir / TEMPLATES_DIR_NAME

        # Target paths (generated in project_root)
        self.target_roo_dir: Path = self.project_root / TARGET_ROO_DIR_NAME
        self.output_json_path: Path = self.project_root / OUTPUT_JSON_NAME

    def _get_package_source_path(self) -> Path | None:
        """Gets the path to the bundled source templates within the khive package."""
        try:
            # Try to get the path from the installed package
            return importlib.resources.files("khive.prompts")
        except (ModuleNotFoundError, AttributeError):
            logging.warning(
                "Could not locate package templates via importlib.resources. "
                "Falling back to development path."
            )

        # Fallback for development (if running from source, not installed package)
        dev_path = Path(__file__).resolve().parent.parent / "prompts"
        if dev_path.is_dir():
            logging.info(f"Using development path for templates: {dev_path.resolve()}")
            return dev_path

        logging.error("Source templates directory not found.")
        return None

    def initialize_khive_structure(self) -> bool:
        """Ensures .khive/prompts and its contents are set up, copying from package templates if needed."""
        # Create .khive directory if it doesn't exist
        if not self.khive_dir.exists():
            logging.info(
                f"Creating '{KHIVE_DIR_NAME}' directory at {self.khive_dir.resolve()}"
            )
            self.khive_dir.mkdir()

        # Create .khive/prompts directory if it doesn't exist
        if not self.khive_prompts_dir.exists():
            logging.info(
                f"Creating '{PROMPTS_DIR_NAME}' directory in {self.khive_dir.resolve()}"
            )
            self.khive_prompts_dir.mkdir()

        # Get the source path for templates
        source_path = self._get_package_source_path()
        if not source_path:
            logging.error(
                "Failed to locate source templates. Cannot initialize .khive structure."
            )
            return False

        # Copy roo_rules if it doesn't exist or is empty
        if not self.source_roo_rules_dir.exists() or not any(
            self.source_roo_rules_dir.iterdir()
        ):
            source_roo_rules = source_path / ROO_RULES_DIR_NAME
            if source_roo_rules.exists() and source_roo_rules.is_dir():
                logging.info(
                    f"Copying roo_rules from {source_roo_rules} to {self.source_roo_rules_dir}"
                )
                try:
                    if self.source_roo_rules_dir.exists():
                        shutil.rmtree(self.source_roo_rules_dir)
                    shutil.copytree(source_roo_rules, self.source_roo_rules_dir)
                except Exception as e:
                    logging.exception(f"Failed to copy roo_rules: {e}")
                    return False
            else:
                logging.error(
                    f"Source roo_rules directory not found at {source_roo_rules}"
                )
                return False

        # Copy templates if it doesn't exist or is empty
        if not self.source_templates_dir.exists() or not any(
            self.source_templates_dir.iterdir()
        ):
            source_templates = source_path / TEMPLATES_DIR_NAME
            if source_templates.exists() and source_templates.is_dir():
                logging.info(
                    f"Copying templates from {source_templates} to {self.source_templates_dir}"
                )
                try:
                    if self.source_templates_dir.exists():
                        shutil.rmtree(self.source_templates_dir)
                    shutil.copytree(source_templates, self.source_templates_dir)
                except Exception as e:
                    logging.exception(f"Failed to copy templates: {e}")
                    return False
            else:
                logging.error(
                    f"Source templates directory not found at {source_templates}"
                )
                return False

        return True

    def synchronize_target_roo_folder(self) -> bool:
        """Copies rules from .khive/prompts/roo_rules/ to .roo/, overwriting .roo/."""
        if not self.source_roo_rules_dir.is_dir():
            logging.error(
                f"Source rules directory '{self.source_roo_rules_dir.resolve()}' does not exist. "
                "Cannot synchronize. Run initialization or check your .khive setup."
            )
            return False

        if self.target_roo_dir.exists():
            logging.info(f"Removing existing target '{self.target_roo_dir.resolve()}'.")
            try:
                shutil.rmtree(self.target_roo_dir)
            except Exception as e:
                logging.exception(
                    f"Failed to remove '{self.target_roo_dir.resolve()}': {e}"
                )
                return False

        logging.info(
            f"Copying rules from '{self.source_roo_rules_dir.resolve()}' to '{self.target_roo_dir.resolve()}'."
        )
        try:
            shutil.copytree(self.source_roo_rules_dir, self.target_roo_dir)
            return True
        except Exception as e:
            logging.exception(
                f"Error copying to '{self.target_roo_dir.resolve()}': {e}"
            )
            return False

    def _parse_mode_readme(self, filepath: Path) -> dict | None:
        """Parses a mode readme file to extract mode data."""
        logging.debug(f"Parsing mode readme: {filepath.resolve()}")
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            logging.exception(f"Error reading file {filepath.resolve()}: {e}")
            return None

        # Extract YAML front matter
        front_matter_pattern = re.compile(r"\A---\s*(.*?)\s*---", re.DOTALL)
        fm_match = front_matter_pattern.search(content)
        if not fm_match:
            logging.warning(
                f"Could not find YAML front matter in {filepath.name}. Skipping."
            )
            return None

        front_matter_text = fm_match.group(1)
        remaining_md = content[fm_match.end() :].strip()

        try:
            front_matter_data = yaml.safe_load(front_matter_text)
            if not isinstance(front_matter_data, dict):
                raise ValueError("Front matter YAML did not parse as a dictionary.")
        except yaml.YAMLError as e:
            logging.warning(f"Error parsing YAML in {filepath.name}: {e}. Skipping.")
            return None
        except ValueError as e:
            logging.warning(
                f"Invalid YAML structure in {filepath.name}: {e}. Skipping."
            )
            return None

        # Extract Role Definition and Custom Instructions sections
        def extract_section(text: str, heading: str) -> str:
            pattern = re.compile(
                rf"^[#]{{2,3}}\s+{re.escape(heading)}\s*(.*?)(?=\n^[#]{{2,3}}\s+|\Z)",
                re.DOTALL | re.MULTILINE,
            )
            sec_match = pattern.search(text)
            return sec_match.group(1).strip() if sec_match else ""

        role_def_text = extract_section(remaining_md, "Role Definition")
        custom_instructions_text = extract_section(remaining_md, "Custom Instructions")

        # Determine slug and name
        default_slug = (
            filepath.parent.name
            if filepath.name.lower() in ["_mode_instruction.md", "readme.md"]
            else filepath.stem
        )

        mode_data = {
            "slug": front_matter_data.get("slug", default_slug),
            "name": front_matter_data.get(
                "name", default_slug.replace("_", " ").title()
            ),
            "groups": front_matter_data.get("groups", []),
            "source": front_matter_data.get("source", "project"),
            "roleDefinition": role_def_text,
            "customInstructions": custom_instructions_text,
        }

        # Validate required fields
        if not mode_data["slug"]:
            logging.warning(
                f"Mode 'slug' is empty for {filepath.name}. Using directory name."
            )
            mode_data["slug"] = filepath.parent.name

        if not mode_data["name"]:
            logging.warning(
                f"Mode 'name' is empty for slug '{mode_data['slug']}' in {filepath.name}."
            )

        if not role_def_text:
            logging.warning(
                f"'## Role Definition' section empty or not found for slug '{mode_data['slug']}' in {filepath.name}."
            )

        if not custom_instructions_text:
            logging.warning(
                f"'## Custom Instructions' section empty or not found for slug '{mode_data['slug']}' in {filepath.name}."
            )

        return mode_data

    def generate_roomodes_file(self) -> bool:
        """Generates the .roomodes JSON file from mode readme files in the target .roo/ directory."""
        if "yaml" not in sys.modules:
            logging.critical("PyYAML is not available. Cannot parse mode files.")
            return False

        if not self.target_roo_dir.is_dir():
            logging.error(
                f"Target rules directory '{self.target_roo_dir.resolve()}' does not exist. "
                "Cannot generate .roomodes. Ensure synchronization step ran successfully."
            )
            return False

        custom_modes = []
        mode_dirs_found = False
        logging.info(
            f"Scanning for mode directories in '{self.target_roo_dir.resolve()}'..."
        )

        # Look for mode directories (rules-* or other directories with _MODE_INSTRUCTION.md or readme.md)
        for item in sorted(self.target_roo_dir.iterdir()):
            if item.is_dir():
                # Check if this is a mode directory
                mode_readme = None
                for readme_name in ["_MODE_INSTRUCTION.md", "readme.md", "README.md"]:
                    potential_readme = item / readme_name
                    if potential_readme.exists() and potential_readme.is_file():
                        mode_readme = potential_readme
                        break

                if mode_readme:
                    mode_dirs_found = True
                    logging.info(f"Processing mode directory: {item.name}")
                    mode_data = self._parse_mode_readme(mode_readme)
                    if mode_data:
                        custom_modes.append(mode_data)
                        logging.info(
                            f"  -> Parsed successfully (slug='{mode_data['slug']}')"
                        )
                    else:
                        logging.warning(
                            f"  -> Failed to parse or skipped {mode_readme.name}"
                        )

        # Also check for standalone mode files at the top level
        for item in sorted(self.target_roo_dir.iterdir()):
            if item.is_file() and item.name.lower().endswith(".md"):
                # Skip files that are clearly not mode files
                if item.name.lower() in [
                    "readme.md",
                    "index.md",
                    "contributing.md",
                    "license.md",
                ]:
                    continue

                logging.info(f"Processing potential mode file: {item.name}")
                mode_data = self._parse_mode_readme(item)
                if mode_data:
                    custom_modes.append(mode_data)
                    logging.info(
                        f"  -> Parsed successfully (slug='{mode_data['slug']}')"
                    )
                else:
                    logging.warning(f"  -> Failed to parse or skipped {item.name}")

        if not mode_dirs_found and not custom_modes:
            logging.warning(
                f"No mode directories or files found in '{self.target_roo_dir.resolve()}'. Output JSON will be empty."
            )

        output_data = {"customModes": custom_modes}

        try:
            with open(self.output_json_path, "w", encoding="utf-8") as out_file:
                json.dump(output_data, out_file, indent=2, ensure_ascii=False)
            logging.info(
                f"Successfully wrote {len(custom_modes)} modes to '{self.output_json_path.resolve()}'"
            )
            return True
        except Exception as e:
            logging.exception(
                f"CRITICAL: Error writing JSON to '{self.output_json_path.resolve()}': {e}"
            )
            return False

    def run(self) -> int:
        """Executes the full khive roo process."""
        if not self.initialize_khive_structure():
            logging.warning(
                "Failed to fully initialize .khive structure. "
                "Process may continue with existing files, but defaults might be missing."
            )
            # Decide if this should be a fatal error. For now, let's try to continue.

        if not self.synchronize_target_roo_folder():
            logging.error("Failed to synchronize target .roo folder. Aborting.")
            return 1

        if not self.generate_roomodes_file():
            logging.error("Failed to generate .roomodes file. Aborting.")
            return 1

        logging.info("Khive Roo processing completed successfully.")
        return 0


def main():
    """
    Main entry point for the khive roo command.
    This would be called by your CLI framework (e.g., Typer, Click).
    """
    # Add argparse here if CLI options are needed in the future
    # For now, it runs with default behavior.
    manager = KhiveRooManager()
    exit_code = manager.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    # This allows the script to be run directly for development/testing
    print("Running KhiveRooManager directly (intended for 'khive roo' CLI command)...")
    manager = KhiveRooManager()
    return_code = manager.run()
    if return_code == 0:
        print("Khive Roo generation finished successfully.")
    else:
        print(f"Khive Roo generation failed with code: {return_code}")

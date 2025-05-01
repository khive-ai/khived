import importlib.util
import json
import string
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    PythonVersion,
    generate,
)
from pydantic import BaseModel, PydanticUserError

I = TypeVar("I")


__all__ = (
    "import_module",
    "load_pydantic_model_from_schema",
)


def import_module(
    package_name: str,
    module_name: str = None,
    import_name: str | list = None,
) -> I | list[I]:
    """Import a module by its path."""
    try:
        full_import_path = (
            f"{package_name}.{module_name}" if module_name else package_name
        )

        if import_name:
            import_name = (
                [import_name] if not isinstance(import_name, list) else import_name
            )
            a = __import__(
                full_import_path,
                fromlist=import_name,
            )
            if len(import_name) == 1:
                return getattr(a, import_name[0])
            return [getattr(a, name) for name in import_name]
        return __import__(full_import_path)

    except ImportError as e:
        raise ImportError(f"Failed to import module {full_import_path}: {e}") from e


def load_pydantic_model_from_schema(
    schema: str | dict[str, Any],
    model_name: str = "DynamicModel",
    pydantic_version: DataModelType = DataModelType.PydanticV2BaseModel,
    python_version: PythonVersion = PythonVersion.PY_310,
) -> type[BaseModel]:
    """
    Generates a Pydantic model class dynamically from a JSON schema string or dict,
    and ensures it's fully resolved using model_rebuild() with the correct namespace.

    Args:
        schema: The JSON schema as a string or a Python dictionary.
        model_name: The desired base name for the generated Pydantic model.
                    If the schema has a 'title', that will likely be used.
        pydantic_version: The Pydantic model type to generate.
        python_version: The target Python version for generated code syntax.

    Returns:
        The dynamically created and resolved Pydantic BaseModel class.

    Raises:
        ValueError: If the schema is invalid.
        FileNotFoundError: If the generated model file is not found.
        AttributeError: If the expected model class cannot be found.
        RuntimeError: For errors during generation, loading, or rebuilding.
        Exception: For other potential errors.
    """
    schema_input_data: str
    schema_dict: dict[str, Any]
    resolved_model_name = model_name  # Keep track of the potentially updated name

    # --- 1. Prepare Schema Input ---
    if isinstance(schema, dict):
        try:
            model_name_from_title = schema.get("title")
            if model_name_from_title and isinstance(model_name_from_title, str):
                valid_chars = string.ascii_letters + string.digits + "_"
                sanitized_title = "".join(
                    c
                    for c in model_name_from_title.replace(" ", "")
                    if c in valid_chars
                )
                if sanitized_title and sanitized_title[0].isalpha():
                    resolved_model_name = sanitized_title  # Update the name to use
            schema_dict = schema
            schema_input_data = json.dumps(schema)
        except TypeError as e:
            raise ValueError(f"Invalid dictionary provided for schema: {e}")
    elif isinstance(schema, str):
        try:
            schema_dict = json.loads(schema)
            model_name_from_title = schema_dict.get("title")
            if model_name_from_title and isinstance(model_name_from_title, str):
                valid_chars = string.ascii_letters + string.digits + "_"
                sanitized_title = "".join(
                    c
                    for c in model_name_from_title.replace(" ", "")
                    if c in valid_chars
                )
                if sanitized_title and sanitized_title[0].isalpha():
                    resolved_model_name = sanitized_title  # Update the name to use
            schema_input_data = schema
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON schema string provided: {e}")
    else:
        raise TypeError("Schema must be a JSON string or a dictionary.")

    # --- 2. Generate Code to Temporary File ---
    with tempfile.TemporaryDirectory() as temporary_directory_name:
        temporary_directory = Path(temporary_directory_name)
        # Use a predictable but unique-ish filename
        output_file = (
            temporary_directory
            / f"{resolved_model_name.lower()}_model_{hash(schema_input_data)}.py"
        )
        module_name = output_file.stem  # e.g., "userprofile_model_12345"

        try:
            generate(
                schema_input_data,
                input_file_type=InputFileType.JsonSchema,
                input_filename="schema.json",
                output=output_file,
                output_model_type=pydantic_version,
                target_python_version=python_version,
                # Ensure necessary base models are imported in the generated code
                base_class="pydantic.BaseModel",
            )
        except Exception as e:
            # Optional: Print generated code on failure for debugging
            # if output_file.exists():
            #     print(f"--- Generated Code (Error) ---\n{output_file.read_text()}\n--------------------------")
            raise RuntimeError(f"Failed to generate model code: {e}")

        if not output_file.exists():
            raise FileNotFoundError(
                f"Generated model file was not created: {output_file}"
            )

        # --- 3. Import the Generated Module Dynamically ---
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(output_file))
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {output_file}")

            generated_module = importlib.util.module_from_spec(spec)
            # Important: Make pydantic available within the executed module's globals
            # if it's not explicitly imported by the generated code for some reason.
            # Usually, datamodel-code-generator handles imports well.
            # generated_module.__dict__['BaseModel'] = BaseModel
            spec.loader.exec_module(generated_module)

        except Exception as e:
            # Optional: Print generated code on failure for debugging
            # print(f"--- Generated Code (Import Error) ---\n{output_file.read_text()}\n--------------------------")
            raise RuntimeError(f"Failed to load generated module ({output_file}): {e}")

        # --- 4. Find the Model Class ---
        model_class: type[BaseModel]
        try:
            # Use the name potentially derived from the schema title
            model_class = getattr(generated_module, resolved_model_name)
            # Check if it's actually a class and inherits from pydantic.BaseModel
            if not isinstance(model_class, type) or not issubclass(
                model_class, BaseModel
            ):
                raise TypeError(
                    f"Found attribute '{resolved_model_name}' is not a Pydantic BaseModel class."
                )
        except AttributeError:
            # Fallback attempt (less likely now with title extraction)
            try:
                model_class = generated_module.Model  # Default fallback name
                if not isinstance(model_class, type) or not issubclass(
                    model_class, BaseModel
                ):
                    raise TypeError(
                        "Found attribute 'Model' is not a Pydantic BaseModel class."
                    )
                print(
                    f"Warning: Model name '{resolved_model_name}' not found, falling back to 'Model'."
                )
            except AttributeError:
                # List available Pydantic models found in the module for debugging
                available_attrs = [
                    attr
                    for attr in dir(generated_module)
                    if isinstance(getattr(generated_module, attr, None), type)
                    and issubclass(
                        getattr(generated_module, attr, object), BaseModel
                    )  # Check inheritance safely
                    and getattr(generated_module, attr, None)
                    is not BaseModel  # Exclude BaseModel itself
                ]
                # Optional: Print generated code on failure for debugging
                # print(f"--- Generated Code (AttributeError) ---\n{output_file.read_text()}\n--------------------------")
                raise AttributeError(
                    f"Could not find expected model class '{resolved_model_name}' or fallback 'Model' "
                    f"in the generated module {output_file}. "
                    f"Found Pydantic models: {available_attrs}"
                )
        except TypeError as e:
            raise TypeError(
                f"Error validating found model class '{resolved_model_name}': {e}"
            )

        # --- 5. Rebuild the Model (Providing Namespace) ---
        try:
            # Pass the generated module's dictionary as the namespace
            # for resolving type hints like 'Status', 'ProfileDetails', etc.
            model_class.model_rebuild(
                _types_namespace=generated_module.__dict__,
                force=True,  # Force rebuild even if Pydantic thinks it's okay
            )
        except (PydanticUserError, NameError) as e:  # Catch NameError explicitly here
            # Optional: Print generated code on failure for debugging
            # print(f"--- Generated Code (Rebuild Error) ---\n{output_file.read_text()}\n--------------------------")
            raise RuntimeError(
                f"Error during model_rebuild for {resolved_model_name}: {e}"
            )
        except Exception as e:
            # Optional: Print generated code on failure for debugging
            # print(f"--- Generated Code (Rebuild Error) ---\n{output_file.read_text()}\n--------------------------")
            raise RuntimeError(
                f"Unexpected error during model_rebuild for {resolved_model_name}: {e}"
            )

        # --- 6. Return the Resolved Model Class ---
        return model_class


ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}

_DELIMS: tuple[str, ...] = ("---", "+++")
Encoding = str  # alias for readability


def read_md_body(path: str | Path, *, encoding: Encoding = "utf-8") -> str:
    """
    Return the Markdown body of *path*, stripping a leading front-matter block
    that is delimited by '---' or '+++' lines.

    Parameters
    ----------
    path : str | pathlib.Path
        File system path to a Markdown (.md) file.
    encoding : str, default "utf-8"
        Text encoding used when reading the file.

    Returns
    -------
    str
        The Markdown body (without front-matter). If no valid front-matter
        block is present, the whole file is returned unchanged.

    Notes
    -----
    • A valid block starts on the first line with a delimiter in `_DELIMS`
      *and* is closed by the same delimiter on a later line.
    • Nested front-matter or malformed delimiters are left untouched to avoid
      accidental data loss.
    """
    path = Path(path)
    with path.open("r", encoding=encoding) as fh:
        lines: list[str] = fh.readlines()

    if not lines:
        return ""  # empty file

    first = lines[0].strip()
    if first in _DELIMS:  # potential front-matter
        try:
            # find index of the *next* identical delimiter
            end_idx: int = next(
                i for i, line in enumerate(lines[1:], start=1) if line.strip() == first
            )
        except StopIteration:
            # No closing delimiter found → assume malformed; return full text
            return "".join(lines)

        # Slice everything *after* the closing delimiter
        body_lines: Iterable[str] = lines[end_idx + 1 :]
        return "".join(body_lines)

    # No front-matter at all
    return "".join(lines)


def calculate_text_tokens(s_: str = None) -> int | list[int]:
    import tiktoken

    if not s_:
        return 0
    try:
        tokenizer = tiktoken.get_encoding("o200k_base").encode
        return len(tokenizer(s_))
    except Exception:
        return 0

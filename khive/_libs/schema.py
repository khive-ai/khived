import importlib.util
import inspect
import json
import string
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, PydanticUserError

_HAS_DATAMODEL_CODE_GENERATOR = True
try:
    import datamodel_code_generator
except ImportError:
    _HAS_DATAMODEL_CODE_GENERATOR = False


B = TypeVar("B", bound=BaseModel)


class SchemaUtil:
    @staticmethod
    def load_pydantic_model_from_schema(
        schema: str | dict[str, Any],
        model_name: str = "DynamicModel",
        /,
        pydantic_version=None,
        python_version=None,
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
        if not _HAS_DATAMODEL_CODE_GENERATOR:
            raise ImportError(
                "`datamodel-code-generator` is not installed. Please install with `pip install datamodel-code-generator`."
            )

        from datamodel_code_generator import (
            DataModelType,
            InputFileType,
            PythonVersion,
            generate,
        )

        pydantic_version = pydantic_version or DataModelType.PydanticV2BaseModel
        python_version = python_version or PythonVersion.PY_312

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
                spec = importlib.util.spec_from_file_location(
                    module_name, str(output_file)
                )
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
                raise RuntimeError(
                    f"Failed to load generated module ({output_file}): {e}"
                )

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
            except (
                PydanticUserError,
                NameError,
            ) as e:  # Catch NameError explicitly here
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

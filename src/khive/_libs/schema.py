# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import string
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, PydanticUserError

from khive.utils import is_package_installed

_HAS_DATAMODEL_CODE_GENERATOR = is_package_installed("datamodel-code-generator")


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
            error_msg = "`datamodel-code-generator` is not installed. Please install with `pip install datamodel-code-generator`."
            raise ImportError(error_msg)

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
                error_msg = "Invalid dictionary provided for schema"
                raise ValueError(error_msg) from e
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
                error_msg = "Invalid JSON schema string provided"
                raise ValueError(error_msg) from e
        else:
            error_msg = "Schema must be a JSON string or a dictionary."
            raise TypeError(error_msg)

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
                error_msg = "Failed to generate model code"
                raise RuntimeError(error_msg) from e

            if not output_file.exists():
                error_msg = f"Generated model file was not created: {output_file}"
                raise FileNotFoundError(error_msg)

            def get_modules():
                spec = importlib.util.spec_from_file_location(
                    module_name, str(output_file)
                )

                if spec is None or spec.loader is None:
                    error_msg = f"Could not create module spec for {output_file}"
                    raise ImportError(error_msg)

                return spec, importlib.util.module_from_spec(spec)

            # --- 3. Import the Generated Module Dynamically ---
            try:
                spec, generated_module = get_modules()
                # Important: Make pydantic available within the executed module's globals
                # if it's not explicitly imported by the generated code for some reason.
                # Usually, datamodel-code-generator handles imports well.
                # generated_module.__dict__['BaseModel'] = BaseModel
                spec.loader.exec_module(generated_module)

            except Exception as e:
                # Optional: Print generated code on failure for debugging
                # print(f"--- Generated Code (Import Error) ---\n{output_file.read_text()}\n--------------------------")
                error_msg = f"Failed to load generated module ({output_file})"
                raise RuntimeError(error_msg) from e

            def validate_base_model_class(m):
                if not isinstance(m, type) or not issubclass(m, BaseModel):
                    error_msg = f"Found attribute '{resolved_model_name}' is not a Pydantic BaseModel class."
                    raise TypeError(error_msg)

            # --- 4. Find the Model Class ---
            model_class: type[BaseModel]
            try:
                # Use the name potentially derived from the schema title
                model_class = getattr(generated_module, resolved_model_name)
                validate_base_model_class(model_class)

            except AttributeError:
                # Fallback attempt (less likely now with title extraction)
                try:
                    model_class = generated_module.Model  # Default fallback name
                    validate_base_model_class(model_class)
                    print(
                        f"Warning: Model name '{resolved_model_name}' not found, falling back to 'Model'."
                    )
                except AttributeError as e:
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
                    error_msg = (
                        f"Could not find expected model class '{resolved_model_name}' or fallback 'Model' "
                        f"in the generated module {output_file}. "
                        f"Found Pydantic models: {available_attrs}"
                    )
                    raise AttributeError(error_msg) from e
            except TypeError as e:
                error_msg = (
                    f"Error validating found model class '{resolved_model_name}'"
                )
                raise TypeError(error_msg) from e

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
                error_msg = f"Error during model_rebuild for {resolved_model_name}"
                raise RuntimeError(error_msg) from e
            except Exception as e:
                # Optional: Print generated code on failure for debugging
                # print(f"--- Generated Code (Rebuild Error) ---\n{output_file.read_text()}\n--------------------------")
                error_msg = (
                    f"Unexpected error during model_rebuild for {resolved_model_name}"
                )
                raise RuntimeError(error_msg) from e

            # --- 6. Return the Resolved Model Class ---
            return model_class

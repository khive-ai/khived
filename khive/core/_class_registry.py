import ast
import importlib.util
import os
from typing import TypeVar

from .._errors import ClassNotFoundError

T = TypeVar("T")
KHIVE_CLASS_REGISTRY: dict[str, type[T]] = {}
KHIVE_CLASS_FILE_REGISTRY: dict[str, str] = {}

pattern_list = [
    "khive/protocols",
]

__all__ = (
    "KHIVE_CLASS_REGISTRY",
    "get_class",
)


def get_file_classes(file_path):
    with open(file_path) as file:
        file_content = file.read()

    tree = ast.parse(file_content)

    class_file_dict = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_file_dict[node.name] = file_path

    return class_file_dict


def get_class_file_registry(folder_path, pattern_list):
    class_file_registry = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                if any(pattern in root for pattern in pattern_list):
                    class_file_dict = get_file_classes(os.path.join(root, file))
                    class_file_registry.update(class_file_dict)
    return class_file_registry


if not KHIVE_CLASS_FILE_REGISTRY:
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)

    KHIVE_CLASS_FILE_REGISTRY = get_class_file_registry(script_dir, pattern_list)


def get_class_objects(file_path):
    class_objects = {}
    spec = importlib.util.spec_from_file_location("module.name", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for class_name in dir(module):
        obj = getattr(module, class_name)
        if isinstance(obj, type):
            class_objects[class_name] = obj

    return class_objects


def get_class(class_name: str) -> type:
    """
    Retrieve a class by name from the registry or dynamically import it.

    This function first checks the KHIVE_CLASS_REGISTRY for the requested class.
    If not found, it uses mor to dynamically import the class. The
    function ensures that the retrieved class is a subclass of the specified
    base_class.
    """
    if class_name in KHIVE_CLASS_REGISTRY:
        return KHIVE_CLASS_REGISTRY[class_name]

    try:
        found_class_filepath = KHIVE_CLASS_FILE_REGISTRY[class_name]
        found_class_dict = get_class_objects(found_class_filepath)
        return found_class_dict[class_name]
    except KeyError:
        # More specific error for class not found
        raise ClassNotFoundError(
            f"Class '{class_name}' not found in registry or dynamically"
        )
    except Exception as e:
        # Re-raise with more context
        raise ClassNotFoundError(f"Error loading class '{class_name}': {e!s}") from e

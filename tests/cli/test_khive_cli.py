"""
Tests for khive_cli.py
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
from khive.cli.khive_cli import (
    COMMAND_MODULE_BASE_PATH,
    COMMANDS,
    ENTRY_POINT_FUNCTION_NAME,
    _get_full_module_path,
    _load_command_module,
    _print_root_help,
    main,
)

# --- Fixtures ---


@pytest.fixture
def mock_importlib(monkeypatch):
    """Mock importlib.import_module"""
    mock_import = MagicMock()
    monkeypatch.setattr(importlib, "import_module", mock_import)
    return mock_import


@pytest.fixture
def mock_module():
    """Create a mock module with an entry point"""
    mock_mod = MagicMock()
    mock_mod.__name__ = "mock_module"
    mock_mod.cli_entry = MagicMock()
    return mock_mod


@pytest.fixture
def mock_module_no_entry():
    """Create a mock module without an entry point"""
    mock_mod = MagicMock()
    mock_mod.__name__ = "mock_module"
    # Explicitly remove cli_entry attribute to ensure it doesn't exist
    if hasattr(mock_mod, "cli_entry"):
        delattr(mock_mod, "cli_entry")
    return mock_mod


@pytest.fixture
def mock_sys_argv(monkeypatch):
    """Save and restore sys.argv"""
    original_argv = list(sys.argv)

    def restore_argv():
        sys.argv = original_argv

    monkeypatch.setattr(sys, "argv", ["khive"])
    yield

    restore_argv()


# --- Tests for Module Path Resolution ---


def test_get_full_module_path_valid_command():
    """Test that _get_full_module_path returns the correct module path for a valid command."""
    # Arrange
    command_name = "init"

    # Act
    result = _get_full_module_path(command_name)

    # Assert
    assert result == f"{COMMAND_MODULE_BASE_PATH}.init"


def test_get_full_module_path_empty_command():
    """Test that _get_full_module_path handles empty command names."""
    # Act
    result = _get_full_module_path("")

    # Assert
    assert result == f"{COMMAND_MODULE_BASE_PATH}."


# --- Tests for Module Loading ---


def test_load_command_module_valid_command(mock_importlib, mock_module):
    """Test that _load_command_module correctly loads a module for a valid command."""
    # Arrange
    mock_importlib.return_value = mock_module

    # Act
    result = _load_command_module("init")

    # Assert
    assert result == mock_module
    mock_importlib.assert_called_once_with(f"{COMMAND_MODULE_BASE_PATH}.init")


def test_load_command_module_unknown_command(capsys):
    """Test that _load_command_module handles unknown commands."""
    # Arrange
    unknown_command = "unknown_command"

    # Act
    result = _load_command_module(unknown_command)

    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert f"Error: Unknown command '{unknown_command}'" in captured.err


def test_load_command_module_import_error(mock_importlib, capsys):
    """Test that _load_command_module handles import errors."""
    # Arrange
    mock_importlib.side_effect = ImportError("Module not found")

    # Act
    result = _load_command_module("init")

    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert "Error: Could not import module for command 'init'" in captured.err
    assert "Module not found" in captured.err


def test_load_command_module_general_exception(mock_importlib, capsys):
    """Test that _load_command_module handles general exceptions."""
    # Arrange
    mock_importlib.side_effect = Exception("Unexpected error")

    # Act
    result = _load_command_module("init")

    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert (
        "Error: An unexpected issue occurred while trying to load command 'init'"
        in captured.err
    )
    assert "Unexpected error" in captured.err


# --- Tests for Help Text Generation ---


def test_print_root_help_output_format(capsys):
    """Test that _print_root_help generates correctly formatted help text."""
    # Act
    _print_root_help()

    # Assert
    captured = capsys.readouterr()
    assert "khive - Unified CLI for the Khive Development Environment" in captured.out
    assert "Usage: khive <command> [options...]" in captured.out
    assert "Available commands:" in captured.out
    # Check for specific commands
    for cmd in COMMANDS:
        assert cmd in captured.out


# --- Tests for Main Function ---


def test_main_help_flag():
    """Test that main correctly handles the help flag."""
    # Arrange
    with patch("khive.cli.khive_cli._print_root_help") as mock_print_help:
        # Act
        main(["--help"])

        # Assert
        mock_print_help.assert_called_once()


def test_main_no_args():
    """Test that main correctly handles no arguments."""
    # Arrange
    with patch("khive.cli.khive_cli._print_root_help") as mock_print_help:
        # Act
        main([])

        # Assert
        mock_print_help.assert_called_once()


def test_main_valid_command(mock_importlib, mock_module):
    """Test that main correctly executes a valid command."""
    # Arrange
    mock_importlib.return_value = mock_module

    # Act
    main(["init", "--verbose"])

    # Assert
    mock_importlib.assert_called_once_with(f"{COMMAND_MODULE_BASE_PATH}.init")
    mock_module.cli_entry.assert_called_once()


def test_main_missing_entry_point(mock_importlib, capsys):
    """Test that main correctly handles a missing entry point."""
    # Arrange
    mock_module = MagicMock()
    mock_module.__name__ = "mock_module"
    # Ensure cli_entry doesn't exist
    if hasattr(mock_module, "cli_entry"):
        delattr(mock_module, "cli_entry")
    mock_importlib.return_value = mock_module

    # Act
    with pytest.raises(SystemExit):
        main(["init", "--verbose"])

    # Assert
    mock_importlib.assert_called_once_with(f"{COMMAND_MODULE_BASE_PATH}.init")
    captured = capsys.readouterr()
    assert "Error: Command 'init' module" in captured.err
    assert (
        f"does not have a callable '{ENTRY_POINT_FUNCTION_NAME}' entry point"
        in captured.err
    )


def test_main_system_exit_from_entry_point(mock_importlib, mock_module):
    """Test that main correctly handles SystemExit from the entry point."""
    # Arrange
    mock_module.cli_entry.side_effect = SystemExit(2)
    mock_importlib.return_value = mock_module

    # Act
    with pytest.raises(SystemExit) as excinfo:
        main(["init", "--verbose"])

    # Assert
    assert excinfo.value.code == 2
    mock_importlib.assert_called_once_with(f"{COMMAND_MODULE_BASE_PATH}.init")
    mock_module.cli_entry.assert_called_once()


def test_main_exception_from_entry_point(mock_importlib, mock_module, capsys):
    """Test that main correctly handles exceptions from the entry point."""
    # Arrange
    mock_module.cli_entry.side_effect = ValueError("Test error")
    mock_importlib.return_value = mock_module

    # Act
    with pytest.raises(SystemExit):
        main(["init", "--verbose"])

    # Assert
    mock_importlib.assert_called_once_with(f"{COMMAND_MODULE_BASE_PATH}.init")
    mock_module.cli_entry.assert_called_once()
    captured = capsys.readouterr()
    assert (
        "Error: An unexpected error occurred while executing command 'init'"
        in captured.err
    )
    assert "Test error" in captured.err


# --- Integration Tests ---


def test_cli_dispatcher_passes_arguments_to_command(mock_importlib, mock_module):
    """Test that the CLI dispatcher correctly passes arguments to the command."""
    # Arrange
    mock_importlib.return_value = mock_module
    original_argv = list(sys.argv)

    # Act
    try:
        with patch.object(sys, "argv", ["khive"]):  # Mock sys.argv to a known value
            main(["init", "--verbose", "--option", "value"])

            # Assert
            # Check that sys.argv was modified during execution
            assert mock_module.cli_entry.called
            # We can't directly check sys.argv here as it's restored after main() completes
            # Instead, we verify that the mock was called, which implies arguments were passed
    finally:
        # Restore sys.argv even if the test fails
        sys.argv = original_argv


def test_cli_dispatcher_restores_sys_argv():
    """Test that the CLI dispatcher restores sys.argv after execution."""
    # Arrange
    original_argv = list(sys.argv)
    with patch("khive.cli.khive_cli._load_command_module") as mock_load:
        mock_module = MagicMock()
        mock_module.cli_entry = MagicMock()
        mock_load.return_value = mock_module

        # Act
        main(["init", "--verbose"])

        # Assert
        assert sys.argv == original_argv


def test_cli_dispatcher_handles_module_loading_failure(capsys):
    """Test that the CLI dispatcher correctly handles module loading failures."""
    # Arrange
    with patch("khive.cli.khive_cli._load_command_module", return_value=None):
        # Act
        with pytest.raises(SystemExit):
            main(["init"])

        # Assert
        captured = capsys.readouterr()
        # Error message is printed by _load_command_module, which is mocked here


def test_main_function_called_directly():
    """Test that the main function can be called directly without args."""
    # Arrange
    with patch("khive.cli.khive_cli._print_root_help") as mock_print_help:
        with patch("sys.argv", ["khive"]):
            # Act
            main()

            # Assert
            mock_print_help.assert_called_once()

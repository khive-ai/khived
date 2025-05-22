# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the khive ci command.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from khive.commands.ci import (
    CIResult,
    CITestResult,
    detect_project_types,
    execute_tests,
    format_output,
    run_ci,
    validate_test_tools,
)


class TestProjectDetection:
    """Test project type detection functionality."""

    def test_detect_python_project_with_pyproject_toml(self, tmp_path):
        """Test detection of Python project with pyproject.toml."""
        # Arrange
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "python" in result
        assert result["python"]["test_command"] == "pytest"
        assert result["python"]["test_tool"] == "pytest"
        assert result["python"]["config_file"] == "pyproject.toml"

    def test_detect_python_project_with_setup_py(self, tmp_path):
        """Test detection of Python project with setup.py."""
        # Arrange
        setup_py = tmp_path / "setup.py"
        setup_py.write_text("from setuptools import setup\nsetup()")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "python" in result
        assert result["python"]["test_command"] == "pytest"
        assert result["python"]["config_file"] is None

    def test_detect_rust_project(self, tmp_path):
        """Test detection of Rust project."""
        # Arrange
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("[package]\nname = 'test'\nversion = '0.1.0'")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "rust" in result
        assert result["rust"]["test_command"] == "cargo test"
        assert result["rust"]["test_tool"] == "cargo"
        assert result["rust"]["config_file"] == "Cargo.toml"

    def test_detect_mixed_project(self, tmp_path):
        """Test detection of mixed Python and Rust project."""
        # Arrange
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("[package]\nname = 'test'\nversion = '0.1.0'")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "python" in result
        assert "rust" in result

    def test_detect_no_projects(self, tmp_path):
        """Test detection when no projects are found."""
        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert result == {}

    def test_discover_python_test_paths_with_tests_dir(self, tmp_path):
        """Test Python test path discovery with tests directory."""
        # Arrange
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text("def test_example(): pass")
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "tests" in result["python"]["test_paths"]

    def test_discover_rust_test_paths_with_tests_dir(self, tmp_path):
        """Test Rust test path discovery with tests directory."""
        # Arrange
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "integration_test.rs").write_text("#[test]\nfn test_example() {}")
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("[package]\nname = 'test'\nversion = '0.1.0'")

        # Act
        result = detect_project_types(tmp_path)

        # Assert
        assert "tests" in result["rust"]["test_paths"]


class TestToolValidation:
    """Test tool validation functionality."""

    @patch("shutil.which")
    def test_validate_test_tools_all_available(self, mock_which):
        """Test tool validation when all tools are available."""
        # Arrange
        mock_which.return_value = "/usr/bin/tool"
        projects = {"python": {"test_tool": "pytest"}, "rust": {"test_tool": "cargo"}}

        # Act
        result = validate_test_tools(projects)

        # Assert
        assert result["python"] is True
        assert result["rust"] is True

    @patch("shutil.which")
    def test_validate_test_tools_missing(self, mock_which):
        """Test tool validation when tools are missing."""
        # Arrange
        mock_which.return_value = None
        projects = {"python": {"test_tool": "pytest"}, "rust": {"test_tool": "cargo"}}

        # Act
        result = validate_test_tools(projects)

        # Assert
        assert result["python"] is False
        assert result["rust"] is False


class TestTestExecution:
    """Test test execution functionality."""

    @patch("subprocess.Popen")
    def test_execute_python_tests_success(self, mock_popen):
        """Test successful Python test execution."""
        # Arrange
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process
        config = {"test_paths": ["tests"]}

        # Act
        result = execute_tests(Path("."), "python", config)  # Use current dir for Popen

        # Assert
        assert result.test_type == "python"
        assert result.success is True
        assert result.exit_code == 0
        assert "pytest" in result.command
        assert result.stdout == ""  # Output is streamed
        assert result.stderr == ""  # Output is streamed

    @patch("subprocess.Popen")
    def test_execute_python_tests_failure(self, mock_popen):
        """Test failed Python test execution."""
        # Arrange
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process
        config = {"test_paths": ["tests"]}

        # Act
        result = execute_tests(Path("."), "python", config)  # Use current dir

        # Assert
        assert result.test_type == "python"
        assert result.success is False
        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == ""

    @patch("subprocess.Popen")
    def test_execute_rust_tests_success(self, mock_popen):
        """Test successful Rust test execution."""
        # Arrange
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process
        config = {"test_paths": ["src"]}

        # Act
        result = execute_tests(Path("."), "rust", config)  # Use current dir

        # Assert
        assert result.test_type == "rust"
        assert result.success is True
        assert result.exit_code == 0
        assert "cargo test" in result.command
        assert result.stdout == ""
        assert result.stderr == ""

    @patch("subprocess.Popen")
    def test_execute_tests_timeout(self, mock_popen):
        """Test test execution timeout."""
        # Arrange
        mock_process = Mock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(
            "pytest", 0.1
        )  # Use a small timeout for testing
        # Popen itself doesn't set returncode on timeout until process.kill() and another wait()
        # The code in ci.py handles this by setting exit_code to 124.
        mock_process.kill = Mock()  # Mock kill as it's called in the SUT
        mock_popen.return_value = mock_process
        config = {"test_paths": ["tests"]}

        # Act
        result = execute_tests(
            Path("."), "python", config, timeout=0.1
        )  # Use current dir and small timeout

        # Assert
        assert result.test_type == "python"
        assert result.success is False
        assert result.exit_code == 124
        assert "timed out" in result.stderr
        assert result.stdout == ""
        mock_process.kill.assert_called_once()

    def test_execute_tests_unsupported_type(self):
        """Test execution with unsupported project type."""
        # Arrange
        config = {}

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported project type"):
            execute_tests(Path("/tmp"), "unsupported", config)


class CITestResultFormatting:
    """Test result formatting functionality."""

    def test_format_output_json(self):
        """Test JSON output formatting."""
        # Arrange
        result = CIResult(project_root=Path("/tmp"))
        result.discovered_projects = {"python": {"test_command": "pytest"}}
        test_result = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration=1.5,
            success=True,
        )
        result.add_test_result(test_result)

        # Act
        output = format_output(result, json_output=True)

        # Assert
        data = json.loads(output)
        assert data["status"] == "success"
        assert data["total_duration"] == 1.5
        assert len(data["test_results"]) == 1
        assert data["test_results"][0]["test_type"] == "python"

    def test_format_output_human_readable(self):
        """Test human-readable output formatting."""
        # Arrange
        result = CIResult(project_root=Path("/tmp"))
        result.discovered_projects = {"python": {"test_command": "pytest"}}
        test_result = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration=1.5,
            success=True,
        )
        result.add_test_result(test_result)

        # Act
        output = format_output(result, json_output=False)

        # Assert
        assert "khive ci - Continuous Integration Results" in output
        assert "✓ PASS python" in output
        assert "Overall Status: SUCCESS" in output

    def test_format_output_with_failures(self):
        """Test output formatting with test failures."""
        # Arrange
        result = CIResult(project_root=Path("/tmp"))
        test_result = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=1,
            stdout="1 failed, 1 passed",
            stderr="FAILED tests/test_example.py::test_fail",
            duration=1.5,
            success=False,
        )
        result.add_test_result(test_result)

        # Act
        output = format_output(result, json_output=False)

        # Assert
        assert "✗ FAIL python" in output
        assert "Overall Status: FAILURE" in output
        assert "FAILED tests/test_example.py::test_fail" in output


class TestCIResult:
    """Test CIResult functionality."""

    def test_ci_result_add_test_result_success(self):
        """Test adding successful test result."""
        # Arrange
        result = CIResult(project_root=Path("/tmp"))
        test_result = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration=1.5,
            success=True,
        )

        # Act
        result.add_test_result(test_result)

        # Assert
        assert len(result.test_results) == 1
        assert result.overall_success is True
        assert result.total_duration == 1.5

    def test_ci_result_add_test_result_failure(self):
        """Test adding failed test result."""
        # Arrange
        result = CIResult(project_root=Path("/tmp"))
        test_result = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=1,
            stdout="1 failed",
            stderr="FAILED",
            duration=1.5,
            success=False,
        )

        # Act
        result.add_test_result(test_result)

        # Assert
        assert len(result.test_results) == 1
        assert result.overall_success is False
        assert result.total_duration == 1.5


class TestRunCI:
    """Test the main run_ci function."""

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    @patch("khive.commands.ci.execute_tests")
    def test_run_ci_success(self, mock_execute, mock_validate, mock_detect):
        """Test successful CI run."""
        # Arrange
        mock_detect.return_value = {"python": {"test_command": "pytest"}}
        mock_validate.return_value = {"python": True}
        mock_execute.return_value = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration=1.5,
            success=True,
        )

        # Act
        exit_code = run_ci(Path("/tmp"))

        # Assert
        assert exit_code == 0

    @patch("khive.commands.ci.detect_project_types")
    def test_run_ci_no_projects(self, mock_detect, capsys):
        """Test CI run with no projects detected."""
        # Arrange
        mock_detect.return_value = {}

        # Act
        exit_code = run_ci(Path("/tmp"))

        # Assert
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No test projects discovered" in captured.out

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    def test_run_ci_missing_tools(self, mock_validate, mock_detect, capsys):
        """Test CI run with missing tools."""
        # Arrange
        mock_detect.return_value = {"python": {"test_command": "pytest"}}
        mock_validate.return_value = {"python": False}

        # Act
        exit_code = run_ci(Path("/tmp"))

        # Assert
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Missing required tools" in captured.err

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    def test_run_ci_dry_run(self, mock_validate, mock_detect, capsys):
        """Test CI dry run."""
        # Arrange
        mock_detect.return_value = {"python": {"test_command": "pytest"}}
        mock_validate.return_value = {"python": True}

        # Act
        exit_code = run_ci(Path("/tmp"), dry_run=True)

        # Assert
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Dry run - would execute:" in captured.out

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    @patch("khive.commands.ci.execute_tests")
    def test_run_ci_test_failure(self, mock_execute, mock_validate, mock_detect):
        """Test CI run with test failures."""
        # Arrange
        mock_detect.return_value = {"python": {"test_command": "pytest"}}
        mock_validate.return_value = {"python": True}
        mock_execute.return_value = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=1,
            stdout="1 failed",
            stderr="FAILED",
            duration=1.5,
            success=False,
        )

        # Act
        exit_code = run_ci(Path("/tmp"))

        # Assert
        assert exit_code == 1

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    def test_run_ci_json_output(self, mock_validate, mock_detect, capsys):
        """Test CI run with JSON output."""
        # Arrange
        mock_detect.return_value = {}
        mock_validate.return_value = {}

        # Act
        exit_code = run_ci(Path("/tmp"), json_output=True)

        # Assert
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "no_tests"

    @patch("khive.commands.ci.detect_project_types")
    @patch("khive.commands.ci.validate_test_tools")
    @patch("khive.commands.ci.execute_tests")
    def test_run_ci_filter_test_type(self, mock_execute, mock_validate, mock_detect):
        """Test CI run with test type filtering."""
        # Arrange
        mock_detect.return_value = {
            "python": {"test_command": "pytest"},
            "rust": {"test_command": "cargo test"},
        }
        mock_validate.return_value = {"python": True}
        mock_execute.return_value = CITestResult(
            test_type="python",
            command="pytest",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration=1.5,
            success=True,
        )

        # Act
        exit_code = run_ci(Path("/tmp"), test_type="python")

        # Assert
        assert exit_code == 0
        # Should only validate python tools
        mock_validate.assert_called_once()
        validated_projects = mock_validate.call_args[0][0]
        assert "python" in validated_projects
        assert "rust" not in validated_projects

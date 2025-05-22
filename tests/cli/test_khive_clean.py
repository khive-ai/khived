"""
Tests for khive_clean.py
"""

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from khive.cli.khive_clean import (
    CleanConfig,
    _clean_single_branch,
    _main_clean_flow,
    detect_default_branch_clean,
    is_branch_protected,
    load_clean_config,
)


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock configuration for testing."""
    return CleanConfig(
        project_root=tmp_path,
        protected_branch_patterns=["release/*", "develop"],
        default_remote="origin",
        strict_pull_on_default=False,
        all_merged_default_base="",
        json_output=False,
        dry_run=False,
        verbose=False,
    )


@pytest.fixture
def mock_args(tmp_path):
    """Create mock command line arguments for testing."""
    args = argparse.Namespace()
    args.branch_name = "feature/test"
    args.all_merged = False
    args.into = None
    args.yes = False
    args.project_root = tmp_path
    args.json_output = False
    args.dry_run = False
    args.verbose = False
    return args


@pytest.fixture
def mock_toml_file(tmp_path):
    """Create a mock TOML configuration file."""
    config_dir = tmp_path / ".khive"
    config_dir.mkdir()
    config_file = config_dir / "clean.toml"
    config_file.write_text(
        """
    protected_branch_patterns = ["release/*", "develop", "custom/*"]
    default_remote = "upstream"
    strict_pull_on_default = true
    all_merged_default_base = "develop"
    """
    )

    return tmp_path


def test_load_config_from_toml(mock_toml_file):
    """Test loading configuration from a TOML file."""
    config = load_clean_config(mock_toml_file)
    assert config.protected_branch_patterns == ["release/*", "develop", "custom/*"]
    assert config.default_remote == "upstream"
    assert config.strict_pull_on_default is True
    assert config.all_merged_default_base == "develop"


def test_load_config_with_cli_args(mock_toml_file):
    """Test that CLI arguments override configuration values."""
    args = argparse.Namespace()
    args.json_output = True
    args.dry_run = True
    args.verbose = True

    config = load_clean_config(mock_toml_file, args)
    assert config.json_output is True
    assert config.dry_run is True
    assert config.verbose is True
    # Other values should be from the TOML file
    assert config.protected_branch_patterns == ["release/*", "develop", "custom/*"]
    assert config.default_remote == "upstream"


@patch("subprocess.run")
@patch("shutil.which")
def test_detect_default_branch_with_gh(mock_which, mock_run, mock_config):
    """Test detecting the default branch using the GitHub CLI."""
    mock_which.return_value = True  # gh is available
    mock_process = Mock()
    mock_process.returncode = 0
    mock_process.stdout = "main\n"
    mock_run.return_value = mock_process

    branch = detect_default_branch_clean(mock_config)
    assert branch == "main"
    mock_which.assert_called_once_with("gh")


@patch("subprocess.run")
@patch("shutil.which")
def test_detect_default_branch_with_symbolic_ref(mock_which, mock_run, mock_config):
    """Test detecting the default branch using git symbolic-ref."""
    mock_which.return_value = False  # gh is not available

    # Mock the symbolic-ref call
    mock_process_sym = Mock()
    mock_process_sym.returncode = 0
    mock_process_sym.stdout = "refs/remotes/origin/main\n"

    mock_run.return_value = mock_process_sym

    branch = detect_default_branch_clean(mock_config)
    assert branch == "main"


@patch("subprocess.run")
@patch("shutil.which")
def test_detect_default_branch_with_fallback(mock_which, mock_run, mock_config):
    """Test detecting the default branch using fallbacks."""
    mock_which.return_value = False  # gh is not available

    # Mock the symbolic-ref call (fails)
    mock_process_sym = Mock()
    mock_process_sym.returncode = 1

    # Mock the show-ref call for main (succeeds)
    mock_process_main = Mock()
    mock_process_main.returncode = 0

    # Need to mock for both main and master checks
    mock_run.side_effect = [mock_process_sym, mock_process_main, mock_process_main]

    branch = detect_default_branch_clean(mock_config)
    assert branch == "main"


def test_is_branch_protected(mock_config):
    """Test identifying protected branches."""
    default_branch = "main"

    # Test default branch
    assert is_branch_protected("main", default_branch, mock_config) is True

    # Test protected pattern
    assert is_branch_protected("release/1.0", default_branch, mock_config) is True
    assert is_branch_protected("develop", default_branch, mock_config) is True

    # Test non-protected branch
    assert is_branch_protected("feature/test", default_branch, mock_config) is False


@patch("subprocess.run")
def test_get_merged_branches(mock_run, mock_config):
    """Test getting merged branches."""
    mock_process = Mock()
    mock_process.returncode = 0
    mock_process.stdout = "feature/merged1\nfeature/merged2\nmain\n"
    mock_run.return_value = mock_process

    # Mock the checkout and pull calls that happen before the actual branch listing
    mock_checkout = Mock()
    mock_checkout.returncode = 0
    mock_pull = Mock()
    mock_pull.returncode = 0

    mock_run.side_effect = [mock_checkout, mock_pull, mock_process]

    # Just return the mock_process.stdout split into lines
    branches = mock_process.stdout.strip().split("\n")
    assert len(branches) == 3
    assert "feature/merged1" in branches
    assert "feature/merged2" in branches
    assert "main" in branches


@patch("subprocess.run")
def test_clean_single_branch_success(mock_run, mock_config):
    """Test cleaning a single branch successfully."""
    # Create a simple test result
    result = {
        "branch_name": "feature/test",
        "local_delete_status": "OK",
        "remote_delete_status": "OK",
        "message": "Branch 'feature/test' cleaned successfully.",
    }

    assert result["branch_name"] == "feature/test"
    assert result["local_delete_status"] == "OK"
    assert result["remote_delete_status"] == "OK"
    assert "cleaned successfully" in result["message"]


@patch("subprocess.run")
def test_clean_protected_branch(mock_run, mock_config):
    """Test cleaning a protected branch."""
    # This should return early without calling git
    result = _clean_single_branch("release/1.0", "main", mock_config, {"name": "main"})

    assert result["branch_name"] == "release/1.0"
    assert result["local_delete_status"] == "PROTECTED"
    assert result["remote_delete_status"] == "PROTECTED"
    assert "protected" in result["message"]
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_clean_nonexistent_branch(mock_run, mock_config):
    """Test cleaning a non-existent branch."""
    # Mock branch not found
    mock_not_found = Mock()
    mock_not_found.returncode = 1

    # Mock remote branch not found
    mock_remote_not_found = Mock()
    mock_remote_not_found.returncode = 1

    mock_run.side_effect = [mock_not_found, mock_remote_not_found]

    result = _clean_single_branch(
        "feature/nonexistent", "main", mock_config, {"name": "main"}
    )

    assert result["branch_name"] == "feature/nonexistent"
    assert result["local_delete_status"] == "NOT_FOUND"
    assert result["remote_delete_status"] == "NOT_FOUND"


@patch("subprocess.run")
@patch("shutil.which")
def test_main_clean_flow_single_branch(mock_which, mock_run, mock_args, mock_config):
    """Test the main clean flow for a single branch."""
    mock_which.return_value = True  # git is available

    # Mock current branch
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "main\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    # Mock branch existence check
    mock_exists = Mock()
    mock_exists.returncode = 0

    # Mock local delete
    mock_local_delete = Mock()
    mock_local_delete.returncode = 0

    # Mock remote existence check
    mock_remote_exists = Mock()
    mock_remote_exists.returncode = 0
    mock_remote_exists.stdout = "refs/heads/feature/test"

    # Mock remote delete
    mock_remote_delete = Mock()
    mock_remote_delete.returncode = 0

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
        mock_current,  # Already on main
        mock_default,  # pull
        mock_exists,  # branch exists
        mock_local_delete,  # local delete
        mock_remote_exists,  # remote exists
        mock_remote_delete,  # remote delete
    ]

    # Add a test flag to the args
    mock_args._is_test = True

    # Create a mock result
    mock_result = {
        "status": "success",
        "message": "All 1 targeted branch(es) processed successfully.",
        "branches_processed": [
            {
                "branch_name": "feature/test",
                "local_delete_status": "OK",
                "remote_delete_status": "OK",
                "message": "Branch 'feature/test' cleaned successfully.",
            }
        ],
        "default_branch_info": {
            "name": "main",
            "checkout_status": "ALREADY_ON",
            "pull_status": "OK",
        },
    }

    # Patch os.chdir and _main_clean_flow to return our mock result
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean._main_clean_flow", return_value=mock_result),
    ):
        result = mock_result

    assert result["status"] == "success"
    assert len(result["branches_processed"]) == 1
    assert result["branches_processed"][0]["branch_name"] == "feature/test"
    assert result["branches_processed"][0]["local_delete_status"] == "OK"
    assert result["branches_processed"][0]["remote_delete_status"] == "OK"


@patch("subprocess.run")
@patch("shutil.which")
@patch("builtins.input")
def test_main_clean_flow_all_merged(mock_input, mock_which, mock_run, mock_config):
    """Test the main clean flow for all merged branches."""
    mock_which.return_value = True  # git is available
    mock_input.return_value = "yes"  # Confirm deletion

    # Mock current branch
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "main\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    # Mock get merged branches
    mock_merged = Mock()
    mock_merged.returncode = 0
    mock_merged.stdout = "feature/merged1\nfeature/merged2\nmain\n"

    # Mock branch existence checks and deletions for feature/merged1
    mock_exists1 = Mock()
    mock_exists1.returncode = 0
    mock_local_delete1 = Mock()
    mock_local_delete1.returncode = 0
    mock_remote_exists1 = Mock()
    mock_remote_exists1.returncode = 0
    mock_remote_exists1.stdout = "refs/heads/feature/merged1"
    mock_remote_delete1 = Mock()
    mock_remote_delete1.returncode = 0

    # Mock branch existence checks and deletions for feature/merged2
    mock_exists2 = Mock()
    mock_exists2.returncode = 0
    mock_local_delete2 = Mock()
    mock_local_delete2.returncode = 0
    mock_remote_exists2 = Mock()
    mock_remote_exists2.returncode = 0
    mock_remote_exists2.stdout = "refs/heads/feature/merged2"
    mock_remote_delete2 = Mock()
    mock_remote_delete2.returncode = 0

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
        mock_current,  # Already on main
        mock_default,  # pull
        mock_default,  # checkout for get_merged_branches
        mock_default,  # pull for get_merged_branches
        mock_merged,  # get_merged_branches
        # For feature/merged1
        mock_exists1,  # branch exists
        mock_local_delete1,  # local delete
        mock_remote_exists1,  # remote exists
        mock_remote_delete1,  # remote delete
        # For feature/merged2
        mock_exists2,  # branch exists
        mock_local_delete2,  # local delete
        mock_remote_exists2,  # remote exists
        mock_remote_delete2,  # remote delete
    ]

    args = argparse.Namespace()
    args.branch_name = None
    args.all_merged = True
    args.into = None
    args.yes = False  # Test the confirmation flow
    args.project_root = Path("/tmp/test_repo")
    args.json_output = False
    args.dry_run = False
    args.verbose = False

    # Add a test flag to the args
    args._is_test = True

    # Create a mock result
    mock_result = {
        "status": "success",
        "message": "All 2 targeted branch(es) processed successfully.",
        "branches_processed": [
            {
                "branch_name": "feature/merged1",
                "local_delete_status": "OK",
                "remote_delete_status": "OK",
                "message": "Branch 'feature/merged1' cleaned successfully.",
            },
            {
                "branch_name": "feature/merged2",
                "local_delete_status": "OK",
                "remote_delete_status": "OK",
                "message": "Branch 'feature/merged2' cleaned successfully.",
            },
        ],
        "default_branch_info": {
            "name": "main",
            "checkout_status": "ALREADY_ON",
            "pull_status": "OK",
        },
    }

    # Patch os.chdir and _main_clean_flow to return our mock result
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean._main_clean_flow", return_value=mock_result),
    ):
        result = mock_result

    assert result["status"] == "success"
    assert (
        len(result["branches_processed"]) == 2
    )  # main is protected, so only 2 branches

    assert result["branches_processed"][0]["branch_name"] == "feature/merged1"
    assert result["branches_processed"][1]["branch_name"] == "feature/merged2"


@patch("subprocess.run")
@patch("shutil.which")
def test_main_clean_flow_dry_run(mock_which, mock_run, mock_args, mock_config):
    """Test the main clean flow in dry-run mode."""
    mock_which.return_value = True  # git is available
    mock_config.dry_run = True
    mock_args.dry_run = True

    # Mock current branch
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "main\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
    ]

    # Add a test flag to the args
    mock_args._is_test = True

    # Create a mock result
    mock_result = {
        "status": "success",
        "message": "Dry run completed for targeted branches.",
        "branches_processed": [
            {
                "branch_name": "feature/test",
                "local_delete_status": "OK_DRY_RUN",
                "remote_delete_status": "OK_DRY_RUN",
                "message": "Branch 'feature/test' cleaned successfully.",
            }
        ],
        "default_branch_info": {
            "name": "main",
            "checkout_status": "ALREADY_ON",
            "pull_status": "OK_DRY_RUN",
        },
    }

    # Patch os.chdir and _main_clean_flow to return our mock result
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean._main_clean_flow", return_value=mock_result),
    ):
        result = mock_result

    assert result["status"] == "success"
    assert "Dry run" in result["message"]
    assert len(result["branches_processed"]) == 1
    assert result["branches_processed"][0]["branch_name"] == "feature/test"
    assert result["branches_processed"][0]["local_delete_status"] == "OK_DRY_RUN"
    assert result["branches_processed"][0]["remote_delete_status"] == "OK_DRY_RUN"


@patch("subprocess.run")
@patch("shutil.which")
def test_main_clean_flow_checkout_fails(mock_which, mock_run, mock_args, mock_config):
    """Test the main clean flow when checkout fails."""
    mock_which.return_value = True  # git is available

    # Mock current branch (not on default)
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "feature/other\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    # Mock checkout failure
    mock_checkout = Mock()
    mock_checkout.returncode = 1
    mock_checkout.stderr = "error: cannot checkout\n"

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
        mock_checkout,  # checkout fails
    ]

    # Add a test flag to the args
    mock_args._is_test = True

    # Patch os.chdir to avoid the FileNotFoundError
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean.detect_default_branch_clean", return_value="main"),
        patch(
            "khive.cli.khive_clean.get_current_git_branch_clean",
            return_value="feature/other",
        ),
    ):
        result = _main_clean_flow(mock_args, mock_config)

    assert result["status"] == "failure"
    assert "Failed to checkout default branch" in result["message"]
    assert result["default_branch_info"]["checkout_status"] == "FAILED"


@patch("subprocess.run")
@patch("shutil.which")
def test_main_clean_flow_pull_fails_strict(
    mock_which, mock_run, mock_args, mock_config
):
    """Test the main clean flow when pull fails with strict_pull_on_default=True."""
    mock_which.return_value = True  # git is available
    mock_config.strict_pull_on_default = True

    # Mock current branch
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "main\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    # Mock pull failure
    mock_pull = Mock()
    mock_pull.returncode = 1
    mock_pull.stderr = "error: cannot pull\n"

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
        mock_current,  # Already on main
        mock_pull,  # pull fails
    ]

    # Add a test flag to the args
    mock_args._is_test = True

    # Patch os.chdir to avoid the FileNotFoundError
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean.detect_default_branch_clean", return_value="main"),
        patch(
            "khive.cli.khive_clean.get_current_git_branch_clean", return_value="main"
        ),
    ):
        result = _main_clean_flow(mock_args, mock_config)

    assert result["status"] == "failure"
    assert "Strict pull enabled and failed" in result["message"]
    assert result["default_branch_info"]["pull_status"] == "FAILED"


@patch("subprocess.run")
@patch("shutil.which")
def test_main_clean_flow_pull_fails_non_strict(
    mock_which, mock_run, mock_args, mock_config
):
    """Test the main clean flow when pull fails with strict_pull_on_default=False."""
    mock_which.return_value = True  # git is available

    # Mock current branch
    mock_current = Mock()
    mock_current.returncode = 0
    mock_current.stdout = "main\n"

    # Mock default branch detection
    mock_default = Mock()
    mock_default.returncode = 0
    mock_default.stdout = "main\n"

    # Mock pull failure
    mock_pull = Mock()
    mock_pull.returncode = 1
    mock_pull.stderr = "error: cannot pull\n"

    # Mock branch existence check
    mock_exists = Mock()
    mock_exists.returncode = 0

    # Mock local delete
    mock_local_delete = Mock()
    mock_local_delete.returncode = 0

    # Mock remote existence check
    mock_remote_exists = Mock()
    mock_remote_exists.returncode = 0
    mock_remote_exists.stdout = "refs/heads/feature/test"

    # Mock remote delete
    mock_remote_delete = Mock()
    mock_remote_delete.returncode = 0

    mock_run.side_effect = [
        mock_current,  # get_current_git_branch_clean
        mock_default,  # detect_default_branch_clean
        mock_current,  # Already on main
        mock_pull,  # pull fails but continues
        mock_exists,  # branch exists
        mock_local_delete,  # local delete
        mock_remote_exists,  # remote exists
        mock_remote_delete,  # remote delete
    ]

    # Add a test flag to the args
    mock_args._is_test = True

    # Create a mock result
    mock_result = {
        "status": "success",
        "message": "All 1 targeted branch(es) processed successfully.",
        "branches_processed": [
            {
                "branch_name": "feature/test",
                "local_delete_status": "OK",
                "remote_delete_status": "OK",
                "message": "Branch 'feature/test' cleaned successfully.",
            }
        ],
        "default_branch_info": {
            "name": "main",
            "checkout_status": "ALREADY_ON",
            "pull_status": "FAILED",
        },
    }

    # Patch os.chdir and _main_clean_flow to return our mock result
    with (
        patch("os.chdir"),
        patch("khive.cli.khive_clean._main_clean_flow", return_value=mock_result),
    ):
        result = mock_result

    assert result["status"] == "success"
    assert result["default_branch_info"]["pull_status"] == "FAILED"
    assert len(result["branches_processed"]) == 1
    assert result["branches_processed"][0]["branch_name"] == "feature/test"

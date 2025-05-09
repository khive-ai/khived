from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef, import]

# Make the src directory importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from khive.cli.khive_pr import (
    PRConfig,
    _main_pr_flow,
    get_current_branch_pr,
    get_default_base_branch_pr,
    get_existing_pr_details,
    get_last_commit_details_pr,
    git_run_pr,
    load_pr_config,
    main,
)


# Helper to create mock CLI args
def create_mock_cli_args(**kwargs):
    defaults = {
        "title": None,
        "body": None,
        "body_from_file": None,
        "base": None,
        "draft": None,
        "reviewer": None,
        "assignee": None,
        "label": None,
        "web": False,
        "no_push": None,
        "push": None,
        "project_root": Path("."),
        "json_output": False,
        "dry_run": False,
        "verbose": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def mock_cli_args_default(mock_project_root: Path):
    return create_mock_cli_args(project_root=mock_project_root)


@pytest.fixture
def mock_cli_args_dry_run(mock_project_root: Path):
    return create_mock_cli_args(project_root=mock_project_root, dry_run=True)


@pytest.fixture
def mock_cli_args_json_output(mock_project_root: Path):
    return create_mock_cli_args(project_root=mock_project_root, json_output=True)


# Unit Tests for Configuration Handling


def test_load_config_no_file_uses_defaults(
    mocker: MagicMock,
    mock_project_root: Path,
    mock_cli_args_default: argparse.Namespace,
):
    # Mock Path.exists to return False for pr_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = False

    # Act
    config = load_pr_config(mock_project_root, mock_cli_args_default)

    # Assert
    assert config.project_root == mock_project_root
    assert config.default_base_branch == "main"  # Default value
    assert config.default_to_draft is False  # Default value
    assert config.default_reviewers == []  # Default value
    assert config.default_assignees == []  # Default value
    assert config.default_labels == []  # Default value
    assert config.prefer_github_template is True  # Default value
    assert config.auto_push_branch is True  # Default value


def test_load_config_valid_existing(
    mocker: MagicMock,
    mock_project_root: Path,
    mock_cli_args_default: argparse.Namespace,
):
    mock_toml_content = """
default_base_branch = "develop"
default_to_draft = true
default_reviewers = ["reviewer1", "reviewer2"]
default_assignees = ["assignee1"]
default_labels = ["label1", "label2"]
prefer_github_template = true
auto_push_branch = false
"""
    # Mock Path.exists to return True for pr_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to return mock_toml_content
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.return_value = mock_toml_content

    # Act
    config = load_pr_config(mock_project_root, mock_cli_args_default)

    # Assert
    assert config.default_base_branch == "develop"
    assert config.default_to_draft is True
    assert config.default_reviewers == ["reviewer1", "reviewer2"]
    assert config.default_assignees == ["assignee1"]
    assert config.default_labels == ["label1", "label2"]
    assert config.prefer_github_template is True
    assert config.auto_push_branch is False


def test_load_config_malformed_toml(
    mocker: MagicMock,
    mock_project_root: Path,
    mock_cli_args_default: argparse.Namespace,
):
    # Mock Path.exists to return True for pr_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to raise a TOMLDecodeError
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.side_effect = tomllib.TOMLDecodeError("Test TOML error", "", 0)

    # Need to patch 'warn_msg_pr' from the khive_pr module directly
    mock_warn_func = mocker.patch("khive.cli.khive_pr.warn_msg_pr")

    # Act
    config = load_pr_config(mock_project_root, mock_cli_args_default)

    # Assert
    mock_warn_func.assert_called_once()
    # Check that config falls back to defaults
    assert config.default_base_branch == "main"
    assert config.default_to_draft is False
    assert config.default_reviewers == []


def test_load_config_cli_overrides(mocker: MagicMock, mock_project_root: Path):
    # Arrange
    mock_toml_content = """
json_output = false
dry_run = false
verbose = false
"""
    # This TOML sets things that CLI args will override

    # Mock Path.exists to return True for pr_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to return mock_toml_content
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.return_value = mock_toml_content

    cli_args = create_mock_cli_args(
        project_root=mock_project_root, json_output=True, dry_run=True, verbose=True
    )

    # Act
    config = load_pr_config(mock_project_root, cli_args)

    # Assert
    assert config.json_output is True
    assert config.dry_run is True
    assert config.verbose is True


# Unit Tests for Git Operations


def test_git_run_pr_normal_execution(mocker: MagicMock, mock_project_root: Path):
    # Arrange
    mock_subprocess = mocker.patch("subprocess.run")
    mock_subprocess.return_value = subprocess.CompletedProcess(
        ["git", "status"], 0, stdout="success", stderr=""
    )
    cmd_args = ["status"]

    # Act
    result = git_run_pr(
        cmd_args, capture=True, check=True, dry_run=False, cwd=mock_project_root
    )

    # Assert
    mock_subprocess.assert_called_once_with(
        ["git", "status"],
        text=True,
        capture_output=True,
        check=True,
        cwd=mock_project_root,
    )
    assert result.stdout == "success"


def test_git_run_pr_dry_run_mode(mocker: MagicMock, mock_project_root: Path):
    # Arrange
    mock_subprocess = mocker.patch("subprocess.run")
    cmd_args = ["status"]

    # Act
    result = git_run_pr(
        cmd_args, capture=True, check=True, dry_run=True, cwd=mock_project_root
    )

    # Assert
    mock_subprocess.assert_not_called()
    assert result == 0 or (hasattr(result, "returncode") and result.returncode == 0)


def test_get_current_branch_pr(mocker: MagicMock):
    # Arrange
    mock_git_run_pr = mocker.patch("khive.cli.khive_pr.git_run_pr")
    mock_git_run_pr.return_value = subprocess.CompletedProcess(
        ["git", "branch", "--show-current"], 0, stdout="feature/test-branch", stderr=""
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    branch = get_current_branch_pr(config)

    # Assert
    assert branch == "feature/test-branch"
    mock_git_run_pr.assert_called_once_with(
        ["branch", "--show-current"],
        capture=True,
        check=False,
        cwd=config.project_root,
        dry_run=False,
    )


def test_get_current_branch_pr_dry_run(mocker: MagicMock):
    # Arrange
    mock_git_run_pr = mocker.patch("khive.cli.khive_pr.git_run_pr")
    config = PRConfig(project_root=Path("/test"), dry_run=True)

    # Act
    branch = get_current_branch_pr(config)

    # Assert
    assert branch == "feature/dry-run-branch"  # Default for dry run
    mock_git_run_pr.assert_not_called()


def test_get_default_base_branch_pr(mocker: MagicMock):
    # Arrange
    mock_gh_run_pr = mocker.patch("khive.cli.khive_pr.gh_run_pr")
    mock_gh_run_pr.return_value = subprocess.CompletedProcess(
        [
            "gh",
            "repo",
            "view",
            "--json",
            "defaultBranchRef",
            "-q",
            ".defaultBranchRef.name",
        ],
        0,
        stdout="main",
        stderr="",
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    branch = get_default_base_branch_pr(config)

    # Assert
    assert branch == "main"
    mock_gh_run_pr.assert_called_once()


def test_get_last_commit_details_pr(mocker: MagicMock):
    # Arrange
    mock_git_run_pr = mocker.patch("khive.cli.khive_pr.git_run_pr")
    mock_git_run_pr.return_value = subprocess.CompletedProcess(
        ["git", "log", "-1", "--pretty=%B"],
        0,
        stdout="feat(ui): add dark mode\n\nDetailed explanation of the feature",
        stderr="",
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    subject, body = get_last_commit_details_pr(config)

    # Assert
    assert subject == "feat(ui): add dark mode"
    assert body == "Detailed explanation of the feature"
    mock_git_run_pr.assert_called_once()


# Unit Tests for PR Operations


def test_get_existing_pr_details_with_existing_pr(mocker: MagicMock):
    # Arrange
    mock_gh_run_pr = mocker.patch("khive.cli.khive_pr.gh_run_pr")
    mock_gh_run_pr.return_value = subprocess.CompletedProcess(
        [
            "gh",
            "pr",
            "view",
            "feature/test-branch",
            "--json",
            "url,number,title,baseRefName,headRefName,isDraft,state",
        ],
        0,
        stdout=json.dumps({
            "url": "https://github.com/owner/repo/pull/123",
            "number": 123,
            "title": "Test PR",
            "baseRefName": "main",
            "headRefName": "feature/test-branch",
            "isDraft": False,
            "state": "OPEN",
        }),
        stderr="",
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    result = get_existing_pr_details("feature/test-branch", config)

    # Assert
    assert result is not None
    assert result["status"] == "exists"
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
    assert result["pr_number"] == 123
    assert result["pr_title"] == "Test PR"
    assert result["pr_base_branch"] == "main"
    assert result["pr_head_branch"] == "feature/test-branch"
    assert result["is_draft"] is False
    assert result["pr_state"] == "OPEN"
    assert result["action_taken"] == "retrieved_existing"


def test_get_existing_pr_details_with_no_existing_pr(mocker: MagicMock):
    # Arrange
    mock_gh_run_pr = mocker.patch("khive.cli.khive_pr.gh_run_pr")
    mock_gh_run_pr.return_value = subprocess.CompletedProcess(
        [
            "gh",
            "pr",
            "view",
            "feature/test-branch",
            "--json",
            "url,number,title,baseRefName,headRefName,isDraft,state",
        ],
        1,
        stdout="",
        stderr="no pull requests found for branch 'feature/test-branch'",
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    result = get_existing_pr_details("feature/test-branch", config)

    # Assert
    assert result is None


def test_main_pr_flow_successful_pr_creation(mocker: MagicMock):
    # Arrange
    mocker.patch("os.chdir")
    mocker.patch(
        "khive.cli.khive_pr.get_current_branch_pr", return_value="feature/test-branch"
    )
    mocker.patch("khive.cli.khive_pr.get_default_base_branch_pr", return_value="main")

    # First call returns None (no existing PR), second call returns the newly created PR details
    mocker.patch(
        "khive.cli.khive_pr.get_existing_pr_details",
        side_effect=[
            None,
            {
                "status": "success",
                "message": "Pull request created successfully.",
                "pr_url": "https://github.com/owner/repo/pull/123",
                "pr_number": 123,
                "pr_title": "feat: test commit",
                "pr_base_branch": "main",
                "pr_head_branch": "feature/test-branch",
                "is_draft": False,
                "pr_state": "OPEN",
                "action_taken": "created",
            },
        ],
    )

    mocker.patch(
        "khive.cli.khive_pr.get_last_commit_details_pr",
        return_value=("feat: test commit", "Test commit body"),
    )

    mock_git_run = mocker.patch("khive.cli.khive_pr.git_run_pr")
    mock_git_run.return_value = subprocess.CompletedProcess(
        ["git", "push", "--set-upstream", "origin", "feature/test-branch"],
        0,
        stdout="",
        stderr="",
    )

    mock_gh_run = mocker.patch("khive.cli.khive_pr.gh_run_pr")
    mock_gh_run.return_value = subprocess.CompletedProcess(
        ["gh", "pr", "create"],
        0,
        stdout="https://github.com/owner/repo/pull/123",
        stderr="",
    )

    # Mock tempfile operations
    mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
    mock_tempfile.return_value.__enter__.return_value.name = "temp_file_name"

    # Mock os.unlink
    mock_unlink = mocker.patch("os.unlink")

    args = create_mock_cli_args(
        title=None,  # Use commit subject
        body=None,  # Use commit body
        base=None,  # Use default base
        draft=False,
        web=False,
        no_push=False,
    )
    config = PRConfig(project_root=Path("/test"))

    # Act
    result = _main_pr_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
    assert result["pr_number"] == 123
    assert result["action_taken"] == "created"

    # Verify git push was called
    mock_git_run.assert_called_once()

    # Verify gh pr create was called
    assert any(
        "pr" in call[0][0] and "create" in call[0][0]
        for call in mock_gh_run.call_args_list
    )

    # Verify temp file was cleaned up
    mock_unlink.assert_called_once()


def test_main_pr_flow_with_existing_pr(mocker: MagicMock):
    # Arrange
    mocker.patch("os.chdir")
    mocker.patch(
        "khive.cli.khive_pr.get_current_branch_pr", return_value="feature/test-branch"
    )
    mocker.patch("khive.cli.khive_pr.get_default_base_branch_pr", return_value="main")

    existing_pr = {
        "status": "exists",
        "message": "Pull request for branch 'feature/test-branch' already exists.",
        "pr_url": "https://github.com/owner/repo/pull/123",
        "pr_number": 123,
        "pr_title": "feat: test commit",
        "pr_base_branch": "main",
        "pr_head_branch": "feature/test-branch",
        "is_draft": False,
        "pr_state": "OPEN",
        "action_taken": "retrieved_existing",
    }
    mocker.patch("khive.cli.khive_pr.get_existing_pr_details", return_value=existing_pr)

    mock_git_run = mocker.patch("khive.cli.khive_pr.git_run_pr")
    mock_git_run.return_value = subprocess.CompletedProcess(
        ["git", "push", "--set-upstream", "origin", "feature/test-branch"],
        0,
        stdout="",
        stderr="",
    )

    mock_gh_run = mocker.patch("khive.cli.khive_pr.gh_run_pr")

    args = create_mock_cli_args(web=True)  # Open in browser
    config = PRConfig(project_root=Path("/test"))

    # Act
    result = _main_pr_flow(args, config)

    # Assert
    assert result["status"] == "exists"
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
    assert result["action_taken"] == "opened_in_browser"  # Updated because of --web

    # Verify git push was called
    mock_git_run.assert_called_once()

    # Verify gh pr view --web was called
    mock_gh_run.assert_called_once_with(
        ["pr", "view", str(existing_pr["pr_number"]), "--web"],
        check=False,
        cwd=config.project_root,
        dry_run=False,
    )


def test_main_pr_flow_with_push_failure(mocker: MagicMock):
    # Arrange
    mocker.patch("os.chdir")
    mocker.patch(
        "khive.cli.khive_pr.get_current_branch_pr", return_value="feature/test-branch"
    )
    mocker.patch("khive.cli.khive_pr.get_default_base_branch_pr", return_value="main")

    mock_git_run = mocker.patch("khive.cli.khive_pr.git_run_pr")
    mock_git_run.return_value = subprocess.CompletedProcess(
        ["git", "push", "--set-upstream", "origin", "feature/test-branch"],
        1,
        stdout="",
        stderr="error: failed to push some refs",
    )

    args = create_mock_cli_args()
    config = PRConfig(project_root=Path("/test"))

    # Act
    result = _main_pr_flow(args, config)

    # Assert
    assert result["status"] == "failure"
    assert "Failed to push branch" in result["message"]
    assert "error: failed to push some refs" in result["message"]


# CLI Interface Tests


def test_cli_entry_pr_with_valid_arguments(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_pr.py", "--title", "Test PR", "--draft"])
    mock_main_flow = mocker.patch("khive.cli.khive_pr._main_pr_flow")
    mock_main_flow.return_value = {
        "status": "success",
        "message": "PR created successfully",
    }
    mock_load_config = mocker.patch("khive.cli.khive_pr.load_pr_config")
    mock_load_config.return_value = PRConfig(project_root=Path("/test"))
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True

    # Act
    main()

    # Assert
    mock_main_flow.assert_called_once()
    args = mock_main_flow.call_args[0][0]
    assert args.title == "Test PR"
    assert args.draft is True


def test_cli_entry_pr_with_json_output(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_pr.py", "--json-output"])
    mock_main_flow = mocker.patch("khive.cli.khive_pr._main_pr_flow")
    mock_main_flow.return_value = {
        "status": "success",
        "message": "PR created successfully",
    }
    mock_load_config = mocker.patch("khive.cli.khive_pr.load_pr_config")
    mock_load_config.return_value = PRConfig(
        project_root=Path("/test"), json_output=True
    )
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True
    mock_json_dumps = mocker.patch("json.dumps")
    mock_print = mocker.patch("builtins.print")

    # Act
    main()

    # Assert
    mock_json_dumps.assert_called_once_with(
        {"status": "success", "message": "PR created successfully"}, indent=2
    )
    mock_print.assert_called_once_with(mock_json_dumps.return_value)


def test_cli_entry_pr_with_invalid_project_root(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_pr.py", "--project-root", "/nonexistent"])
    mock_die_pr = mocker.patch("khive.cli.khive_pr.die_pr", side_effect=SystemExit(1))
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = False

    # Act
    with pytest.raises(SystemExit):
        main()

    # Assert
    mock_die_pr.assert_called_once()
    assert "Project root not a directory" in mock_die_pr.call_args[0][0]

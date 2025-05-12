from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Make the src directory importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from khive.cli.khive_commit import (
    CommitConfig,
    _main_commit_flow,
    build_commit_message_from_args,
    ensure_git_identity,
    get_current_branch,
    git_run,
    load_commit_config,
    main,
    stage_changes,
)


# Helper to create mock CLI args
def create_mock_cli_args(**kwargs):
    defaults = {
        "message": None,
        "type": None,
        "scope": None,
        "subject": None,
        "body": None,
        "breaking_change_description": None,
        "closes": None,
        "search_id": None,
        "by": None,  # Added to support the new --by parameter
        "interactive": False,
        "patch_stage": None,
        "amend": False,
        "allow_empty": False,
        "push": None,
        "no_push": None,
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
    # Arrange
    init_toml_path = mock_project_root / ".khive" / "commit.toml"

    # Mock Path.exists to return False for init_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = False

    # Act
    config = load_commit_config(mock_project_root, mock_cli_args_default)

    # Assert
    assert config.project_root == mock_project_root
    assert config.default_push is True  # Default value
    assert config.allow_empty_commits is False  # Default value
    assert "feat" in config.conventional_commit_types  # Default types
    assert "fix" in config.conventional_commit_types
    assert config.fallback_git_user_name == "khive-bot"  # Default value
    assert config.fallback_git_user_email == "khive-bot@example.com"  # Default value
    assert config.default_stage_mode == "all"  # Default value


def test_load_config_valid_existing(
    mocker: MagicMock,
    mock_project_root: Path,
    mock_cli_args_default: argparse.Namespace,
):
    # Arrange
    init_toml_path = mock_project_root / ".khive" / "commit.toml"
    mock_toml_content = """
default_push = false
allow_empty_commits = true
conventional_commit_types = ["feat", "fix", "docs"]
fallback_git_user_name = "test-user"
fallback_git_user_email = "test@example.com"
default_stage_mode = "patch"
"""
    # Mock Path.exists to return True for init_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to return mock_toml_content
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.return_value = mock_toml_content

    # Act
    config = load_commit_config(mock_project_root, mock_cli_args_default)

    # Assert
    assert config.default_push is False
    assert config.allow_empty_commits is True
    assert config.conventional_commit_types == ["feat", "fix", "docs"]
    assert config.fallback_git_user_name == "test-user"
    assert config.fallback_git_user_email == "test@example.com"
    assert config.default_stage_mode == "patch"


def test_load_config_malformed_toml(
    mocker: MagicMock,
    mock_project_root: Path,
    mock_cli_args_default: argparse.Namespace,
):
    # Arrange
    init_toml_path = mock_project_root / ".khive" / "commit.toml"

    # Mock Path.exists to return True for init_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to raise a TOMLDecodeError
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.side_effect = tomllib.TOMLDecodeError("Test TOML error", "", 0)

    # Need to patch 'warn_msg' from the khive_commit module directly
    mock_warn_func = mocker.patch("khive.cli.khive_commit.warn_msg")

    # Act
    config = load_commit_config(mock_project_root, mock_cli_args_default)

    # Assert
    mock_warn_func.assert_called_once()
    # Check that config falls back to defaults
    assert config.default_push is True
    assert config.allow_empty_commits is False
    assert "feat" in config.conventional_commit_types


def test_load_config_cli_overrides(mocker: MagicMock, mock_project_root: Path):
    # Arrange
    init_toml_path = mock_project_root / ".khive" / "commit.toml"
    mock_toml_content = """
json_output = false
dry_run = false
verbose = false
"""
    # This TOML sets things that CLI args will override

    # Mock Path.exists to return True for init_toml_path
    mock_exists = mocker.patch("pathlib.Path.exists")
    mock_exists.return_value = True

    # Mock Path.read_text to return mock_toml_content
    mock_read_text = mocker.patch("pathlib.Path.read_text")
    mock_read_text.return_value = mock_toml_content

    cli_args = create_mock_cli_args(
        project_root=mock_project_root, json_output=True, dry_run=True, verbose=True
    )

    # Act
    config = load_commit_config(mock_project_root, cli_args)

    # Assert
    assert config.json_output is True
    assert config.dry_run is True
    assert config.verbose is True


# Unit Tests for Commit Message Construction


def test_build_commit_message_from_args_complete():
    # Arrange
    args = create_mock_cli_args(
        type="feat",
        scope="ui",
        subject="add dark mode",
        body="Detailed explanation of the feature",
        breaking_change_description="This changes the theme API",
        closes="123",
        search_id="pplx-abc",
    )
    config = CommitConfig(project_root=Path("/test"))

    # Act
    message = build_commit_message_from_args(args, config)

    # Assert
    assert message.startswith("feat(ui)!: add dark mode")
    assert "Detailed explanation of the feature" in message
    assert "BREAKING CHANGE: This changes the theme API" in message
    assert "Closes #123" in message
    assert "(search: pplx-abc)" in message


def test_build_commit_message_from_args_minimal():
    # Arrange
    args = create_mock_cli_args(type="fix", subject="correct typo")
    config = CommitConfig(project_root=Path("/test"))

    # Act
    message = build_commit_message_from_args(args, config)

    # Assert
    assert message == "fix: correct typo"


def test_build_commit_message_from_args_positional_precedence():
    # Arrange
    args = create_mock_cli_args(
        message="docs: update README", type="feat", scope="ui", subject="add dark mode"
    )
    config = CommitConfig(project_root=Path("/test"))

    # Act
    message = build_commit_message_from_args(args, config)

    # Assert
    assert message == "docs: update README"


def test_build_commit_message_from_args_insufficient():
    # Arrange
    args = create_mock_cli_args(type="fix")  # Missing subject
    config = CommitConfig(project_root=Path("/test"))

    # Act
    message = build_commit_message_from_args(args, config)

    # Assert
    assert message is None


def test_conventional_commit_regex_validation():
    # Arrange
    config = CommitConfig(project_root=Path("/test"))

    # Act & Assert
    valid_messages = [
        "feat: add feature",
        "fix(core): resolve bug",
        "docs!: update breaking docs",
        "feat(ui)!: redesign interface",
    ]

    invalid_messages = [
        "feature: add something",  # Invalid type
        "feat - add feature",  # Invalid format
        "feat:",  # Missing subject
    ]

    for msg in valid_messages:
        assert (
            config.conventional_commit_regex.match(msg) is not None
        ), f"Should match: {msg}"

    for msg in invalid_messages:
        assert (
            config.conventional_commit_regex.match(msg) is None
        ), f"Should not match: {msg}"


# Unit Tests for Git Operations


def test_git_run_normal_execution(mocker: MagicMock):
    # Arrange
    mock_subprocess = mocker.patch("subprocess.run")
    mock_subprocess.return_value = subprocess.CompletedProcess(
        ["git", "status"], 0, stdout="success", stderr=""
    )
    cmd_args = ["status"]
    cwd = Path("/test")

    # Act
    result = git_run(cmd_args, capture=True, check=True, dry_run=False, cwd=cwd)

    # Assert
    mock_subprocess.assert_called_once_with(
        ["git", "status"], text=True, capture_output=True, check=True, cwd=cwd
    )
    assert result.stdout == "success"


def test_git_run_dry_run_mode(mocker: MagicMock):
    # Arrange
    mock_subprocess = mocker.patch("subprocess.run")
    cmd_args = ["status"]
    cwd = Path("/test")

    # Act
    result = git_run(cmd_args, capture=True, check=True, dry_run=True, cwd=cwd)

    # Assert
    mock_subprocess.assert_not_called()
    assert result == 0 or (hasattr(result, "returncode") and result.returncode == 0)


def test_ensure_git_identity(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # First call: user.name not set, second call: user.email is set
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "config", "--get", "user.name"], 1, stdout="", stderr=""
        ),
        0,  # set user.name
        subprocess.CompletedProcess(
            ["git", "config", "--get", "user.email"],
            0,
            stdout="test@example.com",
            stderr="",
        ),
    ]

    config = CommitConfig(
        project_root=Path("/test"),
        fallback_git_user_name="test-user",
        fallback_git_user_email="test@example.com",
    )

    # Act
    ensure_git_identity(config)

    # Assert
    assert mock_git_run.call_count == 3
    # Check first call - get user.name
    assert mock_git_run.call_args_list[0][0][0] == ["config", "--get", "user.name"]
    # Check second call - set user.name
    assert mock_git_run.call_args_list[1][0][0] == ["config", "user.name", "test-user"]
    # Check third call - get user.email
    assert mock_git_run.call_args_list[2][0][0] == ["config", "--get", "user.email"]
    # No fourth call because email was set


def test_get_current_branch(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.return_value = subprocess.CompletedProcess(
        ["git", "branch", "--show-current"], 0, stdout="feature/test-branch", stderr=""
    )
    config = CommitConfig(project_root=Path("/test"))

    # Act
    branch = get_current_branch(config)

    # Assert
    assert branch == "feature/test-branch"
    mock_git_run.assert_called_once_with(
        ["branch", "--show-current"], capture=True, check=False, cwd=config.project_root
    )


def test_get_current_branch_dry_run(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    config = CommitConfig(project_root=Path("/test"), dry_run=True)

    # Act
    branch = get_current_branch(config)

    # Assert
    assert branch == "feature/dry-run-branch"  # Updated default for dry run
    mock_git_run.assert_not_called()


def test_stage_changes_all_mode(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # First call: working tree is dirty, second call: git add -A, third call: changes are staged
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "diff", "--quiet"], 1, stdout="", stderr=""
        ),
        0,  # git add -A
        subprocess.CompletedProcess(
            ["git", "diff", "--cached", "--quiet"], 1, stdout="", stderr=""
        ),
    ]
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = stage_changes("all", config)

    # Assert
    assert result is True  # Changes were staged
    assert mock_git_run.call_count == 3
    # Check second call - git add -A
    assert mock_git_run.call_args_list[1][0][0] == ["add", "-A"]


def test_stage_changes_patch_mode(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # First call: working tree is dirty, third call: changes are staged
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "diff", "--quiet"], 1, stdout="", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "diff", "--cached", "--quiet"], 1, stdout="", stderr=""
        ),
    ]
    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_subprocess_run.return_value = subprocess.CompletedProcess(
        ["git", "add", "-p"], 0, stdout="", stderr=""
    )

    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = stage_changes("patch", config)

    # Assert
    assert result is True  # Changes were staged
    mock_subprocess_run.assert_called_once_with(
        ["git", "add", "-p"], cwd=config.project_root
    )


def test_stage_changes_no_changes(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # First call: working tree is clean, second call: nothing is staged
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "diff", "--quiet"], 0, stdout="", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "diff", "--cached", "--quiet"], 0, stdout="", stderr=""
        ),
    ]
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = stage_changes("all", config)

    # Assert
    assert result is False  # No changes to stage


# Unit Tests for Main Workflow


def test_main_commit_flow_success(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: test commit",
    )
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(["git", "commit"], 0, stdout="", stderr=""),
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="abcdef1234567890", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 0, stdout="main", stderr=""
        ),
        # Add the new git config calls for branch tracking detection
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.remote"], 0, stdout="origin", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.merge"],
            0,
            stdout="refs/heads/main",
            stderr="",
        ),
        subprocess.CompletedProcess(
            ["git", "push", "origin", "main"], 0, stdout="", stderr=""
        ),
    ]

    args = create_mock_cli_args(message="feat: test commit", push=True)
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["commit_sha"] == "abcdef1234567890"
    assert result["push_status"] == "OK"
    assert result["branch_pushed"] == "main"
    assert result["branch_pushed"] == "main"


def test_main_commit_flow_nothing_to_commit(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=False)
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    args = create_mock_cli_args(message="feat: test commit")
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "skipped"
    assert "Nothing to commit" in result["message"]


def test_main_commit_flow_invalid_message(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    args = create_mock_cli_args(message="invalid commit message")
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "failure"
    assert "does not follow Conventional Commits pattern" in result["message"]


def test_main_commit_flow_commit_failure(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: test commit",
    )
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.return_value = subprocess.CompletedProcess(
        ["git", "commit"], 1, stdout="", stderr="error: could not commit"
    )

    args = create_mock_cli_args(message="feat: test commit")
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "failure"
    assert "Git commit command failed" in result["message"]


def test_main_commit_flow_push_failure(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: test commit",
    )
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(["git", "commit"], 0, stdout="", stderr=""),
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="abcdef1234567890", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 0, stdout="main", stderr=""
        ),
        # Add the new git config calls for branch tracking detection
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.remote"], 0, stdout="origin", stderr=""
        ),
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.merge"],
            0,
            stdout="refs/heads/main",
            stderr="",
        ),
        subprocess.CompletedProcess(
            ["git", "push", "origin", "main"],
            1,
            stdout="",
            stderr="error: could not push",
        ),
    ]

    args = create_mock_cli_args(message="feat: test commit", push=True)
    config = CommitConfig(project_root=Path("/test"))

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert "but pushing branch 'main' to origin failed" in result["message"]
    assert "abcdef1234567890" in result["message"]
    assert result["push_status"] == "FAILED"
    assert result["push_details"] == "error: could not push"


# CLI Interface Tests


def test_cli_entry_valid_message(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_commit.py", "feat: test commit"])
    mock_main_flow = mocker.patch("khive.cli.khive_commit._main_commit_flow")
    mock_main_flow.return_value = {"status": "success", "message": "Commit successful"}
    mock_load_config = mocker.patch("khive.cli.khive_commit.load_commit_config")
    mock_load_config.return_value = CommitConfig(project_root=Path("/test"))
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True

    # Act
    main()

    # Assert
    mock_main_flow.assert_called_once()
    args = mock_main_flow.call_args[0][0]
    assert args.message == "feat: test commit"


def test_cli_entry_structured_args(mocker: MagicMock):
    # Arrange
    mocker.patch(
        "sys.argv",
        [
            "khive_commit.py",
            "--type",
            "feat",
            "--scope",
            "ui",
            "--subject",
            "add dark mode",
            "--search-id",
            "pplx-abc",
        ],
    )
    mock_main_flow = mocker.patch("khive.cli.khive_commit._main_commit_flow")
    mock_main_flow.return_value = {"status": "success", "message": "Commit successful"}
    mock_load_config = mocker.patch("khive.cli.khive_commit.load_commit_config")
    mock_load_config.return_value = CommitConfig(project_root=Path("/test"))
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True

    # Act
    main()

    # Assert
    mock_main_flow.assert_called_once()
    args = mock_main_flow.call_args[0][0]
    assert args.type == "feat"
    assert args.scope == "ui"
    assert args.subject == "add dark mode"
    assert args.search_id == "pplx-abc"


def test_cli_entry_no_message_strategy(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_commit.py"])  # No message or structured args
    mock_die_commit = mocker.patch("khive.cli.khive_commit.die_commit")
    mock_load_config = mocker.patch("khive.cli.khive_commit.load_commit_config")
    mock_load_config.return_value = CommitConfig(project_root=Path("/test"))
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError
    mocker.patch(
        "khive.cli.khive_commit._main_commit_flow"
    )  # Mock _main_commit_flow to prevent it from being called

    # Act
    main()

    # Assert
    mock_die_commit.assert_called_once()
    assert "No commit message strategy" in mock_die_commit.call_args[0][0]


def test_cli_entry_project_root_not_dir(mocker: MagicMock):
    # Arrange
    mocker.patch(
        "sys.argv",
        ["khive_commit.py", "feat: test commit", "--project-root", "/nonexistent"],
    )
    mock_die_commit = mocker.patch(
        "khive.cli.khive_commit.die_commit", side_effect=SystemExit(1)
    )
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = False
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError

    # Act
    with pytest.raises(SystemExit):
        main()

    # Assert
    mock_die_commit.assert_called_once_with(
        "Project root not a directory: /nonexistent", json_output_flag=False
    )
    assert "Project root not a directory" in mock_die_commit.call_args[0][0]


def test_cli_entry_json_output(mocker: MagicMock):
    # Arrange
    mocker.patch("sys.argv", ["khive_commit.py", "feat: test commit", "--json-output"])
    mock_main_flow = mocker.patch("khive.cli.khive_commit._main_commit_flow")
    mock_main_flow.return_value = {"status": "success", "message": "Commit successful"}
    mock_load_config = mocker.patch("khive.cli.khive_commit.load_commit_config")
    mock_load_config.return_value = CommitConfig(
        project_root=Path("/test"), json_output=True
    )
    mock_path_is_dir = mocker.patch("pathlib.Path.is_dir")
    mock_path_is_dir.return_value = True
    mocker.patch("os.chdir")  # Mock os.chdir to prevent FileNotFoundError
    mock_json_dumps = mocker.patch("json.dumps")
    mock_print = mocker.patch("builtins.print")

    # Act
    main()

    # Assert
    mock_json_dumps.assert_called_once_with(
        {"status": "success", "message": "Commit successful"}, indent=2
    )
    mock_print.assert_called_once_with(mock_json_dumps.return_value)


# Tests for Branch Publishing Feature


def test_main_commit_flow_publish_new_branch(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: publish new feature",
    )
    mocker.patch("os.chdir")

    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # Simulate: commit, get SHA, get current branch, check remote (not found), check merge (not found), push with --set-upstream
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "commit"], 0, stdout="", stderr=""
        ),  # commit
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="newsha123", stderr=""
        ),  # get sha
        subprocess.CompletedProcess(
            ["git", "branch", "--show-current"],
            0,
            stdout="feature/new-branch",
            stderr="",
        ),  # get current branch
        subprocess.CompletedProcess(
            ["git", "config", "branch.feature/new-branch.remote"],
            1,
            stdout="",
            stderr="",
        ),  # remote not set
        subprocess.CompletedProcess(
            ["git", "config", "branch.feature/new-branch.merge"],
            1,
            stdout="",
            stderr="",
        ),  # merge not set
        subprocess.CompletedProcess(
            ["git", "push", "--set-upstream", "origin", "feature/new-branch"],
            0,
            stdout="",
            stderr="",
        ),  # push
    ]

    args = create_mock_cli_args(
        message="feat: publish new feature", push=True
    )  # Explicitly push=True
    config = CommitConfig(
        project_root=Path("/test"), default_push=True
    )  # Config also defaults to push

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["commit_sha"] == "newsha123"
    assert result["push_status"] == "OK"
    assert result["branch_pushed"] == "feature/new-branch"
    # Check that git_run was called for push with '--set-upstream'
    push_call = mock_git_run.call_args_list[-1]  # Last call should be the push
    assert push_call[0][0] == ["push", "--set-upstream", "origin", "feature/new-branch"]
    assert "Publishing and setting upstream" in result["message"]


def test_main_commit_flow_push_existing_tracked_branch(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="fix: update existing feature",
    )
    mocker.patch("os.chdir")

    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    # Simulate: commit, get SHA, get current branch, check remote (found), check merge (found), push without --set-upstream
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "commit"], 0, stdout="", stderr=""
        ),  # commit
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="existingsha", stderr=""
        ),  # get sha
        subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 0, stdout="main", stderr=""
        ),  # get current branch
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.remote"], 0, stdout="origin", stderr=""
        ),  # remote set
        subprocess.CompletedProcess(
            ["git", "config", "branch.main.merge"],
            0,
            stdout="refs/heads/main",
            stderr="",
        ),  # merge set
        subprocess.CompletedProcess(
            ["git", "push", "origin", "main"], 0, stdout="", stderr=""
        ),  # push
    ]

    args = create_mock_cli_args(message="fix: update existing feature", push=True)
    config = CommitConfig(project_root=Path("/test"), default_push=True)

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["commit_sha"] == "existingsha"
    assert result["push_status"] == "OK"
    assert result["branch_pushed"] == "main"
    push_call = mock_git_run.call_args_list[-1]
    assert push_call[0][0] == ["push", "origin", "main"]  # No --set-upstream
    assert "Pushing branch" in result["message"]


def test_main_commit_flow_publish_new_branch_dry_run(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: dry run publish",
    )
    mocker.patch("os.chdir")
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")

    # Dry run: commit (ret 0), get SHA (ret 0), get branch (ret 'feature/dry-branch'), push (ret 0)
    mock_git_run.side_effect = [
        0,  # dry run commit
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="DRY_RUN_SHA_FROM_MOCK", stderr=""
        ),  # actual call for sha in dry_run
        0,  # dry run get_current_branch (note: get_current_branch has its own dry run path)
        0,  # dry run push with --set-upstream
    ]
    # Mock get_current_branch specifically for its dry_run path if its not fully mocked by git_run side_effect
    mocker.patch(
        "khive.cli.khive_commit.get_current_branch", return_value="feature/dry-branch"
    )

    args = create_mock_cli_args(
        message="feat: dry run publish", push=True, dry_run=True
    )
    config = CommitConfig(
        project_root=Path("/test"), default_push=True, dry_run=True
    )  # Ensure config also knows about dry_run

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["commit_sha"] == "DRY_RUN_SHA"  # As per _main_commit_flow logic
    assert (
        result["push_status"] == "OK"
    )  # Changed from OK_DRY_RUN to match implementation
    assert result["branch_pushed"] == "feature/dry-branch"

    # Verify the push command shown in dry run includes --set-upstream
    # The actual call to git_run for push would have dry_run=True
    # We need to check the arguments it *would* have been called with.
    # The `info_msg` inside _main_commit_flow for dry_run push will indicate the --set-upstream.
    # And `git_run` itself logs "[DRY-RUN] Would run: git push --set-upstream origin feature/dry-branch"
    # So we check the `message` field that combines these.
    assert (
        "Publishing and setting upstream for branch 'feature/dry-branch'"
        in result["message"]
    )

    # Last call to git_run (the push) should reflect the --set-upstream
    push_call_args = None
    for call_args in mock_git_run.call_args_list:
        if (
            len(call_args[0][0]) > 0 and call_args[0][0][0] == "push"
        ):  # Check the command part
            push_call_args = call_args[0][0]
            break
    assert push_call_args == ["push", "--set-upstream", "origin", "feature/dry-branch"]


def test_main_commit_flow_no_push_flag_skips_push(mocker: MagicMock):
    # Arrange
    mocker.patch("khive.cli.khive_commit.ensure_git_identity")
    mocker.patch("khive.cli.khive_commit.stage_changes", return_value=True)
    mocker.patch(
        "khive.cli.khive_commit.build_commit_message_from_args",
        return_value="feat: no push test",
    )
    mocker.patch("os.chdir")
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.side_effect = [  # Only commit and SHA, no push related calls
        subprocess.CompletedProcess(["git", "commit"], 0, stdout="", stderr=""),
        subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="nopushSHA", stderr=""
        ),
    ]
    args = create_mock_cli_args(
        message="feat: no push test", push=False
    )  # Explicitly push=False (--no-push)
    config = CommitConfig(
        project_root=Path("/test"), default_push=True
    )  # Config defaults to push, but CLI overrides

    # Act
    result = _main_commit_flow(args, config)

    # Assert
    assert result["status"] == "success"
    assert result["commit_sha"] == "nopushSHA"
    assert result["push_status"] == "SKIPPED"
    # Ensure no 'git push' or 'git config' for branch remote/merge was called
    for call in mock_git_run.call_args_list:
        assert call[0][0][0] != "push"
        assert not (call[0][0][0] == "config" and "branch." in call[0][0][1])


def test_get_current_branch_detached_head(mocker: MagicMock):
    # Arrange
    mock_git_run = mocker.patch("khive.cli.khive_commit.git_run")
    mock_git_run.side_effect = [
        subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 0, stdout="", stderr=""
        ),  # No current branch name
        subprocess.CompletedProcess(
            ["git", "rev-parse", "--short", "HEAD"], 0, stdout="abcdef", stderr=""
        ),  # Short SHA
    ]
    config = CommitConfig(project_root=Path("/test-detached"))

    # Act
    branch = get_current_branch(config)

    # Assert
    assert branch == "detached-HEAD-abcdef"
    assert mock_git_run.call_count == 2
    assert mock_git_run.call_args_list[0][0][0] == ["branch", "--show-current"]
    assert mock_git_run.call_args_list[1][0][0] == ["rev-parse", "--short", "HEAD"]


def test_cli_push_flag_logic(mocker: MagicMock):
    # Test cases: (sys_argv_suffix, config_default_push, expected_args_push_value_in_flow)
    # args.push is what argparse sets: True for --push, False for --no-push, None if neither.
    # _main_commit_flow then decides based on args.push and config.default_push.
    test_scenarios = [
        (["--push"], False, True),  # CLI --push overrides config
        (["--push"], True, True),  # CLI --push confirms config
        (["--no-push"], True, False),  # CLI --no-push overrides config
        (["--no-push"], False, False),  # CLI --no-push confirms config
        ([], True, True),  # No CLI flag, use config default_push = True
        ([], False, False),  # No CLI flag, use config default_push = False
    ]

    for argv_suffix, cfg_default_push, expected_should_push in test_scenarios:
        mocker.resetall()  # Reset mocks for each scenario
        base_argv = ["khive_commit.py", "feat: test push logic"]
        mocker.patch("sys.argv", base_argv + argv_suffix)

        mock_main_flow = mocker.patch("khive.cli.khive_commit._main_commit_flow")
        mock_main_flow.return_value = {"status": "success", "message": "Mocked flow"}

        mock_path_is_dir = mocker.patch("pathlib.Path.is_dir", return_value=True)
        mocker.patch("os.chdir")

        # Setup config for load_commit_config
        # Create a factory function that returns a new function with the value baked in
        def create_config_loader(default_push_value):
            def config_loader(project_r, cli_args_ns):
                # cli_args_ns already has args.push correctly set by argparse
                # We just need to ensure the CommitConfig object has the correct default_push
                return CommitConfig(
                    project_root=project_r,
                    default_push=default_push_value,  # Use the baked-in value
                    json_output=cli_args_ns.json_output,
                    dry_run=cli_args_ns.dry_run,
                    verbose=cli_args_ns.verbose,
                )

            return config_loader

        # Create a specific loader function for this iteration
        side_effect_load_config = create_config_loader(cfg_default_push)

        mocker.patch(
            "khive.cli.khive_commit.load_commit_config",
            side_effect=side_effect_load_config,
        )

        main()  # Run the CLI entry point

        called_args, called_config = mock_main_flow.call_args[0]

        # Check the args.push value passed to _main_commit_flow
        argparse_push_value = None
        if "--push" in argv_suffix:
            argparse_push_value = True
        elif "--no-push" in argv_suffix:
            argparse_push_value = False

        assert (
            called_args.push == argparse_push_value
        ), f"Scenario: {argv_suffix}, cfg_default_push={cfg_default_push}"
        assert called_config.default_push == cfg_default_push

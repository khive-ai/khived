"""
Tests for khive_new_doc.py
"""

import argparse
import datetime as dt
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# from khive.cli.khive_cli import cli as khive_cli_group  # Import the main CLI group - Not used by current tests
from khive.cli.khive_new_doc import (
    NewDocConfig,
    Template,
    create_document,
    discover_templates,
    find_template,
    load_new_doc_config,
    main,
    parse_frontmatter,
    substitute_placeholders,
)

# --- Fixtures ---


@pytest.fixture
def mock_toml_file(tmp_path):
    """Create a mock TOML config file."""
    config_dir = tmp_path / ".khive"
    config_dir.mkdir()
    config_file = config_dir / "new_doc.toml"
    config_file.write_text(
        """
    default_destination_base_dir = "custom_reports"
    custom_template_dirs = ["templates", "/abs/path/templates"]

    [default_vars]
    author = "Test Author"
    project = "Test Project"
    """
    )
    return tmp_path


@pytest.fixture
def mock_template_dirs(tmp_path):
    """Create mock template directories with templates."""
    # Create multiple template directories
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Create templates in dir1
    template1 = dir1 / "template1.md"
    template1.write_text(
        """---
doc_type: TPL1
title: "Template 1"
output_subdir: tpl1s
---
Template 1 content with {{IDENTIFIER}} and {{DATE}}
"""
    )

    # Create templates in dir2
    template2 = dir2 / "template2.md"
    template2.write_text(
        """---
doc_type: TPL2
title: "Template 2"
output_subdir: tpl2s
---
Template 2 content with {{IDENTIFIER}} and {{DATE}}
"""
    )

    return {"root": tmp_path, "dirs": [dir1, dir2]}


@pytest.fixture
def mock_template():
    """Create a mock Template object."""
    return Template(
        path=Path("template.md"),
        doc_type="TEST",
        title="Test Template",
        output_subdir="tests",
        filename_prefix="TEST",
        meta={"doc_type": "TEST", "title": "Test Template", "output_subdir": "tests"},
        body_template="Hello {{NAME}}, today is {{DATE}}. Your ID is {{IDENTIFIER}}.",
    )


@pytest.fixture
def mock_args():
    """Create mock CLI args."""
    args = argparse.Namespace()
    args.json_output = True
    args.dry_run = True
    args.verbose = True
    return args


# --- Tests for Configuration ---


def test_load_config_from_file(mock_toml_file):
    """Test loading configuration from TOML file."""
    # Arrange
    project_root = mock_toml_file

    # Act
    config = load_new_doc_config(project_root)

    # Assert
    assert config.default_destination_base_dir == "custom_reports"
    assert "templates" in config.custom_template_dirs
    assert "/abs/path/templates" in config.custom_template_dirs
    assert config.default_vars["author"] == "Test Author"
    assert config.default_vars["project"] == "Test Project"


def test_default_config(tmp_path):
    """Test default configuration when no file is present."""
    # Arrange
    project_root = tmp_path

    # Act
    config = load_new_doc_config(project_root)

    # Assert
    assert config.default_destination_base_dir == ".khive/reports"
    assert config.custom_template_dirs == []
    assert config.default_vars == {}


def test_cli_args_override_config(mock_toml_file, mock_args):
    """Test that CLI arguments override configuration file values."""
    # Arrange
    project_root = mock_toml_file

    # Act
    config = load_new_doc_config(project_root, mock_args)

    # Assert
    assert config.json_output is True
    assert config.dry_run is True
    assert config.verbose is True


# --- Tests for Template Discovery ---


def test_parse_frontmatter():
    """Test parsing frontmatter from template content."""
    # Arrange
    content = """---
doc_type: TEST
title: "Test Template"
output_subdir: tests
---
Template content
"""

    # Act
    meta, body = parse_frontmatter(content, Path("test.md"))

    # Assert
    assert meta["doc_type"] == "TEST"
    assert meta["title"] == "Test Template"
    assert meta["output_subdir"] == "tests"
    assert body == "Template content"


def test_parse_frontmatter_missing():
    """Test parsing content without frontmatter."""
    # Arrange
    content = "Template content without frontmatter"

    # Act
    meta, body = parse_frontmatter(content, Path("test.md"))

    # Assert
    assert meta == {}
    assert body == "Template content without frontmatter"


def test_discover_templates(mock_template_dirs):
    """Test discovering templates across multiple directories."""
    # Arrange
    config = NewDocConfig(project_root=mock_template_dirs["root"])
    config.custom_template_dirs = [
        str(d.relative_to(mock_template_dirs["root"]))
        for d in mock_template_dirs["dirs"]
    ]

    # Act
    templates = discover_templates(config)

    # Assert
    assert len(templates) == 2
    template_types = [t.doc_type for t in templates]
    assert "TPL1" in template_types
    assert "TPL2" in template_types


def test_find_template_by_doc_type(mock_template_dirs):
    """Test finding a template by doc_type."""
    # Arrange
    config = NewDocConfig(project_root=mock_template_dirs["root"])
    config.custom_template_dirs = [
        str(d.relative_to(mock_template_dirs["root"]))
        for d in mock_template_dirs["dirs"]
    ]
    templates = discover_templates(config)

    # Act
    template = find_template("TPL1", templates)

    # Assert
    assert template is not None
    assert template.doc_type == "TPL1"


def test_find_template_by_filename(mock_template_dirs):
    """Test finding a template by filename."""
    # Arrange
    config = NewDocConfig(project_root=mock_template_dirs["root"])
    config.custom_template_dirs = [
        str(d.relative_to(mock_template_dirs["root"]))
        for d in mock_template_dirs["dirs"]
    ]
    templates = discover_templates(config)

    # Act
    template = find_template("template1.md", templates)

    # Assert
    assert template is not None
    assert template.path.name == "template1.md"


def test_find_template_not_found(mock_template_dirs):
    """Test finding a template that doesn't exist."""
    # Arrange
    config = NewDocConfig(project_root=mock_template_dirs["root"])
    config.custom_template_dirs = [
        str(d.relative_to(mock_template_dirs["root"]))
        for d in mock_template_dirs["dirs"]
    ]
    templates = discover_templates(config)

    # Act
    template = find_template("NONEXISTENT", templates)

    # Assert
    assert template is None


# --- Tests for Placeholder Substitution ---


def test_standard_placeholders():
    """Test substituting standard placeholders."""
    # Arrange
    text = "Date: {{DATE}}, ID: {{IDENTIFIER}}"
    identifier = "test-id"
    custom_vars = {}
    today = dt.date.today().isoformat()

    # Act
    result = substitute_placeholders(text, identifier, custom_vars)

    # Assert
    assert f"Date: {today}" in result
    assert "ID: test-id" in result


def test_custom_variables():
    """Test substituting custom variables."""
    # Arrange
    text = "Hello {{NAME}}, welcome to {{PROJECT}}"
    identifier = "test-id"
    custom_vars = {"NAME": "John", "PROJECT": "Khive"}

    # Act
    result = substitute_placeholders(text, identifier, custom_vars)

    # Assert
    assert "Hello John, welcome to Khive" in result


def test_alternative_placeholder_formats():
    """Test substituting alternative placeholder formats."""
    # Arrange
    text = "Issue: <issue>, ID: <identifier>"
    identifier = "test-id"
    custom_vars = {}

    # Act
    result = substitute_placeholders(text, identifier, custom_vars)

    # Assert
    assert "Issue: test-id, ID: test-id" in result


# --- Tests for Document Creation ---


def test_create_document(tmp_path, mock_template):
    """Test creating a document."""
    # Arrange
    config = NewDocConfig(project_root=tmp_path)
    custom_vars = {"NAME": "John"}

    # Act
    result = create_document(
        template=mock_template,
        identifier="test-id",
        config=config,
        cli_dest_base_dir=None,
        custom_vars_cli=custom_vars,
        force_overwrite=False,
    )

    # Assert
    assert result["status"] == "success"
    output_path = tmp_path / ".khive/reports" / "tests" / "TEST-test-id.md"
    assert output_path.exists()
    content = output_path.read_text()
    assert "Hello John" in content
    assert f"today is {dt.date.today().isoformat()}" in content
    assert "Your ID is test-id" in content


def test_create_document_file_exists(tmp_path, mock_template):
    """Test creating a document when the file already exists."""
    # Arrange
    config = NewDocConfig(project_root=tmp_path)
    custom_vars = {"NAME": "John"}

    # Create initial document
    output_dir = tmp_path / ".khive/reports" / "tests"
    output_dir.mkdir(parents=True)
    output_path = output_dir / "TEST-test-id.md"
    output_path.write_text("Original content")

    # Act
    result = create_document(
        template=mock_template,
        identifier="test-id",
        config=config,
        cli_dest_base_dir=None,
        custom_vars_cli=custom_vars,
        force_overwrite=False,
    )

    # Assert
    # Assert
    assert result["status"] == "error"  # Updated from "failure"
    assert (
        result["message"]
        == "Output file '.khive/reports/tests/TEST-test-id.md' already exists. Use --force to overwrite."
    )
    assert "Original content" in output_path.read_text()


def test_create_document_force_overwrite(tmp_path, mock_template):
    """Test creating a document with force overwrite."""
    # Arrange
    config = NewDocConfig(project_root=tmp_path)
    custom_vars = {"NAME": "John"}

    # Create initial document
    output_dir = tmp_path / ".khive/reports" / "tests"
    output_dir.mkdir(parents=True)
    output_path = output_dir / "TEST-test-id.md"
    output_path.write_text("Original content")

    # Act
    result = create_document(
        template=mock_template,
        identifier="test-id",
        config=config,
        cli_dest_base_dir=None,
        custom_vars_cli=custom_vars,
        force_overwrite=True,
    )

    # Assert
    assert result["status"] == "success"
    content = output_path.read_text()
    assert "Hello John" in content
    assert "Original content" not in content


def test_create_document_dry_run(tmp_path, mock_template):
    """Test creating a document with dry run."""
    # Arrange
    config = NewDocConfig(project_root=tmp_path)
    config.dry_run = True
    custom_vars = {"NAME": "John"}

    # Act
    result = create_document(
        template=mock_template,
        identifier="test-id",
        config=config,
        cli_dest_base_dir=None,
        custom_vars_cli=custom_vars,
        force_overwrite=False,
    )

    # Assert
    assert result["status"] == "success_dry_run"
    output_path = tmp_path / ".khive/reports" / "tests" / "TEST-test-id.md"
    assert not output_path.exists()


# --- Tests for CLI Integration ---


@patch("sys.argv", ["khive_new_doc.py", "--list-templates"])
@patch("khive.cli.khive_new_doc.discover_templates")
@patch("khive.cli.khive_new_doc.load_new_doc_config")
def test_cli_list_templates(mock_load_config, mock_discover, capsys):
    """Test listing templates via CLI."""
    # Arrange
    mock_config = MagicMock()
    mock_config.json_output = False
    mock_load_config.return_value = mock_config

    mock_template1 = MagicMock()
    mock_template1.doc_type = "TPL1"
    mock_template1.title = "Template 1"
    mock_template1.path = Path("template1.md")
    mock_template1.output_subdir = "tpl1s"
    mock_template1.filename_prefix = "TPL1"

    mock_template2 = MagicMock()
    mock_template2.doc_type = "TPL2"
    mock_template2.title = "Template 2"
    mock_template2.path = Path("template2.md")
    mock_template2.output_subdir = "tpl2s"
    mock_template2.filename_prefix = "TPL2"

    mock_discover.return_value = [mock_template1, mock_template2]

    # Act
    main()

    # Assert
    captured = capsys.readouterr()
    assert "TPL1" in captured.out
    assert "TPL2" in captured.out
    assert "Template 1" in captured.out
    assert "Template 2" in captured.out


def test_cli_create_document(tmp_path):
    """Test creating a document directly."""
    # This is a more direct test of the create_document function
    # rather than testing the CLI entry point which is more complex to mock

    # Arrange
    template = Template(
        path=Path("template.md"),
        doc_type="TEST",
        title="Test Template",
        output_subdir="tests",
        filename_prefix="TEST",
        meta={"doc_type": "TEST", "title": "Test Template", "output_subdir": "tests"},
        body_template="Hello {{NAME}}, today is {{DATE}}. Your ID is {{IDENTIFIER}}.",
    )

    config = NewDocConfig(project_root=tmp_path)
    custom_vars = {"NAME": "John"}

    # Act
    result = create_document(
        template=template,
        identifier="test-id",
        config=config,
        cli_dest_base_dir=None,
        custom_vars_cli=custom_vars,
        force_overwrite=False,
    )

    # Assert
    assert result["status"] == "success"
    output_path = tmp_path / ".khive/reports" / "tests" / "TEST-test-id.md"
    assert output_path.exists()
    content = output_path.read_text()
    assert "Hello John" in content
    assert "Your ID is test-id" in content


@patch("sys.argv", ["khive_new_doc.py", "TEST", "test-id", "--json-output"])
@patch("khive.cli.khive_new_doc.discover_templates")
@patch("khive.cli.khive_new_doc.find_template")
@patch("khive.cli.khive_new_doc.create_document")
@patch("khive.cli.khive_new_doc.load_new_doc_config")
def test_cli_json_output(
    mock_load_config, mock_create, mock_find, mock_discover, capsys
):
    """Test JSON output via CLI."""
    # Arrange
    mock_config = MagicMock()
    mock_config.json_output = True
    mock_load_config.return_value = mock_config

    mock_template = MagicMock()
    mock_template.doc_type = "TEST"
    mock_find.return_value = mock_template

    mock_discover.return_value = [mock_template]

    mock_create.return_value = {
        "status": "success",
        "message": "Document created: .khive/reports/tests/TEST-test-id.md",
        "created_file_path": ".khive/reports/tests/TEST-test-id.md",
        "template_used": "template.md",
    }

    # Act
    main()

    # Assert
    captured = capsys.readouterr()
    json_output = json.loads(captured.out)
    assert json_output["status"] == "success"
    assert json_output["created_file_path"] == ".khive/reports/tests/TEST-test-id.md"
    assert json_output["template_used"] == "template.md"


@patch("sys.argv", ["khive_new_doc.py", "NONEXISTENT", "test-id"])
@patch("khive.cli.khive_new_doc.discover_templates")
@patch("khive.cli.khive_new_doc.find_template")
@patch("khive.cli.khive_new_doc.load_new_doc_config")
@patch("khive.cli.khive_new_doc.die_doc")
@patch("khive.cli.khive_new_doc.create_document")
def test_cli_template_not_found(
    mock_create, mock_die_doc, mock_load_config, mock_find, mock_discover, capsys
):
    """Test error when template is not found."""
    # Arrange
    mock_config = MagicMock()
    mock_config.json_output = False
    mock_load_config.return_value = mock_config

    # Create a proper mock template with string attributes
    mock_template = MagicMock()
    mock_template.doc_type = "TEST"
    mock_template.path = MagicMock()
    mock_template.path.name = "test_template.md"
    mock_template.path.is_relative_to.return_value = True
    mock_template.path.relative_to.return_value = Path("test_template.md")

    # Return a list of string values for available types and files
    mock_discover.return_value = [mock_template]

    # Return None for find_template to trigger the error path
    mock_find.return_value = None

    # Mock die_doc to raise SystemExit, so we can catch it
    mock_die_doc.side_effect = SystemExit(1)

    # Act & Assert
    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    mock_die_doc.assert_called_once()
    # The actual message check is now implicitly handled by die_doc being called correctly before exit.
    # We can check the arguments passed to die_doc if needed, but the primary check is that it was called
    # and led to an exit.
    assert "Template 'NONEXISTENT' not found" in mock_die_doc.call_args[0][0]
    # Ensure create_document was not called
    mock_create.assert_not_called()


# --- New Tests for Enhanced Error Handling (CLI Invocation Style) ---
def test_cli_new_doc_file_exists_error_no_force(tmp_path, mocker, capsys):
    """Test CLI error when output file exists and --force is not used."""
    output_dir = tmp_path / ".khive" / "reports" / "ip"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_file = output_dir / "IP-cliexists.md"
    existing_file.write_text("Original CLI content")

    # Mock template discovery and rendering to isolate file existence check
    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy IP Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )

    # Patch sys.argv
    mocker.patch(
        "sys.argv",
        ["khive-new-doc", "IP", "cliexists", "--project-root", str(tmp_path)],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert (
        "Output file '.khive/reports/ip/IP-cliexists.md' already exists. Use --force to overwrite."
        in captured.err
    )
    assert existing_file.read_text() == "Original CLI content"
    assert existing_file.read_text() == "Original CLI content"


def test_cli_new_doc_file_exists_error_no_force_json(tmp_path, mocker, capsys):
    """Test CLI JSON error when output file exists and --force is not used."""
    output_dir = tmp_path / ".khive" / "reports" / "ip"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_file = output_dir / "IP-cliexistsjson.md"
    existing_file.write_text("Original CLI JSON content")

    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy IP Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )

    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "IP",
            "cliexistsjson",
            "--project-root",
            str(tmp_path),
            "--json-output",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    json_output = json.loads(captured.out)
    assert json_output["status"] == "error"
    assert (
        "Output file '.khive/reports/ip/IP-cliexistsjson.md' already exists. Use --force to overwrite."
        in json_output["message"]
    )
    assert existing_file.read_text() == "Original CLI JSON content"


def test_cli_new_doc_template_not_found_error(tmp_path, mocker, capsys):
    """Test CLI error when template is not found (no templates discovered)."""
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates", return_value=[]
    )  # No templates found
    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "NonExistentType",
            "test-id",
            "--project-root",
            str(tmp_path),
        ],
    )

    # Mock die_doc to check its call without exiting the test runner prematurely
    mock_die = mocker.patch("khive.cli.khive_new_doc.die_doc")
    mock_die.side_effect = SystemExit(1)  # Simulate exit

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    # die_doc is called before find_template if discover_templates returns empty
    mock_die.assert_called_once()
    assert "No templates found. Cannot create document." in mock_die.call_args[0][0]


def test_cli_new_doc_specific_template_not_found_error(tmp_path, mocker, capsys):
    """Test CLI error when a specific template is not found among existing ones."""
    mock_template_instance = Template(
        path=Path("actual_template.md"),
        doc_type="Actual",
        title="Actual Template",
        output_subdir="actual",
        filename_prefix="ACT",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=None
    )  # Specific template not found

    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "NonExistentType",
            "test-id",
            "--project-root",
            str(tmp_path),
        ],
    )
    mock_die = mocker.patch("khive.cli.khive_new_doc.die_doc")
    mock_die.side_effect = SystemExit(1)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    mock_die.assert_called_once()
    assert "Template 'NonExistentType' not found." in mock_die.call_args[0][0]
    assert "Available doc_types: Actual" in mock_die.call_args[0][0]


def test_cli_new_doc_template_not_found_error_json(tmp_path, mocker, capsys):
    """Test CLI JSON error when template is not found."""
    mocker.patch("khive.cli.khive_new_doc.discover_templates", return_value=[])
    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "NonExistentType",
            "test-id",
            "--project-root",
            str(tmp_path),
            "--json-output",
        ],
    )

    mock_die = mocker.patch("khive.cli.khive_new_doc.die_doc")

    # Let die_doc print to stdout for JSON capture, then raise SystemExit
    def die_side_effect(msg, json_output_flag, json_data=None):
        if json_output_flag:
            base_data = {"status": "failure", "message": msg}  # die_doc uses "failure"
            if json_data:
                base_data.update(json_data)
            print(json.dumps(base_data, indent=2))
        raise SystemExit(1)

    mock_die.side_effect = die_side_effect

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    json_output = json.loads(captured.out)
    assert json_output["status"] == "failure"  # die_doc uses "failure"
    assert "No templates found. Cannot create document." in json_output["message"]


def test_cli_new_doc_dest_not_writable_error(tmp_path, mocker, capsys):
    """Test CLI error when destination is not writable."""
    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )
    mocker.patch(
        "pathlib.Path.mkdir", side_effect=PermissionError("Test permission denied")
    )

    non_writable_dest_base = tmp_path / "locked_reports"
    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "IP",
            "testperm",
            "--project-root",
            str(tmp_path),
            "--dest",
            str(non_writable_dest_base),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert "Permission denied: Cannot create directory or write file" in captured.err
    assert "Test permission denied" in captured.err


def test_cli_new_doc_dest_not_writable_error_json(tmp_path, mocker, capsys):
    """Test CLI JSON error when destination is not writable."""
    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )
    mocker.patch(
        "pathlib.Path.mkdir", side_effect=PermissionError("Test permission denied JSON")
    )

    non_writable_dest_base = tmp_path / "locked_reports_json"
    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "IP",
            "testpermjson",
            "--project-root",
            str(tmp_path),
            "--dest",
            str(non_writable_dest_base),
            "--json-output",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    json_output = json.loads(captured.out)
    assert json_output["status"] == "error"
    assert (
        "Permission denied: Cannot create directory or write file"
        in json_output["message"]
    )
    assert "Test permission denied JSON" in json_output["message"]


def test_cli_new_doc_path_conflict_error(tmp_path, mocker, capsys):
    """Test CLI error when a path component is a file."""
    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )

    conflict_base = tmp_path / "reports_is_a_file.txt"
    conflict_base.write_text("I am a file, not a directory.")
    # Mock mkdir to raise FileExistsError when trying to create a dir where a file exists
    mocker.patch(
        "pathlib.Path.mkdir",
        side_effect=FileExistsError(
            f"[Errno 17] File exists: '{conflict_base / 'ip'}'"
        ),
    )

    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "IP",
            "testconflict",
            "--project-root",
            str(tmp_path),
            "--dest",
            str(conflict_base),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert "Path conflict: A component of the destination path" in captured.err
    assert str(conflict_base / "ip") in captured.err


def test_cli_new_doc_path_conflict_error_json(tmp_path, mocker, capsys):
    """Test CLI JSON error when a path component is a file."""
    mock_template_instance = Template(
        path=Path("dummy_template.md"),
        doc_type="IP",
        title="Dummy Template",
        output_subdir="ip",
        filename_prefix="IP",
        meta={},
        body_template="content",
    )
    mocker.patch(
        "khive.cli.khive_new_doc.discover_templates",
        return_value=[mock_template_instance],
    )
    mocker.patch(
        "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
    )
    mocker.patch(
        "khive.cli.khive_new_doc.substitute_placeholders",
        return_value="rendered_content",
    )

    conflict_base = tmp_path / "reports_is_a_file_json.txt"
    conflict_base.write_text("I am a file, not a directory.")
    mocker.patch(
        "pathlib.Path.mkdir",
        side_effect=FileExistsError(
            f"[Errno 17] File exists: '{conflict_base / 'ip'}'"
        ),
    )

    mocker.patch(
        "sys.argv",
        [
            "khive-new-doc",
            "IP",
            "testconflictjson",
            "--project-root",
            str(tmp_path),
            "--dest",
            str(conflict_base),
            "--json-output",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    json_output = json.loads(captured.out)
    assert json_output["status"] == "error"
    assert (
        "Path conflict: A component of the destination path" in json_output["message"]
    )
    assert str(conflict_base / "ip") in json_output["message"]


# --- New Tests for Enhanced Error Handling ---

# The tests below use CliRunner but there may be issues with the integration between
# khive_new_doc.py and the CLI group. Let's leave them as reference but we'll rely on
# the direct tests above using sys.argv and main() which are more reliable.

# --- CLI Group Integration Tests (Using CliRunner) ---
"""
# Commenting out CliRunner tests as sys.argv + main() is the preferred approach for these standalone script tests.
# These are kept for reference in case direct Click group testing becomes necessary later.

# def test_cli_new_doc_file_exists_error_no_force_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI error when output file exists and --force is not used, using CliRunner.\"\"\"
#     runner = CliRunner()
#     output_dir = tmp_path / ".khive" / "reports" / "ip"
#     output_dir.mkdir(parents=True, exist_ok=True)
#     existing_file = output_dir / "IP-cliexists.md"
#     existing_file.write_text("Original CLI content")

#     # Mock template discovery and rendering to isolate file existence check
#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy IP Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )

#     # result = runner.invoke(
#     #     khive_cli_group, ["new-doc", "IP", "cliexists", "--project-root", str(tmp_path)]
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # assert (
#     #     "Output file 'IP-cliexists.md' already exists. Use --force to overwrite."
#     #     in result.stderr
#     # )
#     # assert existing_file.read_text() == "Original CLI content"
#     pass # Test commented out


# def test_cli_new_doc_file_exists_error_no_force_json_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI JSON error when output file exists and --force is not used, using CliRunner.\"\"\"
#     runner = CliRunner()
#     output_dir = tmp_path / ".khive" / "reports" / "ip"
#     output_dir.mkdir(parents=True, exist_ok=True)
#     existing_file = output_dir / "IP-cliexistsjson.md"
#     existing_file.write_text("Original CLI JSON content")

#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy IP Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "IP",
#     #         "cliexistsjson",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--json-output",
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # json_output = json.loads(result.stdout)
#     # assert json_output["status"] == "error"
#     # assert (
#     #     "Output file 'IP-cliexistsjson.md' already exists. Use --force to overwrite."
#     #     in json_output["message"]
#     # )
#     # assert existing_file.read_text() == "Original CLI JSON content"
#     pass # Test commented out


# def test_cli_new_doc_template_not_found_error_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI error when template is not found, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates", return_value=[]
#     )  # No templates found

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     ["new-doc", "NonExistentType", "test-id", "--project-root", str(tmp_path)],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # # This error is now caught by die_doc earlier in the main() flow
#     # assert "No templates found. Cannot create document." in result.stderr
#     pass # Test commented out


# def test_cli_new_doc_template_not_found_specific_error_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI error when a specific template is not found among existing ones, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mock_template_instance = Template(
#         path=Path("actual_template.md"),
#         doc_type="Actual",
#         title="Actual Template",
#         output_subdir="actual",
#         filename_prefix="ACT",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     # find_template will return None

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     ["new-doc", "NonExistentType", "test-id", "--project-root", str(tmp_path)],
#     # )
#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # assert "Template 'NonExistentType' not found." in result.stderr
#     # assert (
#     #     "Available doc_types: Actual" in result.stderr
#     # )  # Check if suggestions are present
#     pass # Test commented out


# def test_cli_new_doc_template_not_found_error_json_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI JSON error when template is not found, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mocker.patch("khive.cli.khive_new_doc.discover_templates", return_value=[])

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "NonExistentType",
#     #         "test-id",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--json-output",
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # json_output = json.loads(result.stdout)
#     # assert json_output["status"] == "failure"  # die_doc uses "failure"
#     # assert "No templates found. Cannot create document." in json_output["message"]
#     pass # Test commented out


# def test_cli_new_doc_dest_not_writable_error_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI error when destination is not writable, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )

#     # Mock Path.mkdir to simulate PermissionError
#     mocker.patch(
#         "pathlib.Path.mkdir", side_effect=PermissionError("Test permission denied")
#     )

#     non_writable_dest_base = tmp_path / "locked_reports"
#     # We don't actually create non_writable_dest_base, mkdir mock will handle it

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "IP",
#     #         "testperm",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--dest",
#     #         str(non_writable_dest_base),
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # assert "Permission denied: Cannot create directory or write file" in result.stderr
#     # assert "Test permission denied" in result.stderr
#     pass # Test commented out


# def test_cli_new_doc_dest_not_writable_error_json_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI JSON error when destination is not writable, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )
#     mocker.patch(
#         "pathlib.Path.mkdir", side_effect=PermissionError("Test permission denied JSON")
#     )

#     non_writable_dest_base = tmp_path / "locked_reports_json"

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "IP",
#     #         "testpermjson",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--dest",
#     #         str(non_writable_dest_base),
#     #         "--json-output",
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # json_output = json.loads(result.stdout)
#     # assert json_output["status"] == "error"
#     # assert (
#     #     "Permission denied: Cannot create directory or write file"
#     #     in json_output["message"]
#     # )
#     # assert "Test permission denied JSON" in json_output["message"]
#     pass # Test commented out


# def test_cli_new_doc_path_conflict_error_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI error when a path component is a file, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )

#     # Create a file where a directory is expected
#     conflict_base = tmp_path / "reports_is_a_file.txt"
#     conflict_base.write_text("I am a file, not a directory.")

#     # Attempt to create a doc where 'reports_is_a_file.txt' would be a parent dir
#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "IP",
#     #         "testconflict",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--dest",
#     #         str(conflict_base),
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # assert (
#     #     "Path conflict: A component of the destination path" in result.stderr
#     #     or "Invalid path: A component of the base destination path" in result.stderr
#     # )  # Depending on where error is caught
#     # assert (
#     #     str(conflict_base / "ip") in result.stderr
#     #     or str(conflict_base) in result.stderr
#     # )
#     pass # Test commented out


# def test_cli_new_doc_path_conflict_error_json_cli_runner(tmp_path, mocker):
#     \"\"\"Test CLI JSON error when a path component is a file, using CliRunner.\"\"\"
#     runner = CliRunner()
#     mock_template_instance = Template(
#         path=Path("dummy_template.md"),
#         doc_type="IP",
#         title="Dummy Template",
#         output_subdir="ip",
#         filename_prefix="IP",
#         meta={},
#         body_template="content",
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.discover_templates",
#         return_value=[mock_template_instance],
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.find_template", return_value=mock_template_instance
#     )
#     mocker.patch(
#         "khive.cli.khive_new_doc.substitute_placeholders",
#         return_value="rendered_content",
#     )

#     conflict_base = tmp_path / "reports_is_a_file_json.txt"
#     conflict_base.write_text("I am a file, not a directory.")

#     # result = runner.invoke(
#     #     khive_cli_group,
#     #     [
#     #         "new-doc",
#     #         "IP",
#     #         "testconflictjson",
#     #         "--project-root",
#     #         str(tmp_path),
#     #         "--dest",
#     #         str(conflict_base),
#     #         "--json-output",
#     #     ],
#     # )

#     # assert result.exit_code != 0, f"Output: {result.output}"
#     # json_output = json.loads(result.stdout)
#     # assert json_output["status"] == "error"
#     # assert (
#     #     "Path conflict: A component of the destination path" in json_output["message"]
#     #     or "Invalid path: A component of the base destination path"
#     #     in json_output["message"]
#     # )
#     # assert (
#     #     str(conflict_base / "ip") in json_output["message"]
#     #     or str(conflict_base) in json_output["message"]
#     # )
#     pass # Test commented out
"""

"""
Tests for khive_new_doc.py
"""

import argparse
import datetime as dt
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
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
    assert result["status"] == "failure"
    assert "File already exists" in result["message"]
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

    # Mock die_doc to avoid SystemExit
    mock_die_doc.side_effect = lambda msg, *args, **kwargs: None

    # Act
    main()

    # Assert
    mock_die_doc.assert_called_once()
    assert "Template 'NONEXISTENT' not found" in mock_die_doc.call_args[0][0]

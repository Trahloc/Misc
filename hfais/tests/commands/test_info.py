import pytest
from click.testing import CliRunner
from hfais.commands.info import command

def test_info():
    """Test the info command."""
    runner = CliRunner()

    # Test basic info
    result = runner.invoke(command, [], obj={'verbose': 0})
    assert result.exit_code == 0
    assert "Project: hfais" in result.output

    # Test verbose info
    result = runner.invoke(command, [], obj={'verbose': 1})
    assert result.exit_code == 0
    assert "Description:" in result.output
    assert "Created using the Zeroth Law AI Framework" in result.output
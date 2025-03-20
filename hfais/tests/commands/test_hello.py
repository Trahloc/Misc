import pytest
from click.testing import CliRunner
from hfais.commands.hello import command

def test_hello():
    """Test the hello command."""
    runner = CliRunner()

    # Test the hello command with informal greeting
    result = runner.invoke(command, ["Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output

    # Test the hello command with formal greeting
    result = runner.invoke(command, ["Bob", "--formal"])
    assert result.exit_code == 0
    assert "Greetings, Bob!" in result.output
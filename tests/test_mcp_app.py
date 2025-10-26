from unittest.mock import patch

from seev.mcp_app import run


def test_run_with_http_transport():
    """Test run function with HTTP transport arguments."""
    with patch("glin.mcp_app.mcp") as mock_mcp:
        run(["script.py", "--transport", "http"])
        mock_mcp.run.assert_called_once_with(transport="http", port=8000)


def test_run_with_default_transport():
    """Test run function with default transport (no HTTP args)."""
    with patch("glin.mcp_app.mcp") as mock_mcp:
        run(["script.py"])
        mock_mcp.run.assert_called_once_with()


def test_run_with_transport_but_not_http():
    """Test run function with transport arg but not http."""
    with patch("glin.mcp_app.mcp") as mock_mcp:
        run(["script.py", "--transport", "stdio"])
        mock_mcp.run.assert_called_once_with()


def test_run_with_http_but_no_transport():
    """Test run function with http arg but no transport."""
    with patch("glin.mcp_app.mcp") as mock_mcp:
        run(["script.py", "http"])
        mock_mcp.run.assert_called_once_with()


def test_run_with_none_argv():
    """Test run function with None argv (uses sys.argv)."""
    with patch("glin.mcp_app.mcp") as mock_mcp, patch("glin.mcp_app.sys") as mock_sys:
        mock_sys.argv = ["script.py", "--transport", "http"]
        run(None)
        mock_mcp.run.assert_called_once_with(transport="http", port=8000)


def test_run_with_none_argv_default():
    """Test run function with None argv using default transport."""
    with patch("glin.mcp_app.mcp") as mock_mcp, patch("glin.mcp_app.sys") as mock_sys:
        mock_sys.argv = ["script.py"]
        run(None)
        mock_mcp.run.assert_called_once_with()

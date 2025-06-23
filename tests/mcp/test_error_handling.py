from pythonium.mcp.utils.error_handling import ErrorHandler, ErrorContext


def test_handle_file_not_found_error():
    handler = ErrorHandler()
    result = handler.handle_error(FileNotFoundError("nope.txt"), ErrorContext(tool_name="x"))
    assert "File not found" in result[0].text
    assert "nope.txt" in result[0].text


def test_handle_value_error_required():
    handler = ErrorHandler()
    result = handler.handle_error(ValueError("path required"), ErrorContext())
    assert "Missing required parameter" in result[0].text


def test_handle_value_error_generic():
    handler = ErrorHandler()
    result = handler.handle_error(ValueError("bad input"), ErrorContext())
    assert "Invalid input" in result[0].text

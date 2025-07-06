import inspect
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pythonium.common.config import TransportType
from pythonium.core.server import PythoniumMCPServer
from pythonium.tools.base import BaseTool, ParameterType, ToolMetadata, ToolParameter


class DummyTool(BaseTool):
    @property
    def metadata(self):
        return ToolMetadata(
            name="dummy",
            description="dummy",
            category="test",
            parameters=[
                ToolParameter(
                    name="x", type=ParameterType.INTEGER, description="x", required=True
                ),
                ToolParameter(
                    name="y",
                    type=ParameterType.STRING,
                    description="y",
                    required=False,
                    default="d",
                ),
            ],
        )

    async def execute(self, params, context):
        from pythonium.common.base import Result

        return Result.success_result({"sum": params["x"], "y": params.get("y")})


@pytest.mark.asyncio
async def test_dynamic_tool_function():
    server = PythoniumMCPServer()
    func = server._create_dynamic_tool_function(DummyTool())
    sig = inspect.signature(func)
    assert list(sig.parameters.keys()) == ["x", "y"]
    result = await func(1, "ok")
    assert result == {"sum": 1, "y": "ok"}


def test_map_parameter_type():
    server = PythoniumMCPServer()
    mapping = {
        ParameterType.STRING: str,
        ParameterType.INTEGER: int,
        ParameterType.NUMBER: float,
        ParameterType.BOOLEAN: bool,
        ParameterType.ARRAY: list,
        ParameterType.OBJECT: dict,
        ParameterType.PATH: str,
        ParameterType.URL: str,
        ParameterType.EMAIL: str,
    }
    for pt, expected in mapping.items():
        assert server._map_parameter_type(pt) == expected


@pytest.mark.asyncio
async def test_run_http_and_ws():
    server = PythoniumMCPServer(config_overrides={"server": {"transport": "http"}})
    server.start = AsyncMock()
    server.stop = AsyncMock()
    server.mcp_server.run = Mock()

    async def mock_run_in_executor(_executor, func, *args):
        func(*args)

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = mock_run_in_executor
        await server.run()
        server.mcp_server.run.assert_called_with(transport="streamable-http")

    server.config.server.transport = TransportType.WEBSOCKET
    server.mcp_server.run.reset_mock()
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = mock_run_in_executor
        await server.run()
        server.mcp_server.run.assert_called_with(transport="sse")


@pytest.mark.asyncio
async def test_start_stop_idempotent_and_signal_handler():
    server = PythoniumMCPServer()
    server.config_manager.validate_config = lambda: []
    server._discover_and_register_tools = AsyncMock()
    server._setup_signal_handlers = Mock()
    await server.start()
    await server.start()  # should be no-op when already running
    await server.stop()
    await server.stop()  # stop when not running
    with patch("asyncio.create_task") as mock_task:
        server._running = True
        server._signal_handler(signal.SIGTERM, None)
        mock_task.assert_called()

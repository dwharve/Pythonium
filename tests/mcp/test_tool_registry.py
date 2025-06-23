import asyncio
import mcp.types as types
from pythonium.mcp.core.tool_registry import ToolRegistry


def test_tool_registry_register_execute_unregister():
    registry = ToolRegistry()
    schema = types.Tool(name='hello', description='greet', inputSchema={})

    async def handler(args):
        return [types.TextContent(type='text', text=f"hi {args.get('name','')}" )]

    registry.register('hello', handler, schema, category='greet')
    assert registry.is_registered('hello')

    result = asyncio.run(registry.execute_tool('hello', {'name': 'Alice'}))
    assert result[0].text == 'hi Alice'

    # error path
    async def bad(args):
        raise RuntimeError('boom')
    registry.register('bad', bad, schema)
    result = asyncio.run(registry.execute_tool('bad', {}))
    assert 'Error executing tool' in result[0].text

    info = registry.get_registry_info()
    assert info['total_tools'] == 2
    assert 'hello' in info['tools']

    assert registry.unregister('hello')
    assert not registry.is_registered('hello')
    assert not registry.unregister('missing')


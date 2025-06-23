import asyncio
import mcp.types as types
from pythonium.mcp.core.middleware import Middleware, MiddlewareChain


class DummyMiddleware(Middleware):
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    async def process(self, tool_name, arguments, next_handler):
        self.calls.append(f"before-{self.name}")
        result = await next_handler(tool_name, arguments)
        self.calls.append(f"after-{self.name}")
        return result


def test_middleware_chain_add_remove_clear_execution():
    calls = []
    chain = MiddlewareChain()
    m1 = DummyMiddleware('m1', calls)
    m2 = DummyMiddleware('m2', calls)
    chain.add(m1).add(m2)

    async def final(name, args):
        calls.append('final')
        return [types.TextContent(type='text', text='done')]

    result = asyncio.run(chain.process('tool', {}, final))
    assert result[0].text == 'done'
    assert calls == ['before-m1', 'before-m2', 'final', 'after-m2', 'after-m1']

    assert chain.remove(DummyMiddleware)  # removes first occurrence
    assert len(chain.get_middleware_info()) == 1
    chain.clear()
    assert chain.get_middleware_info() == []


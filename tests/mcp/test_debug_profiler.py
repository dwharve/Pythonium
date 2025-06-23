import asyncio
from pythonium.mcp.utils import debug
from pythonium.mcp.utils.debug import OperationProfiler, profile_operation, setup_minimal_logging, setup_debug_logging


def test_operation_profiler_basic(tmp_path):
    setup_minimal_logging()
    profiler = OperationProfiler()
    profiler.start_operation('op', foo=1)
    profiler.checkpoint('mid', step=2)
    profiler.end_operation(success=True, bar=3)
    report = profiler.get_report()
    assert 'Operation: op' in report
    assert 'Status: success' in report


def test_profile_operation_decorator_sync_and_async():
    setup_debug_logging()
    debug.profiler.operations.clear()

    @profile_operation('sync')
    def add(a, b):
        return a + b

    @profile_operation('async')
    async def add_async(a, b):
        return a + b

    assert add(2, 3) == 5
    asyncio.run(add_async(1, 4))
    names = [op['name'] for op in debug.profiler.operations]
    assert names == ['sync', 'async']
    for op in debug.profiler.operations:
        assert op['status'] == 'success'


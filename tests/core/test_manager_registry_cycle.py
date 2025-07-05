import pytest

from pythonium.core.managers import ManagerRegistry
from pythonium.managers import BaseManager


class StartStopManager(BaseManager):
    async def _initialize(self):
        pass

    async def _start(self):
        pass

    async def _stop(self):
        pass

    async def _cleanup(self):
        pass


@pytest.mark.asyncio
async def test_start_stop_cycle():
    registry = ManagerRegistry()
    registry.register_manager("a", StartStopManager)
    await registry.initialize_all()
    info = registry.get_manager_info()
    assert info["a"]["auto_start"] is True
    await registry.shutdown_all()
    assert registry._instances == {}

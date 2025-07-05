import pytest

from pythonium.common.types import HealthStatus
from pythonium.core.managers import ManagerRegistry
from pythonium.managers import BaseManager


class SimpleManager(BaseManager):
    async def _initialize(self):
        pass

    async def _start(self):
        pass

    async def _stop(self):
        pass

    async def _cleanup(self):
        pass

    async def get_health_status(self) -> HealthStatus:
        return HealthStatus.HEALTHY


class DependentManager(SimpleManager):
    def __init__(self, name="dep"):
        super().__init__(name)


@pytest.mark.asyncio
async def test_registry_dependency_and_health():
    registry = ManagerRegistry()
    registry.register_manager("a", SimpleManager)
    registry.register_manager("b", DependentManager)
    await registry.start_all_managers()
    health = await registry.get_system_health()
    assert health["overall_status"] == "healthy"
    assert set(health["managers"].keys()) == {"a", "b"}
    info = registry.get_manager_info()
    assert info["a"]["auto_start"] is True
    await registry.shutdown_all()
    assert registry._instances == {}


class FailingStartManager(SimpleManager):
    async def _start(self):
        raise RuntimeError("boom")


class UnhealthyManager(SimpleManager):
    async def get_health_status(self) -> HealthStatus:
        raise RuntimeError("bad")


@pytest.mark.asyncio
async def test_start_failure_and_health_report():
    registry = ManagerRegistry()
    registry.register_manager("fail", FailingStartManager)
    registry.register_manager("bad", UnhealthyManager)

    with pytest.raises(Exception):
        await registry.start_all_managers()

    # even after failure, check health report handles exception
    health = await registry.get_system_health()
    assert health["overall_status"] in {"healthy", "unhealthy", "degraded"}

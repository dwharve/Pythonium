import asyncio
import pytest

from pythonium.core import ManagerRegistry
from pythonium.core.managers import (
    register_manager,
    get_manager,
    get_manager_by_type,
    get_manager_registry,
)
from pythonium.managers import BaseManager
from pythonium.managers.base import ManagerDependency


class AManager(BaseManager):
    async def _initialize(self):
        pass

    async def _start(self):
        pass

    async def _stop(self):
        pass

    async def _cleanup(self):
        pass


class BManager(AManager):
    def __init__(self, name="b"):
        super().__init__(name)
        self.info.dependencies.append(ManagerDependency(AManager))

class BSimple(AManager):
    pass




@pytest.mark.asyncio
async def test_unregistration_and_global_helpers():
    registry = ManagerRegistry()
    registry.register_manager("a", AManager, tags={"alpha"})
    registry.register_manager("b", BManager, tags={"beta"})
    assert set(registry.list_registrations()) == {"a", "b"}
    assert registry.list_registrations(tags={"beta"}) == ["b"]
    registry.unregister_manager("b")
    assert not registry.is_registered("b")

    register_manager("global_a", AManager)
    mgr = await get_manager("global_a")
    assert isinstance(mgr, AManager)
    assert await get_manager_by_type(AManager) is mgr
    assert get_manager_registry().is_registered("global_a")


@pytest.mark.asyncio
async def test_circular_dependency_detection():
    registry = ManagerRegistry()
    class A(AManager):
        def __init__(self, name="a"):
            super().__init__(name)
            self.info.dependencies.append(ManagerDependency(B))
    class B(AManager):
        def __init__(self, name="b"):
            super().__init__(name)
            self.info.dependencies.append(ManagerDependency(A))
    registry.register_manager("a", A)
    registry.register_manager("b", B)
    with pytest.raises(Exception):
        await registry.start_all_managers()



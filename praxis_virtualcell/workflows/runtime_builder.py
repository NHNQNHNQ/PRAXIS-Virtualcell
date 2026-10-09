"""Explicit construction root for the generic direct-v2 execution seam."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import (
    Clock,
    IdGen,
    Mode,
    RuntimeConfig,
    assert_llm_boundaries,
)
from praxis_virtualcell.core.domain_extension import DomainExtension
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, require_v2_request
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import EnvironmentSnapshot
from praxis_virtualcell.model_zoo.post_result_policy import OutputReducerPolicyRegistry
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import (
    ComposedModelRegistryV2,
    EnvironmentIdentityV2,
    ModelRegistryV2,
)
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry


class DirectV2RuntimeFactory:
    """Build one direct-v2 runtime from explicitly supplied, generic contracts.

    This is intentionally a small composition root, not a plugin manager.  It
    neither discovers domain code nor substitutes default Pack, adapter, or
    wrapper dependencies when a caller has not supplied them.
    """

    def __init__(
        self,
        *,
        registry: ModelZooRegistry,
        cache: ModelCache,
        pack_registry: PackRegistry,
        environment: EnvironmentSnapshot,
        adapter_registry: AdapterRegistry,
        wrapper_registry: WrapperRegistry,
        output_reducer_registry: OutputReducerPolicyRegistry | None = None,
        domain_extensions: tuple[DomainExtension, ...] = (),
    ) -> None:
        if not isinstance(registry, ModelZooRegistry):
            raise TypeError("registry must be ModelZooRegistry")
        if not isinstance(registry.registry_v2, (ModelRegistryV2, ComposedModelRegistryV2)):
            raise ValueError("direct-v2 requires an explicit Model Registry v2 source")
        if not isinstance(cache, ModelCache):
            raise TypeError("cache must be ModelCache")
        if not isinstance(pack_registry, PackRegistry):
            raise TypeError("pack_registry must be PackRegistry")
        if not isinstance(environment, EnvironmentSnapshot):
            raise TypeError("environment must be EnvironmentSnapshot")
        if environment.schema_version != "vc.environment.v3" or type(environment.identity) is not EnvironmentIdentityV2:
            raise ValueError("direct-v2 requires an exact vc.environment.v3 EnvironmentIdentityV2")
        if not isinstance(adapter_registry, AdapterRegistry):
            raise TypeError("adapter_registry must be AdapterRegistry")
        if not isinstance(wrapper_registry, WrapperRegistry):
            raise TypeError("wrapper_registry must be WrapperRegistry")
        if output_reducer_registry is not None and not isinstance(
            output_reducer_registry,
            OutputReducerPolicyRegistry,
        ):
            raise TypeError("output_reducer_registry must be OutputReducerPolicyRegistry")
        if not isinstance(domain_extensions, tuple) or any(
            not isinstance(extension, DomainExtension) for extension in domain_extensions
        ):
            raise TypeError("domain_extensions must be a tuple of DomainExtension")
        self._registry = registry
        self._cache = cache
        self._pack_registry = pack_registry
        self._environment = environment
        self._adapter_registry = adapter_registry
        self._wrapper_registry = wrapper_registry
        self._output_reducer_registry = output_reducer_registry
        self._domain_extensions = domain_extensions
        # The factory deliberately reuses registries and adapter instances.
        # Every runtime it builds therefore shares this re-entrant execution
        # slot, preventing a stateful registered adapter from crossing jobs.
        self._execution_lock = threading.RLock()

    def _broker(self) -> ModelBrokerAgent:
        return ModelBrokerAgent(
            registry=self._registry,
            cache=self._cache,
            pack_registry=self._pack_registry,
            environment=self._environment,
            adapter_registry=self._adapter_registry,
            wrapper_registry=self._wrapper_registry,
            output_reducer_registry=self._output_reducer_registry,
        )

    def compatibility(
        self,
        request: VirtualCellRequestV2 | dict,
        pack_id: str,
        pack_version: str,
    ) -> dict:
        """Return the path-free direct-v2 plan without preparing or running it."""

        with self.compatibility_guard(request, pack_id, pack_version) as plan:
            return plan

    @contextmanager
    def compatibility_guard(
        self,
        request: VirtualCellRequestV2 | dict,
        pack_id: str,
        pack_version: str,
    ) -> Iterator[dict]:
        """Hold the factory execution slot from exact planning through a caller's run."""

        from praxis_virtualcell.pack_product import _public_plan

        validated = request if isinstance(request, VirtualCellRequestV2) else require_v2_request(request)
        if not all(isinstance(value, str) and value and value.strip() == value for value in (pack_id, pack_version)):
            raise ValueError("pack_id and pack_version must be non-empty trimmed strings")
        with self._execution_lock:
            plan = self._broker().plan(
                validated,
                self._pack_registry.record(pack_id, pack_version),
                require_registered_wrapper=True,
            )
            yield _public_plan(plan.to_dict())

    def build(
        self,
        *,
        config: RuntimeConfig | None = None,
        clock: Clock | None = None,
        idgen: IdGen | None = None,
    ) -> AgentRuntime:
        config = RuntimeConfig() if config is None else config
        if not isinstance(config, RuntimeConfig):
            raise TypeError("config must be RuntimeConfig")
        if config.mode != Mode.OFFLINE or config.llm_enabled:
            raise ValueError("direct-v2 runtime requires offline configuration")
        assert_llm_boundaries(config)
        if clock is not None and not isinstance(clock, Clock):
            raise TypeError("clock must be Clock")
        if idgen is not None and not isinstance(idgen, IdGen):
            raise TypeError("idgen must be IdGen")

        runtime = AgentRuntime(
            config,
            bus=MessageBus(),
            clock=clock or Clock(),
            idgen=idgen or IdGen(),
            domain_extensions=self._domain_extensions,
            execution_lock=self._execution_lock,
        )
        runtime.register_agent(self._broker())
        return runtime

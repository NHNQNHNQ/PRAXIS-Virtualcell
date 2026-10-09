"""Explicit, generic construction of the direct-v2 runtime."""

from __future__ import annotations

import threading

import pytest

import praxis_virtualcell.model_zoo.cache as cache_module
from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _pack_registry,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.tests.test_direct_v2_single_model import (
    _MODEL_NAME,
    _pack_bound_request,
    _ScalarAdapter,
    _ScalarWrapper,
)
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory


def test_factory_rejects_legacy_v2_environment_identity(tmp_path) -> None:
    card = _card()
    registry_v2, environment = _v2_registry_and_environment(card, "0" * 64)
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)

    with pytest.raises(ValueError, match="vc.environment.v3"):
        DirectV2RuntimeFactory(
            registry=zoo,
            cache=ModelCache(root=str(tmp_path / "cache")),
            pack_registry=_pack_registry(),
            environment=environment,
            adapter_registry=AdapterRegistry(),
            wrapper_registry=WrapperRegistry(),
        )


def test_raw_direct_v2_v2_environment_hard_abstains_before_snapshot_or_wrapper(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bypass of the factory still cannot execute without a v3 budget."""

    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _ScalarAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    # Exercise the raw public runtime seam without allowing the factory
    # constructor itself to reject the old environment first.
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.config import Clock, IdGen
    from praxis_virtualcell.core.runtime import AgentRuntime

    direct = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    direct.register_agent(
        ModelBrokerAgent(
            registry=zoo,
            cache=cache,
            pack_registry=packs,
            environment=environment,
            adapter_registry=AdapterRegistry([adapter]),
            wrapper_registry=wrappers,
        )
    )

    def forbidden_read(*_args, **_kwargs):
        raise AssertionError("v2 environment must stop before artifact snapshot reads")

    monkeypatch.setattr(cache_module.os, "read", forbidden_read)
    report = direct.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert "artifact.snapshot_budget_unavailable" in report["abstain_reasons"]


def test_factory_builds_only_an_explicit_generic_direct_v2_stack(tmp_path) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _ScalarAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)

    runtime = DirectV2RuntimeFactory(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    ).build(clock=Clock(), idgen=IdGen())

    assert set(runtime._agents) == {ModelBrokerAgent.name}
    result = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )
    assert result["abstain"] is False
    assert result["prediction"]["output"] == "test_output"

    missing_wrapper = DirectV2RuntimeFactory(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=WrapperRegistry(),
    ).build()
    abstained = missing_wrapper.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )
    assert abstained["abstain"] is True
    assert abstained["prediction"] is None


def test_factory_rejects_non_offline_configuration(tmp_path) -> None:
    from praxis_virtualcell.core.config import Mode
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

    factory = DirectV2RuntimeFactory(
        registry=ModelZooRegistry(),
        cache=ModelCache(root=str(tmp_path / "cache")),
        pack_registry=_pack_registry(),
        environment=_v2_registry_and_environment(
            _card(),
            "0" * 64,
            snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
        )[1],
        adapter_registry=AdapterRegistry(),
        wrapper_registry=WrapperRegistry(),
    )

    try:
        factory.build(
            config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True),
        )
    except ValueError as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("direct-v2 must not construct an LLM-enabled runtime")


def test_factory_serializes_shared_adapter_instances_across_built_runtimes(
    tmp_path,
    monkeypatch,
) -> None:
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _ScalarAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    factory = DirectV2RuntimeFactory(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
    )
    first_runtime = factory.build()
    second_runtime = factory.build()
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    counter_lock = threading.Lock()
    calls = 0
    original_prepare = adapter.prepare_input

    def serial_probe(*args, **kwargs):
        nonlocal calls
        with counter_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            first_entered.set()
            assert release_first.wait(timeout=2)
        else:
            second_entered.set()
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(adapter, "prepare_input", serial_probe)
    reports: list[dict] = []
    errors: list[BaseException] = []

    def execute(runtime) -> None:
        try:
            reports.append(
                runtime.run_workflow_v2(
                    request,
                    pack_id="tiny-human-scrna",
                    pack_version="0.1.0",
                )
            )
        except BaseException as exc:  # noqa: BLE001 - asserted after workers join
            errors.append(exc)

    first = threading.Thread(target=execute, args=(first_runtime,))
    second = threading.Thread(target=execute, args=(second_runtime,))
    first.start()
    assert first_entered.wait(timeout=2)
    second.start()
    assert not second_entered.wait(timeout=0.2)
    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(reports) == 2
    assert all(report["abstain"] is False for report in reports)

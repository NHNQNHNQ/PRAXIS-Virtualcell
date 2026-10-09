"""Explicit direct-v2 wrapper registration without runtime discovery."""

from __future__ import annotations

import re

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper

_ENTRYPOINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)


class WrapperConflictError(ValueError):
    """Two wrapper classes claimed one public entrypoint."""


class WrapperNotFoundError(LookupError):
    """No wrapper was explicitly registered for the requested entrypoint."""


class WrapperRegistry:
    """Resolve one exact registered wrapper class; never import or discover it."""

    def __init__(self) -> None:
        self._wrappers: dict[str, type[ModelWrapper]] = {}

    @staticmethod
    def _entrypoint(value: str) -> str:
        if not isinstance(value, str) or not _ENTRYPOINT.fullmatch(value):
            raise ValueError("wrapper entrypoint must be a fully-qualified class path")
        return value

    def register(self, entrypoint: str, wrapper_class) -> None:
        entrypoint = self._entrypoint(entrypoint)
        if not isinstance(wrapper_class, type) or not issubclass(
            wrapper_class,
            ModelWrapper,
        ):
            raise TypeError("wrapper class must be a ModelWrapper subclass")
        class_entrypoint = (
            f"{wrapper_class.__module__}.{wrapper_class.__qualname__}"
        )
        if class_entrypoint != entrypoint:
            raise ValueError("wrapper entrypoint must exactly match the registered class")
        existing = self._wrappers.get(entrypoint)
        if existing is not None and existing is not wrapper_class:
            raise WrapperConflictError(f"wrapper entrypoint conflict: {entrypoint}")
        self._wrappers[entrypoint] = wrapper_class

    def resolve(self, entrypoint: str) -> type[ModelWrapper]:
        entrypoint = self._entrypoint(entrypoint)
        try:
            return self._wrappers[entrypoint]
        except KeyError as exc:
            raise WrapperNotFoundError(
                f"wrapper entrypoint is not registered: {entrypoint}"
            ) from exc

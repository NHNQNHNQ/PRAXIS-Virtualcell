"""Standalone VirtualCell execution exceptions."""
from __future__ import annotations


class PraxisVCError(Exception):
    """Base exception for the package."""


class InputValidationError(PraxisVCError):
    """VirtualCellRequest parsing or validation failure."""


class RetrieveBeforePredictError(PraxisVCError):
    """Prediction attempted before brain retrieval, violating the retrieve-before-predict gate."""


class UnknownAgentError(PraxisVCError):
    """Dispatch targets an unregistered agent."""


class SchemaError(PraxisVCError):
    """Message/handoff schema violation: missing fields, nondictionary payload, or free-text handoff."""


class UnsupportedEngine(PraxisVCError):
    """No real case runner supports the requested engine/species/perturbation combination."""

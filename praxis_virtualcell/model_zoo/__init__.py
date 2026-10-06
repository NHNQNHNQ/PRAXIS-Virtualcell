"""Strict model cards, capability planning, wrappers, and hash-locked local assets.

Pack-aware execution is driven by CapabilityRegistry and ModelBrokerAgent. Missing
scope, assets, dependencies, resources, or runtime adapters fail closed; no model
download or mock fallback occurs here.
"""

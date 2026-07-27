"""VirtualCellPack validation errors."""


class VirtualCellPackError(ValueError):
    """Base error for deterministic Pack contract failures."""


class PackManifestError(VirtualCellPackError):
    """The manifest cannot be parsed or violates its schema."""


class PackPathError(VirtualCellPackError):
    """A declared asset path is unsafe or escapes the Pack root."""


class PackAssetMissing(VirtualCellPackError):
    """A declared asset does not exist as a regular file."""


class PackAssetSizeMismatch(VirtualCellPackError):
    """A declared asset size does not match the file."""


class PackAssetHashMismatch(VirtualCellPackError):
    """A declared asset hash does not match the file."""


class PackRegistryError(VirtualCellPackError):
    """A Pack cannot be registered or retrieved."""


class OmicsAdapterError(VirtualCellPackError):
    """Base error for optional omics adapter failures."""


class OmicsDependencyError(OmicsAdapterError):
    """The optional omics dependency is unavailable."""


class OmicsMappingError(OmicsAdapterError):
    """Manifest mappings do not identify required AnnData fields."""


class OmicsDataError(OmicsAdapterError):
    """AnnData content violates the declared immutable data contract."""


class FeatureAlignmentError(OmicsAdapterError):
    """Feature alignment cannot satisfy an explicit model contract."""

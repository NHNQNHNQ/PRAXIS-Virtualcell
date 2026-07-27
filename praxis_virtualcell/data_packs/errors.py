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

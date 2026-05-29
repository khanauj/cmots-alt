"""Typed exceptions for the pipeline."""


class CmotsAltError(Exception):
    """Base."""


class FetchError(CmotsAltError):
    """Raised when a source fetch fails after retries."""


class ParseError(CmotsAltError):
    """Raised when raw payload cannot be parsed."""


class ValidationError(CmotsAltError):
    """Raised when validated dataframe violates schema or business rules."""


class ResolverError(CmotsAltError):
    """Raised when identifier resolution fails."""

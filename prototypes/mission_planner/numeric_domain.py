"""Finite binary64 domain checks, independent of UI, search and resource formulas."""
import math


class NumericDomainError(ValueError):
    """Finite inputs produced arithmetic outside the supported numeric domain."""


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def require_number(value, name, *, minimum=None, positive=False):
    if (not finite_number(value) or (minimum is not None and value < minimum)
            or (positive and value <= 0)):
        raise ValueError(f"{name}: numero finito en el dominio requerido, sin bool")


def finite_result(value, name):
    if not finite_number(value):
        raise NumericDomainError(f"{name}: operacion fuera del dominio numerico finito")
    return value

"""basic math nodes"""

import math
import sys
from typing import List
from funcnodes.nodemaker import NodeDecorator
from funcnodes.lib import module_to_shelf


# region: Basic math nodes
@NodeDecorator(
    "value_node",
    inputs=[{"name": "value", "allow_multiple": True}],
)
def value_node(value: float) -> float:
    return value


@NodeDecorator(
    "add_node",
    name="Add",
)
def add_node(a: float, b: float) -> float:
    """Add two numbers"""
    a = float(a)
    b = float(b)
    return a + b


@NodeDecorator(
    "sub_node",
)
def sub_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a - b


@NodeDecorator(
    "mul_node",
)
def mul_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a * b


@NodeDecorator(
    "div_node",
)
def div_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a / b


@NodeDecorator(
    "mod_node",
)
def mod_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a % b


@NodeDecorator(
    "pow_node",
)
def pow_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a**b


@NodeDecorator(
    "floor_div_node",
)
def floor_div_node(a: float, b: float) -> float:
    a = float(a)
    b = float(b)
    return a // b


@NodeDecorator(
    "abs_node",
)
def abs_node(a: float) -> float:
    a = float(a)
    return abs(a)


@NodeDecorator(
    "neg_node",
)
def neg_node(a: float) -> float:
    a = float(a)
    return -a


@NodeDecorator(
    "pos_node",
)
def pos_node(a: float) -> float:
    a = float(a)
    return +a


@NodeDecorator(
    "round_node",
)
def round_node(a: float, ndigits: int = 0) -> float:
    a = float(a)
    ndigits = int(ndigits)
    return round(a, ndigits)


@NodeDecorator(
    "greater_node",
)
def greater_node(a: float, b: float) -> bool:
    a = float(a)
    b = float(b)
    return a > b


@NodeDecorator(
    "greater_equal_node",
)
def greater_equal_node(a: float, b: float) -> bool:
    a = float(a)
    b = float(b)
    return a >= b


@NodeDecorator(
    "less_node",
)
def less_node(a: float, b: float) -> bool:
    a = float(a)
    b = float(b)
    return a < b


@NodeDecorator(
    "less_equal_node",
)
def less_equal_node(a: float, b: float) -> bool:
    return a <= b


@NodeDecorator(
    "equal_node",
)
def equal_node(a: float, b: float) -> bool:
    a = float(a)
    b = float(b)
    return a == b


@NodeDecorator(
    "not_equal_node",
)
def not_equal_node(a: float, b: float) -> bool:
    a = float(a)
    b = float(b)
    return a != b


@NodeDecorator(
    "and_node",
)
def and_node(a: bool, b: bool) -> bool:
    a = float(a)
    b = float(b)
    return a and b


@NodeDecorator(
    "or_node",
)
def or_node(a: bool, b: bool) -> bool:
    a = bool(a)
    b = bool(b)
    return a or b


@NodeDecorator(
    "xor_node",
)
def xor_node(a: bool, b: bool) -> bool:
    a = bool(a)
    b = bool(b)
    return a ^ b


@NodeDecorator(
    "not_node",
)
def not_node(a: bool) -> bool:
    a = bool(a)
    return not a


# endregion basic math nodes


# region constants
@NodeDecorator(
    "math.pi",
)
def math_pi_node() -> float:
    return math.pi


@NodeDecorator(
    "math.e",
)
def math_e_node() -> float:
    return math.e


@NodeDecorator(
    "math.tau",
)
def math_tau_node() -> float:
    return math.tau


@NodeDecorator(
    "math.inf",
)
def math_inf_node() -> float:
    return math.inf


@NodeDecorator(
    "math.nan",
)
def math_nan_node() -> float:
    return math.nan


# endregion constants


# region 1 float in, 1 float out
@NodeDecorator(
    "math.acos",
    name="Acos",
)
def math_acos_node(a: float) -> float:
    """Return the arc cosine of a."""
    return math.acos(a)


@NodeDecorator(
    "math.acosh",
)
def math_acosh_node(a: float) -> float:
    return math.acosh(a)


@NodeDecorator(
    "math.asin",
)
def math_asin_node(a: float) -> float:
    return math.asin(a)


@NodeDecorator(
    "math.asinh",
)
def math_asinh_node(a: float) -> float:
    return math.asinh(a)


@NodeDecorator(
    "math.atan",
)
def math_atan_node(a: float) -> float:
    return math.atan(a)


@NodeDecorator(
    "math.atanh",
)
def math_atanh_node(a: float) -> float:
    return math.atanh(a)


@NodeDecorator(
    "math.ceil",
)
def math_ceil_node(a: float) -> float:
    return math.ceil(a)


@NodeDecorator(
    "math.cos",
)
def math_cos_node(a: float) -> float:
    return math.cos(a)


@NodeDecorator(
    "math.cosh",
)
def math_cosh_node(a: float) -> float:
    return math.cosh(a)


@NodeDecorator(
    "math.degrees",
)
def math_degrees_node(a: float) -> float:
    return math.degrees(a)


@NodeDecorator(
    "math.erf",
)
def math_erf_node(a: float) -> float:
    return math.erf(a)


@NodeDecorator(
    "math.erfc",
)
def math_erfc_node(a: float) -> float:
    return math.erfc(a)


@NodeDecorator(
    "math.exp",
)
def math_exp_node(a: float) -> float:
    return math.exp(a)


@NodeDecorator(
    "math.expm1",
)
def math_expm1_node(a: float) -> float:
    return math.expm1(a)


@NodeDecorator(
    "math.fabs",
)
def math_fabs_node(a: float) -> float:
    return math.fabs(a)


@NodeDecorator(
    "math.floor",
)
def math_floor_node(a: float) -> float:
    return math.floor(a)


@NodeDecorator(
    "math.gamma",
)
def math_gamma_node(a: float) -> float:
    return math.gamma(a)


@NodeDecorator(
    "math.lgamma",
)
def math_lgamma_node(a: float) -> float:
    return math.lgamma(a)


@NodeDecorator(
    "math.log",
)
def math_log_node(a: float) -> float:
    return math.log(a)


@NodeDecorator(
    "math.log10",
)
def math_log10_node(a: float) -> float:
    return math.log10(a)


@NodeDecorator(
    "math.log1p",
)
def math_log1p_node(a: float) -> float:
    return math.log1p(a)


@NodeDecorator(
    "math.log2",
)
def math_log2_node(a: float) -> float:
    return math.log2(a)


@NodeDecorator(
    "math.modf",
)
def math_modf_node(a: float) -> float:
    return math.modf(a)


@NodeDecorator(
    "math.radians",
)
def math_radians_node(a: float) -> float:
    return math.radians(a)


@NodeDecorator(
    "math.sin",
)
def math_sin_node(a: float) -> float:
    return math.sin(a)


@NodeDecorator(
    "math.sinh",
)
def math_sinh_node(a: float) -> float:
    return math.sinh(a)


@NodeDecorator(
    "math.sqrt",
)
def math_sqrt_node(a: float) -> float:
    return math.sqrt(a)


@NodeDecorator(
    "math.tan",
)
def math_tan_node(a: float) -> float:
    return math.tan(a)


@NodeDecorator(
    "math.tanh",
)
def math_tanh_node(a: float) -> float:
    return math.tanh(a)


if sys.version_info >= (3, 11):

    @NodeDecorator(
        "math.exp2",
    )
    def math_exp2_node(a: float) -> float:
        return math.exp2(a)

    @NodeDecorator(
        "math.cbrt",
    )
    def math_cbrt_node(a: float) -> float:
        return math.cbrt(a)


# endregion 1 float in, 1 float out


# region 1 float in, 1 bool out
@NodeDecorator(
    "math.isfinite",
)
def math_isfinite_node(a: float) -> bool:
    return math.isfinite(a)


@NodeDecorator(
    "math.isinf",
)
def math_isinf_node(a: float) -> bool:
    return math.isinf(a)


@NodeDecorator(
    "math.isnan",
)
def math_isnan_node(a: float) -> bool:
    return math.isnan(a)


# endregion 1 float in, 1 bool out


# region 1 float in, 1 int out
@NodeDecorator(
    "math.trunc",
)
def math_trunc_node(a: float) -> int:
    return math.trunc(a)


# endregion 1 float in, 1 int out


# region 2 float in, 1 float out
@NodeDecorator(
    "math.atan2",
)
def math_atan2_node(a: float, b: float) -> float:
    return math.atan2(a, b)


@NodeDecorator(
    "math.copysign",
)
def math_copysign_node(a: float, b: float) -> float:
    return math.copysign(a, b)


@NodeDecorator(
    "math.fmod",
)
def math_fmod_node(a: float, b: float) -> float:
    return math.fmod(a, b)


@NodeDecorator(
    "math.hypot",
)
def math_hypot_node(a: float, b: float) -> float:
    return math.hypot(a, b)


@NodeDecorator(
    "math.pow",
)
def math_pow_node(a: float, b: float) -> float:
    return math.pow(a, b)


@NodeDecorator(
    "math.remainder",
)
def math_remainder_node(a: float, b: float) -> float:
    return math.remainder(a, b)


if sys.version_info >= (3, 9):

    @NodeDecorator(
        "math.nextafter",
    )
    def math_nextafter_node(a: float, b: float) -> float:
        return math.nextafter(a, b)


# endregion 2 float in, 1 float out


# region 2 float in, 1 bool out
@NodeDecorator(
    "math.isclose",
)
def math_isclose_node(a: float, b: float) -> bool:
    return math.isclose(a, b)


# endregion 2 float in, 1 bool out


# region 2 float in, 1 int out
# endregion 2 float in, 1 int out

# region 1 int in, 1 int out


@NodeDecorator(
    "math.factorial",
)
def math_factorial_node(a: int) -> int:
    return math.factorial(a)


if sys.version_info >= (3, 8):

    @NodeDecorator(
        "math.isqrt",
    )
    def math_isqrt_node(a: int) -> int:
        return math.isqrt(a)


# endregion 1 int in, 1 int out


# region 2 int in, 1 int out
@NodeDecorator(
    "math.gcd",
)
def math_gcd_node(a: int, b: int) -> int:
    return math.gcd(a, b)


if sys.version_info >= (3, 8):

    @NodeDecorator(
        "math.comb",
    )
    def math_comb_node(a: int, b: int) -> int:
        return math.comb(a, b)

    @NodeDecorator(
        "math.perm",
    )
    def math_perm_node(a: int, b: int) -> int:
        return math.perm(a, b)


if sys.version_info >= (3, 9):

    @NodeDecorator(
        "math.lcm",
    )
    def math_lcm_node(a: int, b: int) -> int:
        return math.lcm(a, b)


# endregion 2 int in, 1 int out


# region float, int in float out
@NodeDecorator(
    "math.ldexp",
)
def math_ldexp_node(a: float, b: int) -> float:
    return math.ldexp(a, b)


# endregion float, int in float out


# region vector in float out
@NodeDecorator(
    "math.fsum",
)
def math_fsum_node(a: List[float]) -> float:
    return math.fsum(a)


if sys.version_info >= (3, 8):

    @NodeDecorator(
        "math.prod",
    )
    def math_prod_node(a: List[float]) -> float:
        return math.prod(a)


# endregion vector in float out

# region vector, vector in float out

if sys.version_info >= (3, 8):

    @NodeDecorator(
        "math.dist",
    )
    def math_dist_node(a: List[float], b: List[float]) -> float:
        return math.dist(a, b)


if sys.version_info >= (3, 12):

    @NodeDecorator(
        "math.sumprod",
    )
    def math_sumprod_node(a: List[float], b: List[float]) -> float:
        return math.sumprod(a, b)


# endregion vector, vector in float out

NODE_SHELF = module_to_shelf(sys.modules[__name__], name="math")

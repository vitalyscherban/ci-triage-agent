"""A large bank of fast, trivial passing tests.

Real CI suites for anything beyond a toy service run thousands of tests. This
file exists to make the sample log CI-scale (thousands of PASSED lines around
a handful of real failures) so the pruning technique's benefit is visible on
a genuinely large, genuinely-executed pytest run - not just illustrative.
"""

import pytest


@pytest.mark.parametrize("n", range(3000))
def test_trivial_arithmetic_is_consistent(n):
    assert (n + 1) - 1 == n

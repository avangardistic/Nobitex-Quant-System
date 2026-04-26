"""Simple deterministic parameter search helpers.

Limitations:
- Provides grid and seeded random search only; no Bayesian optimization.
"""

from __future__ import annotations

import itertools
import random
from typing import Any


def grid_search(space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(space)
    return [dict(zip(keys, values)) for values in itertools.product(*(space[key] for key in keys))]


def random_search(space: dict[str, list[Any]], samples: int, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    keys = list(space)
    return [{key: rng.choice(space[key]) for key in keys} for _ in range(samples)]

# variation-assigner

Deterministic variation assignment SDK.

Overview
--------

`variation-assigner` provides a small, deterministic SDK to assign users to
experiment variations based on a stable hash of `experiment_id + user_id`.
It allows specifying a `traffic_allocation` (fraction of users that enter
the experiment) and per-variation allocation fractions that must sum to 1.0.

Key features
------------
- Deterministic assignment using MD5 (stable across runs).
- Per-experiment `traffic_allocation` and per-variation allocations.
- Package layout and tests included for easy publishing.

Installation
------------

Build a wheel locally and install:

```bash
python -m pip install --upgrade build
python -m build
python -m pip install dist/variation-assigner-0.1.0-py3-none-any.whl
```

Or install from source (editable):

```bash
python -m pip install -e .
```

Quick Usage
-----------

```python
from variation_assigner import VariationAssigner

# 50% traffic enters experiment; within experiment, control=50%, treatment=50%
assigner = VariationAssigner("exp_123", 0.5, {"control": 0.5, "treatment": 0.5})

print(assigner.assign_variation("user_42"))

# To assign a DataFrame column, iterate externally for full control:
import pandas as pd
df = pd.DataFrame({"user_id": [f"user{i}" for i in range(1, 31)]})
df["variation"] = [assigner.assign_variation(u) for u in df["user_id"]]
```

API
---

`VariationAssigner(experiment_id: str, traffic_alocation: float, variations)`

- `experiment_id` — unique experiment string used as hash salt.
- `traffic_alocation` — fraction in [0.0, 1.0] of traffic included in the experiment.
- `variations` — either a dict mapping `name -> fraction` that sums to 1.0, or an
	iterable/list of names (balanced equally).

Notes & Best Practices
----------------------
- MD5 is used for deterministic mapping; if cryptographic resistance is
	required consider a different approach. For high-performance large-scale
	assignment, consider using C-backed non-cryptographic hashes and
	vectorized operations.
- Keep `experiment_id` stable for the duration of the experiment; changing it
	will reshuffle assignments.

CI and Packaging
----------------
A GitHub Actions workflow (`.github/workflows/ci.yml`) is included to run
tests and build the wheel on push/pull-request.

References
----------
- MD5: https://en.wikipedia.org/wiki/MD5
- setuptools packaging guide: https://setuptools.pypa.io/

License
-------
MIT


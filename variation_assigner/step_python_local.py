"""Deterministic variation assignment utilities.

This module provides the `VariationAssigner` class which deterministically
assigns users to experiment variations based on an MD5 hash of the
concatenation of `experiment_id` and `user_id`.

The assignment maps the 128-bit MD5 digest to a floating proportion in [0, 1),
then compares that proportion with `traffic_alocation` and per-variation
quantiles to select a variation.

Examples:

    Basic single assignment:

    >>> from step_python_local import VariationAssigner
    >>> assigner = VariationAssigner("exp_123", 0.5, {"control": 0.5, "treatment": 0.5})
    >>> assigner.assign_variation("user_42")  # returns a variation name or 'out of the experiment'

    Batch assignment with pandas:

    >>> import pandas as pd
    >>> df = pd.DataFrame({"user_id": ["user1", "user2", "user3"]})
    >>> df["variation"] = df["user_id"].apply(assigner.assign_variation)
"""

import hashlib


class VariationAssigner:
    """Assign users deterministically to experiment variations.

    Args:
        experiment_id (str): Unique identifier for the experiment; used as a salt
            when hashing user ids so assignments differ across experiments.
        traffic_alocation (float): Fraction of traffic to include in the
            experiment. Must be between 0.0 and 1.0. Users with a generated
            proportion >= this value are considered "out of the experiment".
        variations (list): Ordered list of variations. Each item can be either
            a mapping whose key is the variation name (e.g. {'control': {...}})
            or a plain string with the variation name.

    Attributes:
        experiment_id (str)
        traffic_alocation (float)
        variations (dict): Mapping of variation name -> allocation fraction

    Examples:

        Create an assigner with two variations and 50% traffic allocation::

            from step_python_local import VariationAssigner
            assigner = VariationAssigner("exp_123", 0.5, {"control": 0.5, "treatment": 0.5})

        Assign a single user::

            variation = assigner.assign_variation("user1")

        Assign a pandas DataFrame column in batch::

            import pandas as pd
            df = pd.DataFrame({"user_id": ["user1", "user2"]})
            df["variation"] = df["user_id"].apply(assigner.assign_variation)
    """

    def __init__(self, experiment_id: str, traffic_alocation: float, variations):
        """Initialize the assigner.

        `variations` may be either:
        - a dict mapping variation-name -> allocation-fraction (floats summing to 1.0),
        - an iterable/list of variation names (balanced allocation is applied).

        The constructor validates `traffic_alocation` is in [0.0, 1.0] and that
        variation allocations sum to 1.0 (when provided as a dict).
        """

        # Basic validation for traffic allocation
        if not (0.0 <= traffic_alocation <= 1.0):
            raise ValueError('traffic_alocation must be between 0.0 and 1.0')

        self.experiment_id = experiment_id
        self.traffic_alocation = float(traffic_alocation)

        # Normalize variations into a dict mapping name -> allocation
        if isinstance(variations, dict):
            var_alloc = {str(k): float(v) for k, v in variations.items()}
        else:
            # Treat as iterable of names and balance evenly
            names = list(variations)
            if len(names) == 0:
                var_alloc = {}
            else:
                equal = 1.0 / len(names)
                var_alloc = {str(n): equal for n in names}

        # Validate allocations sum to 1.0 (if not empty)
        if len(var_alloc) > 0:
            total = sum(var_alloc.values())
            if abs(total - 1.0) > 1e-8:
                raise ValueError('Sum of variation allocations must be 1.0')
            for name, alloc in var_alloc.items():
                if alloc < 0.0 or alloc > 1.0:
                    raise ValueError(f'Invalid allocation for {name}: {alloc}')

        self.variations = var_alloc

    def assign_variation(self, user_id: str):
        """Assign a single `user_id` to a variation.

        The assignment is deterministic: the same `experiment_id` and
        `user_id` always yield the same result.

        Args:
            user_id (str): Identifier for the user. Must be a string.

        Returns:
            str | None: The assigned variation name, the string
            `'out of the experiment'` if the user falls outside
            `traffic_alocation`, or `None` if a variation entry is `None`.

        Raises:
            ValueError: If `user_id` is not a string.
        """

        if not isinstance(user_id, str):
            raise ValueError('user_id must be string')

        compressed_val = self.__generate_hash_proportion(user_id)
        return self.__select_variation(compressed_val)

    def __generate_hash_proportion(self, user_id: str):
        """Generate a deterministic pseudo-random float in [0, 1).

        The method computes MD5(experiment_id + user_id), interprets the
        hex digest as an integer, and divides by the maximum 128-bit value
        to normalize into a floating proportion.

        Args:
            user_id (str): Identifier for the user.

        Returns:
            float: A deterministic float in [0, 1).
        """

        # Maximum value for a 128-bit integer (MD5 digest interpreted as int)
        max_val = 340282366920938463463374607431768211455

        data_bytes = str.encode(self.experiment_id + user_id)
        hash_experiment = hashlib.md5(data_bytes)
        hex_experiment = hash_experiment.hexdigest()
        hash_val = int(hex_experiment, 16)

        hash_proportion = hash_val / max_val

        return hash_proportion

    def __select_variation(self, random_val: float):
        """Select a variation based on a normalized hash value.

        Args:
            random_val (float): A float in [0, 1) produced by
                `__generate_hash_proportion`.

        Returns:
            str | None: The selected variation name; `'out of the experiment'`
            if `random_val` is outside `traffic_alocation`; or `None` when a
            variation entry is `None`.

        Notes:
            - The experiment allocation (`traffic_alocation`) is divided evenly
              across the provided `variations` list.
            - Variation entries may be dicts (with name as key) or simple
              strings. The selection respects the list order.
        """

        variation_name = 'out of the experiment'

        if len(self.variations) == 0:
            return variation_name

        # If the hashed value is outside the experiment allocation, return default
        if self.traffic_alocation <= 0.0 or random_val >= self.traffic_alocation:
            return variation_name

        # Normalize the random value to the [0,1) range inside the experiment
        normalized = random_val / self.traffic_alocation

        # Iterate variations in insertion order (dict preserves order in Python 3.7+)
        cumulative = 0.0
        for name, alloc in self.variations.items():
            cumulative += alloc
            if normalized < cumulative:
                variation_name = name
                break

        return variation_name

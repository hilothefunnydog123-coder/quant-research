#!/usr/bin/env python3
# Research Note XXX — [Your Question]
# Author: [Your Name] — MIT License.
#
# One seeded, reproducible script. Running it must regenerate every number and
# figure in your paper. Seed all randomness so results are identical each run.
"""[one-line description of what this experiment tests]"""
from __future__ import annotations

import json
import os

import numpy as np

FIG = os.path.join(os.path.dirname(__file__), "paper", "figures")
os.makedirs(FIG, exist_ok=True)


def experiment():
    """Run the study. Return a dict of the results you'll cite in the paper."""
    # TODO: your analysis here. Use only past data (no lookahead). If you use
    # random data, seed it: rng = np.random.default_rng(0)
    results = {}
    return results


def main():
    results = experiment()
    print(json.dumps(results, indent=2))
    with open(os.path.join(os.path.dirname(__file__), "results.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()

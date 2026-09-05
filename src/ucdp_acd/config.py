"""Paths and dataset-level constants.

Everything version-specific about UCDP/PRIO ACD lives here or in
``schema.py``, so that upgrading to a new release is a diff in two files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# Repository root, resolved relative to this file rather than the cwd so that
# the pipeline behaves the same from a notebook, a test runner or the CLI.
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = REPO_ROOT / "reference"

#: The dataset release this code was written against. ``validate`` aborts on
#: a mismatch rather than silently mixing releases with different codings.
EXPECTED_VERSION = "26.1"

#: Observation window of the shipped release. Used only for sanity checks.
FIRST_YEAR = 1946
LAST_YEAR = 2025

DEFAULT_RAW_FILE = RAW_DIR / "UcdpPrioConflict_v26_1.csv"


@dataclass(frozen=True)
class Paths:
	"""Resolved input and output locations for one pipeline run."""

	raw_file: Path = DEFAULT_RAW_FILE
	processed_dir: Path = PROCESSED_DIR
	reference_dir: Path = REFERENCE_DIR

	def ensure_output_dir(self) -> None:
		self.processed_dir.mkdir(parents=True, exist_ok=True)

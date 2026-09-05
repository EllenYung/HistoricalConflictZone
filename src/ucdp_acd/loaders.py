"""Reading the raw release.

The loader deliberately does no cleaning. It reads every column as a string so
that validation sees the file as shipped, and coercion happens in ``clean``
where it can be reasoned about.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_raw(path: str | Path) -> pd.DataFrame:
	"""Read the UCDP/PRIO ACD CSV with no type inference.

	Empty strings become ``pd.NA``. Every column is ``string`` dtype, including
	IDs, because several ID columns are nullable and comma-separated and would
	otherwise be inferred as ``float64``.

	Parameters
	----------
	path
		Path to the release CSV, e.g. ``UcdpPrioConflict_v26_1.csv``.

	Raises
	------
	FileNotFoundError
		If the file does not exist, with a message pointing at the download
		page.
	"""
	path = Path(path)
	if not path.is_file():
		raise FileNotFoundError(
			f"Raw dataset not found at {path}. Download the UCDP/PRIO Armed "
			"Conflict Dataset from https://ucdp.uu.se/downloads/ and place the "
			"CSV there."
		)

	df = pd.read_csv(
		path,
		dtype="string",
		keep_default_na=False,
		na_values=[""],
	)
	return df.rename(columns=str.strip)


def read_gw_iso_crosswalk(path: str | Path) -> pd.DataFrame:
	"""Read the Gleditsch and Ward to ISO-3166 crosswalk.

	Expected columns: ``gwno``, ``gw_name``, ``iso3``, ``is_historical``.
	``iso3`` is null for states with no current ISO code (for example the
	German Democratic Republic), which is the case the mapping policy has to
	decide on.
	"""
	df = pd.read_csv(path, dtype={"gwno": "string", "iso3": "string"})
	expected = {"gwno", "gw_name", "iso3", "is_historical"}
	missing = expected - set(df.columns)
	if missing:
		raise ValueError(f"Crosswalk at {path} is missing columns: {sorted(missing)}")
	return df

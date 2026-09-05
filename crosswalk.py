"""Gleditsch and Ward state codes to names and, optionally, ISO-3166 alpha-3.

The ISO mapping is deliberately a *policy*, not a default. Historical states
without current ISO codes require an explicit decision from the caller.
"""

from __future__ import annotations

import logging

import pandas as pd

from loaders import read_gw_iso_crosswalk

logger = logging.getLogger(__name__)


#: ``none`` keeps identity on the GW code and adds no ISO column.
#: ``annotate`` adds ``iso3`` while retaining nulls for historical states.
#: ``current_only`` adds ``iso3`` and drops rows without a current ISO code.
ISO_POLICIES = ("none", "annotate", "current_only")


def load_crosswalk(path) -> pd.DataFrame:
	"""Load and normalise the reference table shipped in ``reference/``."""
	df = read_gw_iso_crosswalk(path)
	df["gwno"] = df["gwno"].astype("string").str.strip()
	df["iso3"] = df["iso3"].astype("string").str.strip().replace("", pd.NA)
	df["is_historical"] = df["is_historical"].astype(bool)
	duplicated = df["gwno"].duplicated()
	if duplicated.any():
		raise ValueError(
			f"Duplicate gwno values in crosswalk: {sorted(df.loc[duplicated, 'gwno'])}"
		)
	return df


def resolve_countries(
	df: pd.DataFrame,
	crosswalk: pd.DataFrame,
	gw_column: str = "gwno_loc",
	policy: str = "none",
) -> pd.DataFrame:
	"""Attach country name and, optionally, ISO code to a GW code column."""
	if policy not in ISO_POLICIES:
		raise ValueError(f"policy must be one of {ISO_POLICIES}, got {policy!r}")

	keep = ["gwno", "gw_name", "is_historical"]
	if policy != "none":
		keep.append("iso3")

	out = df.copy()
	out[gw_column] = out[gw_column].astype("string").str.strip()
	out = out.merge(
		crosswalk[keep], how="left", left_on=gw_column, right_on="gwno"
	).drop(columns=["gwno"])

	unmapped = out.loc[out["gw_name"].isna(), gw_column].dropna().unique()
	if len(unmapped):
		logger.warning(
			"%d GW code(s) absent from the crosswalk: %s. Add them to "
			"reference/gw_states.csv.",
			len(unmapped),
			sorted(unmapped),
		)

	if policy == "current_only":
		dropped = int(out["iso3"].isna().sum())
		if dropped:
			names = sorted(out.loc[out["iso3"].isna(), "gw_name"].dropna().unique())
			logger.warning(
				"policy='current_only' dropped %d row(s) for states with no "
				"current ISO code: %s",
				dropped,
				names,
			)
		out = out[out["iso3"].notna()].reset_index(drop=True)

	return out

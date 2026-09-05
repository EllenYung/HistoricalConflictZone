"""Derived features, chiefly episode reconstruction.

An *episode* is a run of consecutive active years within one conflict. UCDP
records a conflict-year only when the 25-death threshold is met, so a conflict
that drops below the threshold for a year and resumes is two episodes here even
though the underlying dispute never stopped. That is a property of the coding
rule, not a defect, but it means episode counts measure threshold crossings as
much as they measure wars starting.
"""

from __future__ import annotations

import pandas as pd

from . import schema


def add_episode_id(df: pd.DataFrame) -> pd.DataFrame:
	"""Number consecutive runs of active years within each conflict."""
	out = df.sort_values(list(schema.PRIMARY_KEY)).copy()
	gap = out.groupby("conflict_id")["year"].diff().fillna(0).astype("int64").gt(1)
	out["episode_index"] = (
		gap.groupby(out["conflict_id"]).cumsum().astype("int64") + 1
	)
	out["episode_id"] = (
		out["conflict_id"].astype("string")
		+ "-"
		+ out["episode_index"].astype("string")
	)
	return out.reset_index(drop=True)


def build_episodes(df: pd.DataFrame) -> pd.DataFrame:
	"""Collapse the conflict-year table to one row per episode."""
	frame = add_episode_id(df) if "episode_id" not in df.columns else df.copy()
	final_year = int(frame["year"].max())

	grouped = frame.groupby(["conflict_id", "episode_index"], as_index=False)
	episodes = grouped.agg(
		episode_id=("episode_id", "first"),
		location=("location", "first"),
		side_a=("side_a", "first"),
		incompatibility=("incompatibility", "first"),
		incompatibility_label=("incompatibility_label", "first"),
		region_label=("region_label", "first"),
		start_year=("year", "min"),
		end_year=("year", "max"),
		active_years=("year", "size"),
		peak_intensity=("intensity_level", "max"),
		war_years=("intensity_level", lambda values: int((values == 2).sum())),
		type_at_start=("type_of_conflict", "first"),
		type_at_end=("type_of_conflict", "last"),
		internationalized_years=("is_internationalized", "sum"),
		episode_start_date=("start_date2", "first"),
		episode_end_date=("ep_end_date", "last"),
	)

	episodes["duration_years"] = episodes["end_year"] - episodes["start_year"] + 1
	episodes["is_ongoing"] = episodes["end_year"] == final_year
	episodes["reached_war"] = episodes["peak_intensity"] == 2
	episodes["changed_type"] = episodes["type_at_start"] != episodes["type_at_end"]
	episodes["peak_intensity_label"] = pd.Categorical(
		episodes["peak_intensity"].map(schema.INTENSITY_LABELS),
		categories=list(schema.INTENSITY_LABELS.values()),
		ordered=True,
	)
	return episodes.sort_values(["conflict_id", "episode_index"]).reset_index(drop=True)


def add_conflict_age(df: pd.DataFrame) -> pd.DataFrame:
	"""Add years elapsed since the conflict's first battle-related death."""
	out = df.copy()
	out["conflict_age"] = out["year"] - out["start_date"].dt.year
	return out

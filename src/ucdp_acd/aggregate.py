"""The four analysis-ready output tables.

For the base tables, a conflict is counted once per year globally. Per-country
figures come from ``conflict_locations``, where one conflict-year may appear
once per involved country by design.
"""

from __future__ import annotations

import pandas as pd

from . import clean, crosswalk, features, schema


#: Dimensions exposed in ``summary_yearly``, as (column, dimension label) pairs.
SUMMARY_DIMENSIONS: tuple[tuple[str, str], ...] = (
	("type_broad", "Conflict type (broad)"),
	("type_label", "Conflict type"),
	("incompatibility_label", "Incompatibility"),
	("region_label", "Region"),
	("intensity_label", "Intensity"),
)


def _categories(series: pd.Series) -> list:
	"""Category list, preserving categorical order where present."""
	if isinstance(series.dtype, pd.CategoricalDtype):
		return [category for category in series.cat.categories if category in set(series.dropna())]
	return sorted(series.dropna().unique())


def count_by_year(
	df: pd.DataFrame,
	column: str | None = None,
	dimension: str = "All conflicts",
	fill_gaps: bool = True,
) -> pd.DataFrame:
	"""Count distinct conflicts per year, optionally split by one column."""
	frame = df.copy()
	if column is None:
		frame = frame.assign(_category=dimension)
		column = "_category"
		categories = [dimension]
	else:
		categories = _categories(frame[column])

	frame["_is_war"] = frame["intensity_level"] == 2
	grouped = (
		frame.groupby(["year", column], observed=True, dropna=False)
		.agg(n_conflicts=("conflict_id", "nunique"), n_wars=("_is_war", "sum"))
		.reset_index()
		.rename(columns={column: "category"})
	)
	grouped["category"] = grouped["category"].astype("string")

	if fill_gaps:
		years = range(int(df["year"].min()), int(df["year"].max()) + 1)
		grid = pd.MultiIndex.from_product(
			[years, [str(category) for category in categories]],
			names=["year", "category"],
		).to_frame(index=False)
		grid["category"] = grid["category"].astype("string")
		grouped = grid.merge(grouped, on=["year", "category"], how="left")
		grouped[["n_conflicts", "n_wars"]] = (
			grouped[["n_conflicts", "n_wars"]].fillna(0).astype("int64")
		)

	grouped.insert(1, "dimension", dimension)
	return grouped.sort_values(["dimension", "category", "year"]).reset_index(drop=True)


def build_summary_yearly(df: pd.DataFrame) -> pd.DataFrame:
	"""Build stacked long yearly counts across every configured dimension."""
	parts = [count_by_year(df)]
	for column, dimension in SUMMARY_DIMENSIONS:
		if column in df.columns:
			parts.append(count_by_year(df, column=column, dimension=dimension))
	return pd.concat(parts, ignore_index=True)


def build_conflict_locations(
	df: pd.DataFrame,
	gw_states: pd.DataFrame,
	iso_policy: str = "none",
) -> pd.DataFrame:
	"""Build the long conflict-year-country table, one GW code per row."""
	long = clean.explode_multivalue(df, columns=("gwno_loc",))
	long = crosswalk.resolve_countries(
		long, gw_states, gw_column="gwno_loc", policy=iso_policy
	)

	attributes = [
		"conflict_id",
		"year",
		"type_label",
		"type_broad",
		"incompatibility_label",
		"intensity_level",
		"intensity_label",
		"is_multi_country",
	]
	available = [column for column in attributes if column in df.columns]
	out = long.merge(df[available], on=list(schema.PRIMARY_KEY), how="left")
	return out.sort_values(["year", "gwno_loc", "conflict_id"]).reset_index(drop=True)


def build_country_year(locations: pd.DataFrame) -> pd.DataFrame:
	"""Aggregate conflict locations into country-year counts."""
	frame = locations.copy()
	frame["_is_war"] = frame["intensity_level"] == 2
	grouped = (
		frame.groupby(["gwno_loc", "gw_name", "year"], observed=True, dropna=False)
		.agg(n_conflicts=("conflict_id", "nunique"), n_wars=("_is_war", "sum"))
		.reset_index()
	)
	if "iso3" in frame.columns:
		iso = frame[["gwno_loc", "iso3"]].drop_duplicates()
		grouped = grouped.merge(iso, on="gwno_loc", how="left")
	return grouped.sort_values(["gw_name", "year"]).reset_index(drop=True)


def build_all(
	conflicts: pd.DataFrame,
	gw_states: pd.DataFrame | None = None,
	iso_policy: str = "none",
) -> dict[str, pd.DataFrame]:
	"""Produce every output table from a cleaned conflict-year frame."""
	enriched = features.add_conflict_age(features.add_episode_id(conflicts))
	tables: dict[str, pd.DataFrame] = {
		"conflicts_yearly": enriched,
		"conflict_episodes": features.build_episodes(enriched),
		"summary_yearly": build_summary_yearly(enriched),
	}

	if gw_states is not None:
		locations = build_conflict_locations(enriched, gw_states, iso_policy=iso_policy)
		tables["conflict_locations"] = locations
		tables["country_year"] = build_country_year(locations)

	return tables

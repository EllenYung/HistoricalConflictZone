"""Cleaning decisions.

Every function takes a DataFrame and returns a new one. Nothing mutates in
place, so a notebook can inspect the frame after any single step.

The guiding rule: raw codes are never replaced, only accompanied. Downstream
code can filter on ``incompatibility == 1`` or on ``incompatibility_label``,
whichever reads better, and neither can drift from the other.
"""

from __future__ import annotations

import pandas as pd

import schema


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
	"""Convert the all-string raw frame to analysis dtypes."""
	out = df.copy()
	for column in schema.INT_COLUMNS:
		if column in out.columns:
			out[column] = pd.to_numeric(out[column], errors="coerce").astype("Int64")
	for column in schema.DATE_COLUMNS:
		if column in out.columns:
			out[column] = pd.to_datetime(out[column], format="%Y-%m-%d", errors="coerce")
	for column in out.columns:
		if out[column].dtype == "string":
			out[column] = out[column].str.strip()
	return out


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
	"""Attach human-readable labels next to the numeric codes."""
	out = df.copy()

	def _labelled(source: str, mapping: dict[int, str]) -> pd.Categorical:
		categories = list(dict.fromkeys(mapping.values()))
		return pd.Categorical(
			out[source].map(mapping), categories=categories, ordered=True
		)

	out["incompatibility_label"] = _labelled(
		"incompatibility", schema.INCOMPATIBILITY_LABELS
	)
	out["intensity_label"] = _labelled("intensity_level", schema.INTENSITY_LABELS)
	out["type_label"] = _labelled("type_of_conflict", schema.TYPE_LABELS)
	out["type_broad"] = _labelled("type_of_conflict", schema.TYPE_BROAD_LABELS)
	out["region_label"] = _region_label(out["region"])
	return out


def _region_label(region: pd.Series) -> pd.Series:
	"""Map region codes, treating comma-separated values as multi-region."""
	codes = region.astype("string").str.strip()

	def _map(value: object) -> object:
		if pd.isna(value):
			return pd.NA
		parts = [part.strip() for part in str(value).split(",") if part.strip()]
		if len(parts) != 1:
			return "Multiple regions"
		return schema.REGION_LABELS.get(int(parts[0]), pd.NA)

	categories = list(schema.REGION_LABELS.values()) + ["Multiple regions"]
	return pd.Categorical(codes.map(_map), categories=categories, ordered=False)


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
	"""Add booleans that make analytical caveats filterable rather than tacit."""
	out = df.copy()
	out["start_date2_reliable"] = out["start_prec2"] <= schema.MAX_RELIABLE_PRECISION
	out["start_date_reliable"] = out["start_prec"] <= schema.MAX_RELIABLE_PRECISION
	out["is_censored_year"] = out["year"] == out["year"].max()
	out["is_multi_country"] = out["gwno_loc"].fillna("").str.contains(",")
	out["is_internationalized"] = out["type_of_conflict"] == 4
	return out


def drop_dead_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
	"""Remove empty and constant columns, returning them as run metadata."""
	out = df.copy()
	metadata: dict[str, str] = {}

	for column in schema.CONSTANT_COLUMNS:
		if column in out.columns:
			values = out[column].dropna().unique()
			if len(values) == 1:
				metadata[column] = str(values[0])
				out = out.drop(columns=[column])

	dead = [
		column
		for column in schema.KNOWN_EMPTY_COLUMNS
		if column in out.columns and out[column].isna().all()
	]
	out = out.drop(columns=dead)
	return out, metadata


def explode_multivalue(
	df: pd.DataFrame,
	columns: tuple[str, ...],
	id_columns: tuple[str, ...] = schema.PRIMARY_KEY,
) -> pd.DataFrame:
	"""Split comma-separated columns into a long table, one row per value."""
	subset = df[list(id_columns) + list(columns)].copy()
	for column in columns:
		subset[column] = subset[column].astype("string").fillna("").str.split(",")
	out = subset.explode(list(columns), ignore_index=True)
	for column in columns:
		out[column] = out[column].astype("string").str.strip().replace("", pd.NA)
	return out.dropna(subset=list(columns), how="all").reset_index(drop=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
	"""Full cleaning pipeline: raw strings in, analysis frame plus metadata out."""
	out = coerce_types(df)
	out = add_labels(out)
	out = add_quality_flags(out)
	out, metadata = drop_dead_columns(out)
	return out.sort_values(list(schema.PRIMARY_KEY)).reset_index(drop=True), metadata

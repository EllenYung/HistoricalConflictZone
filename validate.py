"""Data quality checks run against the raw release.

Two severities:

* **error** - the file is not what the pipeline was written for. Cleaning it
  would produce a plausible-looking but wrong result, so ``validate`` raises.
* **warning** - a known quirk of the release (an empty documented column, a
  right-censored final year). Recorded and reported, does not stop the run.

Checks are written against the *raw* string frame so that a type coercion
failure is reported as a data problem rather than a traceback in ``clean``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

import schema
from config import EXPECTED_VERSION, FIRST_YEAR, LAST_YEAR


class ValidationError(RuntimeError):
	"""Raised when the raw file violates a required pipeline assumption."""


@dataclass
class ValidationReport:
	"""Outcome of a validation run."""

	errors: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)

	@property
	def ok(self) -> bool:
		return not self.errors

	def add_error(self, message: str) -> None:
		self.errors.append(message)

	def add_warning(self, message: str) -> None:
		self.warnings.append(message)

	def raise_if_failed(self) -> None:
		if self.errors:
			joined = "\n  - ".join(self.errors)
			raise ValidationError(f"Raw dataset failed validation:\n  - {joined}")

	def summary(self) -> str:
		return (
			f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
			if (self.errors or self.warnings)
			else "all checks passed"
		)


def _as_int(series: pd.Series) -> pd.Series:
	return pd.to_numeric(series, errors="coerce").astype("Int64")


def check_schema(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Column set and order must match the codebook."""
	actual = tuple(df.columns)
	if actual != schema.EXPECTED_COLUMNS:
		missing = sorted(set(schema.EXPECTED_COLUMNS) - set(actual))
		unexpected = sorted(set(actual) - set(schema.EXPECTED_COLUMNS))
		if missing or unexpected:
			report.add_error(
				f"Column mismatch. Missing: {missing}. Unexpected: {unexpected}."
			)
		else:
			report.add_warning("Columns present but in a different order than v26.1.")


def check_version(df: pd.DataFrame, report: ValidationReport) -> None:
	"""A single, expected release version across all rows."""
	if "version" not in df.columns:
		return
	versions = set(df["version"].dropna().unique())
	if versions != {EXPECTED_VERSION}:
		report.add_error(
			f"Expected version {EXPECTED_VERSION!r} on every row, found {sorted(versions)}. "
			"Update config.EXPECTED_VERSION and re-check the codebook before proceeding."
		)


def check_primary_key(df: pd.DataFrame, report: ValidationReport) -> None:
	"""conflict_id + year uniquely identifies a row."""
	key = list(schema.PRIMARY_KEY)
	if not set(key).issubset(df.columns):
		return
	n_dupes = int(df.duplicated(key).sum())
	if n_dupes:
		report.add_error(f"{n_dupes} duplicate rows on {key}.")
	if df[key].isna().any().any():
		report.add_error(f"Null values in primary key columns {key}.")


def check_categorical_domains(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Coded variables contain only codebook-permitted values."""
	domains = {
		"incompatibility": set(schema.INCOMPATIBILITY_LABELS),
		"intensity_level": set(schema.INTENSITY_LABELS),
		"type_of_conflict": set(schema.TYPE_LABELS),
		"cumulative_intensity": {0, 1},
		"ep_end": {0, 1},
		"start_prec": set(schema.VALID_START_PRECISION),
		"start_prec2": set(schema.VALID_START_PRECISION),
	}
	for column, allowed in domains.items():
		if column not in df.columns:
			continue
		observed = set(_as_int(df[column]).dropna().unique())
		unexpected = observed - allowed
		if unexpected:
			report.add_error(
				f"{column} contains values outside the codebook: {sorted(unexpected)}."
			)


def check_year_range(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Years fall inside the documented observation window."""
	if "year" not in df.columns:
		return
	years = _as_int(df["year"]).dropna()
	if years.empty:
		report.add_error("No parseable years.")
		return
	if years.min() < FIRST_YEAR or years.max() > LAST_YEAR:
		report.add_error(
			f"Years span {years.min()}-{years.max()}, outside the expected "
			f"{FIRST_YEAR}-{LAST_YEAR} window."
		)


def check_dates_parse(df: pd.DataFrame, report: ValidationReport) -> None:
	"""All three date columns parse as ISO dates."""
	for column in schema.DATE_COLUMNS:
		if column not in df.columns:
			continue
		parsed = pd.to_datetime(df[column], format="%Y-%m-%d", errors="coerce")
		bad = int((parsed.isna() & df[column].notna()).sum())
		if bad:
			report.add_error(f"{bad} unparseable dates in {column}.")


def check_date_ordering(df: pd.DataFrame, report: ValidationReport) -> None:
	"""start_date <= start_date2 <= ep_end_date where all are present."""
	required = set(schema.DATE_COLUMNS)
	if not required.issubset(df.columns):
		return
	parsed = {
		c: pd.to_datetime(df[c], format="%Y-%m-%d", errors="coerce")
		for c in schema.DATE_COLUMNS
	}
	n_bad = int((parsed["start_date"] > parsed["start_date2"]).sum())
	if n_bad:
		report.add_error(f"{n_bad} rows where start_date is after start_date2.")

	both = parsed["start_date2"].notna() & parsed["ep_end_date"].notna()
	n_bad = int((parsed["start_date2"][both] > parsed["ep_end_date"][both]).sum())
	if n_bad:
		report.add_error(f"{n_bad} rows where start_date2 is after ep_end_date.")


def check_structural_missingness(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Nulls that encode meaning must follow their documented rule exactly."""
	required = {
		"incompatibility",
		"territory_name",
		"ep_end",
		"ep_end_date",
		"type_of_conflict",
		"side_a_2nd",
		"side_b_2nd",
	}
	if not required.issubset(df.columns):
		return

	incompatibility = _as_int(df["incompatibility"])
	territory_null = df["territory_name"].isna()
	mismatch = int(((incompatibility == 2) != territory_null).sum())
	if mismatch:
		report.add_error(
			f"{mismatch} rows where territory_name null does not correspond to "
			"incompatibility == 2 (government)."
		)

	ep_end = _as_int(df["ep_end"])
	end_date_null = df["ep_end_date"].isna()
	mismatch = int(((ep_end == 0) != end_date_null).sum())
	if mismatch:
		report.add_error(
			f"{mismatch} rows where ep_end_date presence disagrees with ep_end."
		)

	conflict_type = _as_int(df["type_of_conflict"])
	has_secondary = df["side_a_2nd"].notna() | df["side_b_2nd"].notna()
	n_bad = int(((conflict_type == 3) & has_secondary).sum())
	if n_bad:
		report.add_error(
			f"{n_bad} intrastate (type 3) rows have a secondary party, which "
			"should make them type 4."
		)
	n_bad = int(((conflict_type == 4) & ~has_secondary).sum())
	if n_bad:
		report.add_error(
			f"{n_bad} internationalized intrastate (type 4) rows have no "
			"secondary party."
		)


def check_cumulative_intensity(df: pd.DataFrame, report: ValidationReport) -> None:
	"""cumulative_intensity is a latch: once 1, never back to 0."""
	required = {"conflict_id", "year", "cumulative_intensity", "intensity_level"}
	if not required.issubset(df.columns):
		return
	frame = pd.DataFrame(
		{
			"conflict_id": _as_int(df["conflict_id"]),
			"year": _as_int(df["year"]),
			"cumulative_intensity": _as_int(df["cumulative_intensity"]),
			"intensity_level": _as_int(df["intensity_level"]),
		}
	).sort_values(["conflict_id", "year"])

	decreases = (
		frame.groupby("conflict_id")["cumulative_intensity"].diff().fillna(0) < 0
	)
	if int(decreases.sum()):
		report.add_error(
			f"{int(decreases.sum())} rows where cumulative_intensity decreases "
			"within a conflict."
		)

	impossible = (frame["intensity_level"] == 2) & (frame["cumulative_intensity"] == 0)
	if int(impossible.sum()):
		report.add_error(
			f"{int(impossible.sum())} rows coded as war but with "
			"cumulative_intensity 0."
		)


def check_multivalue_alignment(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Paired name and code columns must split into the same number of tokens."""
	for name_col, code_col in schema.COUNT_MATCHED_PAIRS:
		if name_col not in df.columns or code_col not in df.columns:
			continue
		names = df[name_col].fillna("").str.split(",").map(len)
		codes = df[code_col].fillna("").str.split(",").map(len)
		n_bad = int((names != codes).sum())
		if n_bad:
			report.add_error(
				f"{n_bad} rows where {name_col} and {code_col} split into a "
				f"different number of values; {code_col} cannot be exploded safely."
			)


def check_known_quirks(df: pd.DataFrame, report: ValidationReport) -> None:
	"""Record expected imperfections so they stay visible rather than assumed."""
	for column in schema.KNOWN_EMPTY_COLUMNS:
		if column in df.columns and df[column].isna().all():
			report.add_warning(
				f"{column} is documented in the codebook but empty in every row; "
				"it is dropped from the analysis table."
			)
		elif column in df.columns:
			report.add_warning(
				f"{column} was empty in v26.1 but now has values; reconsider "
				"dropping it."
			)

	if "year" not in df.columns or "ep_end" not in df.columns:
		return
	years = _as_int(df["year"])
	if years.dropna().empty:
		return
	final_year = int(years.max())
	ep_end = _as_int(df["ep_end"])
	if int(((years == final_year) & (ep_end == 1)).sum()) == 0:
		report.add_warning(
			f"ep_end is 0 for all {int((years == final_year).sum())} rows in "
			f"{final_year} by construction. The final year is right-censored: "
			"exclude it from any analysis of conflict termination."
		)


#: Run in this order by `validate`.
CHECKS = (
	check_schema,
	check_version,
	check_primary_key,
	check_categorical_domains,
	check_year_range,
	check_dates_parse,
	check_date_ordering,
	check_structural_missingness,
	check_cumulative_intensity,
	check_multivalue_alignment,
	check_known_quirks,
)


def validate(df: pd.DataFrame, strict: bool = True) -> ValidationReport:
	"""Run every check against a raw frame.

	Parameters
	----------
	df
		The frame returned by `loaders.load_raw`.
	strict
		If True, raise `ValidationError` when any check fails. Set False to
		collect a full report when investigating a new release.
	"""
	report = ValidationReport()
	for check in CHECKS:
		check(df, report)
	if strict:
		report.raise_if_failed()
	return report

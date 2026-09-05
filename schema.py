"""Codebook v26.1 encoded as data.

Keeping the codebook here rather than inline in the cleaning functions means a
label never has to be retyped in plotting code, and a coding change in a future
release is caught by ``validate.check_categorical_domains`` instead of silently
producing a mislabelled chart.
"""

from __future__ import annotations


#: Columns as shipped, in order. Order is checked as well as membership: a
#: reordered file usually signals a hand-edited export rather than an official
#: release.
EXPECTED_COLUMNS: tuple[str, ...] = (
	"conflict_id",
	"location",
	"side_a",
	"side_a_id",
	"side_a_2nd",
	"side_b",
	"side_b_id",
	"side_b_2nd",
	"incompatibility",
	"territory_name",
	"year",
	"intensity_level",
	"cumulative_intensity",
	"type_of_conflict",
	"start_date",
	"start_prec",
	"start_date2",
	"start_prec2",
	"ep_end",
	"ep_end_date",
	"ep_end_prec",
	"gwno_a",
	"gwno_a_2nd",
	"gwno_b",
	"gwno_b_2nd",
	"gwno_loc",
	"region",
	"version",
)

#: The natural key of the conflict-year table.
PRIMARY_KEY: tuple[str, str] = ("conflict_id", "year")

#: Read as string, then coerced. Reading numeric-looking ID columns as strings
#: first avoids pandas inferring float64 for a column that is nullable and
#: comma-separated (e.g. ``gwno_b``, ``side_b_id``).
DATE_COLUMNS: tuple[str, ...] = ("start_date", "start_date2", "ep_end_date")
INT_COLUMNS: tuple[str, ...] = (
	"conflict_id",
	"year",
	"incompatibility",
	"intensity_level",
	"cumulative_intensity",
	"type_of_conflict",
	"start_prec",
	"start_prec2",
	"ep_end",
)

#: Comma-separated, variable arity. ``location`` and ``gwno_loc`` are safe to
#: split on commas; ``side_b`` is NOT (some organisation names contain a
#: comma), which is why no side_b long table is produced at conflict level.
MULTIVALUE_COLUMNS: tuple[str, ...] = (
	"location",
	"gwno_loc",
	"region",
	"side_a",
	"gwno_a",
	"side_a_2nd",
	"gwno_a_2nd",
	"side_b",
	"side_b_id",
	"side_b_2nd",
	"gwno_b",
	"gwno_b_2nd",
)

#: Name/code pairs that must have equal token counts when split on commas.
#:
#: Equal counts do NOT imply equal ordering. In multi-country rows ``location``
#: is sorted alphabetically by name while ``gwno_loc`` is sorted numerically by
#: code, so conflict 215 reads ``location="Albania, United Kingdom"`` against
#: ``gwno_loc="200, 339"`` even though Albania is 339 and the UK is 200.
#: Exploding both columns together would pair each country with the wrong code.
#: Country names are therefore always resolved through
#: ``reference/gw_states.csv``.
COUNT_MATCHED_PAIRS: tuple[tuple[str, str], ...] = (
	("location", "gwno_loc"),
	("side_a", "gwno_a"),
)

INCOMPATIBILITY_LABELS: dict[int, str] = {
	1: "Territory",
	2: "Government",
	3: "Government and territory",
}

INTENSITY_LABELS: dict[int, str] = {
	1: "Minor (25-999 deaths)",
	2: "War (1000+ deaths)",
}

TYPE_LABELS: dict[int, str] = {
	1: "Extrasystemic",
	2: "Interstate",
	3: "Intrastate",
	4: "Internationalized intrastate",
}

#: Collapses 3 and 4. Offered alongside ``type_of_conflict``, never instead of
#: it: the 3-to-4 transition is itself a substantive finding.
TYPE_BROAD_LABELS: dict[int, str] = {
	1: "Extrasystemic",
	2: "Interstate",
	3: "Intrastate",
	4: "Intrastate",
}

REGION_LABELS: dict[int, str] = {
	1: "Europe",
	2: "Middle East",
	3: "Asia",
	4: "Africa",
	5: "Americas",
}

#: Precision codes 1-7 for start dates, 1-5 for episode ends (codebook 4.3/4.4).
#: Codes 1-3 mean the year and month are observed rather than assigned; anything
#: above that should not be used for sub-annual analysis.
MAX_RELIABLE_PRECISION = 3
VALID_START_PRECISION = frozenset(range(1, 8))

#: Columns whose nulls are structural (meaningful absence), not defects.
#: ``validate`` asserts the implication rather than treating these as missing
#: data.
STRUCTURAL_NULL_COLUMNS: tuple[str, ...] = (
	"territory_name",
	"side_a_2nd",
	"side_b_2nd",
	"gwno_a_2nd",
	"gwno_b",
	"gwno_b_2nd",
	"ep_end_date",
)

#: Shipped in the release but empty in every row of v26.1. Dropped from the
#: analysis table with a warning so that its reappearance is noticed.
KNOWN_EMPTY_COLUMNS: tuple[str, ...] = ("ep_end_prec",)

#: Constant across the file; moved to a metadata sidecar rather than repeated
#: on 2,816 rows.
CONSTANT_COLUMNS: tuple[str, ...] = ("version",)

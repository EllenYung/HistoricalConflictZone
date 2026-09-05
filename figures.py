"""Regenerate every figure in ``figures/`` from the processed tables.

Run after any change to the pipeline or a new UCDP release, then commit the
resulting PNGs together with the code change that produced them.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for import_dir in (SRC_DIR,):
	if str(import_dir) not in sys.path:
		sys.path.insert(0, str(import_dir))

from ucdp_acd import aggregate, clean, crosswalk, features, loaders, plotting  # noqa: E402
from ucdp_acd.config import DEFAULT_RAW_FILE, REFERENCE_DIR  # noqa: E402


FIGURES_DIR = ROOT_DIR / "figures"

#: Width in the README. GitHub serves images at their natural size, so a
#: 2x-scaled export at this DPI stays sharp on high-density screens.
DPI = 160


def _save(fig: plt.Figure, name: str) -> str:
	path = FIGURES_DIR / f"{name}.png"
	fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
	plt.close(fig)
	print(f"  wrote {path.relative_to(FIGURES_DIR.parent)}")
	return path.name


def build_figures(raw_path: Path, reference_path: Path) -> list[str]:
	"""Build and save all configured figures from one raw release."""
	raw = loaders.load_raw(raw_path)
	conflicts, metadata = clean.clean(raw)
	conflicts = features.add_episode_id(conflicts)

	gw_states = crosswalk.load_crosswalk(reference_path)
	tables = aggregate.build_all(conflicts, gw_states, iso_policy="annotate")
	summary = tables["summary_yearly"]
	episodes = tables["conflict_episodes"]
	final_year = int(conflicts["year"].max())

	plotting.set_theme()
	written: list[str] = []

	fig, ax = plotting.plot_conflicts_by_year(
		summary, dimension="Conflict type (broad)", palette=plotting.TYPE_PALETTE
	)
	plotting.annotate_censoring(ax, final_year)
	written.append(_save(fig, "conflicts_by_type"))

	fig, _ = plotting.plot_composition_area(
		summary, dimension="Conflict type", palette=plotting.TYPE_PALETTE
	)
	written.append(_save(fig, "composition_by_type"))

	fig, _ = plotting.plot_intensity_share(summary)
	written.append(_save(fig, "war_intensity_share"))

	fig, _ = plotting.plot_region_heatmap(summary, bin_years=5)
	written.append(_save(fig, "region_heatmap"))

	fig, _ = plotting.plot_episode_timeline(episodes, top_n=20)
	written.append(_save(fig, "longest_episodes"))

	manifest = {
		"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
		"dataset_version": metadata.get("version"),
		"source_file": raw_path.name,
		"final_year": final_year,
		"figures": written,
	}
	(FIGURES_DIR / "figure_manifest.json").write_text(json.dumps(manifest, indent=2))
	return written


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--raw", default=str(DEFAULT_RAW_FILE))
	parser.add_argument("--reference", default=str(REFERENCE_DIR / "gw_states.csv"))
	args = parser.parse_args(argv)

	FIGURES_DIR.mkdir(exist_ok=True)
	print(f"Rendering figures from {args.raw}")
	try:
		written = build_figures(Path(args.raw), Path(args.reference))
	except FileNotFoundError as error:
		print(f"error: {error}", file=sys.stderr)
		return 1
	print(f"Done: {len(written)} figure(s) in {FIGURES_DIR}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

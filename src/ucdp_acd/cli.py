"""Command-line entry points for the UCDP/PRIO ACD pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import aggregate, clean, crosswalk, loaders, validate
from .config import DEFAULT_RAW_FILE, Paths, REFERENCE_DIR


def build(
    raw_path: Path = DEFAULT_RAW_FILE,
    reference_path: Path = REFERENCE_DIR / "gw_states.csv",
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Validate, clean, aggregate, and write the analysis tables."""
    paths = Paths(raw_file=raw_path)
    destination = output_dir or paths.processed_dir
    raw = loaders.load_raw(raw_path)
    report = validate.validate(raw, strict=True)
    conflicts, metadata = clean.clean(raw)
    outputs = aggregate.build_all(conflicts)

    if reference_path.is_file():
        states = crosswalk.load_crosswalk(reference_path)
        outputs.update(
            {
                "conflict_locations": aggregate.build_conflict_locations(
                    conflicts, states, iso_policy="annotate"
                ),
            }
        )
        outputs["country_year"] = aggregate.build_country_year(
            outputs["conflict_locations"]
        )

    destination.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, frame in outputs.items():
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False)
        written[name] = path

    metadata_path = destination / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                **metadata,
                "dataset_version": metadata.get("version"),
                "raw_file": raw_path.name,
                "validation": report.summary(),
            },
            indent=2,
        )
    )
    written["metadata"] = metadata_path
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="build processed analysis tables")
    build_parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_FILE)
    build_parser.add_argument(
        "--reference", type=Path, default=REFERENCE_DIR / "gw_states.csv"
    )
    build_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "build":
        written = build(args.raw, args.reference, args.output)
        for path in written.values():
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
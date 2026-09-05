"""Plotting helpers for matplotlib and seaborn.

Every function returns ``(Figure, Axes)`` and neither calls ``plt.show()`` nor
writes a file. Output format and DPI remain the caller's responsibility.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from . import schema


SOURCE_NOTE = (
	"Source: UCDP/PRIO Armed Conflict Dataset v26.1 "
	"(Gleditsch et al. 2002; Davies et al. 2026)"
)

#: Fixed colours so intensity and type read the same way across every figure.
INTENSITY_PALETTE: dict[str, str] = {
	schema.INTENSITY_LABELS[1]: "#8FA8C8",
	schema.INTENSITY_LABELS[2]: "#A03623",
}

TYPE_PALETTE: dict[str, str] = {
	"Extrasystemic": "#7A6A53",
	"Interstate": "#A03623",
	"Intrastate": "#4C6E9B",
	"Internationalized intrastate": "#D08C3C",
}


def set_theme(context: str = "notebook", font_scale: float = 1.0) -> None:
	"""Apply a consistent, low-chrome seaborn theme."""
	sns.set_theme(
		context=context,
		style="whitegrid",
		font_scale=font_scale,
		rc={
			"axes.spines.top": False,
			"axes.spines.right": False,
			"grid.linewidth": 0.5,
			"figure.dpi": 110,
		},
	)


def _finish(ax: plt.Axes, title: str, ylabel: str, source: bool) -> None:
	ax.set_title(title, loc="left", fontweight="semibold")
	ax.set_xlabel("")
	ax.set_ylabel(ylabel)
	if source:
		ax.figure.text(0.01, -0.02, SOURCE_NOTE, fontsize=7, color="#666666")


def annotate_censoring(ax: plt.Axes, final_year: int) -> plt.Axes:
	"""Shade and label the final observed, right-censored year."""
	ax.axvspan(final_year - 0.5, final_year + 0.5, color="#BBBBBB", alpha=0.25, lw=0)
	ax.annotate(
		"final year\n(censored)",
		xy=(final_year, ax.get_ylim()[1]),
		xytext=(-4, -6),
		textcoords="offset points",
		ha="right",
		va="top",
		fontsize=7,
		color="#666666",
	)
	return ax


def plot_conflicts_by_year(
	summary: pd.DataFrame,
	dimension: str = "All conflicts",
	value: str = "n_conflicts",
	ax: plt.Axes | None = None,
	palette: dict[str, str] | None = None,
	figsize: tuple[float, float] = (10, 5),
) -> tuple[plt.Figure, plt.Axes]:
	"""Plot active conflicts per year, optionally split by a dimension."""
	data = summary.loc[summary["dimension"] == dimension]
	if data.empty:
		raise ValueError(
			f"No rows for dimension {dimension!r}. Available: "
			f"{sorted(summary['dimension'].unique())}"
		)

	fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=figsize)
	single = data["category"].nunique() == 1
	sns.lineplot(
		data=data,
		x="year",
		y=value,
		hue=None if single else "category",
		palette=None if single else palette,
		linewidth=1.6,
		ax=ax,
	)
	ylabel = "Active conflicts" if value == "n_conflicts" else "Conflicts at war intensity"
	_finish(ax, f"{ylabel} by year, {dimension.lower()}", ylabel, source=True)
	ax.set_ylim(bottom=0)
	if not single:
		ax.legend(title=None, frameon=False, loc="upper left")
	return fig, ax


def plot_composition_area(
	summary: pd.DataFrame,
	dimension: str = "Conflict type (broad)",
	normalize: bool = False,
	ax: plt.Axes | None = None,
	palette: dict[str, str] | None = None,
	figsize: tuple[float, float] = (10, 5),
) -> tuple[plt.Figure, plt.Axes]:
	"""Plot stacked conflict composition over time."""
	data = summary.loc[summary["dimension"] == dimension]
	wide = data.pivot_table(
		index="year", columns="category", values="n_conflicts", aggfunc="sum"
	).fillna(0)
	if normalize:
		wide = wide.div(wide.sum(axis=1).replace(0, pd.NA), axis=0).fillna(0)

	colors = [(palette or {}).get(category) for category in wide.columns]
	if any(color is None for color in colors):
		colors = sns.color_palette("deep", n_colors=len(wide.columns))

	fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=figsize)
	ax.stackplot(wide.index, wide.T.values, labels=list(wide.columns), colors=colors)
	ylabel = "Share of active conflicts" if normalize else "Active conflicts"
	_finish(ax, f"Composition of active conflicts, {dimension.lower()}", ylabel, source=True)
	ax.set_xlim(wide.index.min(), wide.index.max())
	ax.set_ylim(0, 1 if normalize else None)
	ax.legend(title=None, frameon=False, loc="upper left", ncols=2)
	return fig, ax


def plot_region_heatmap(
	summary: pd.DataFrame,
	bin_years: int = 5,
	ax: plt.Axes | None = None,
	figsize: tuple[float, float] = (11, 4),
) -> tuple[plt.Figure, plt.Axes]:
	"""Plot region-by-period conflict-year counts as a heatmap."""
	data = summary.loc[summary["dimension"] == "Region"].copy()
	data["period"] = (data["year"] // bin_years) * bin_years
	wide = data.pivot_table(
		index="category", columns="period", values="n_conflicts", aggfunc="sum"
	).fillna(0)

	fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=figsize)
	sns.heatmap(
		wide,
		cmap="rocket_r",
		linewidths=0.4,
		linecolor="white",
		cbar_kws={"label": "Conflict-years"},
		ax=ax,
	)
	_finish(ax, f"Conflict-years by region, {bin_years}-year periods", "", source=True)
	ax.set_xlabel("")
	return fig, ax


def plot_episode_timeline(
	episodes: pd.DataFrame,
	top_n: int = 25,
	ax: plt.Axes | None = None,
	figsize: tuple[float, float] = (10, 8),
) -> tuple[plt.Figure, plt.Axes]:
	"""Plot a horizontal timeline of the longest conflict episodes."""
	data = episodes.nlargest(top_n, "duration_years").sort_values("start_year")
	fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=figsize)

	labels = []
	for position, (_, row) in enumerate(data.iterrows()):
		ongoing = bool(row["is_ongoing"])
		ax.barh(
			position,
			width=row["duration_years"],
			left=row["start_year"],
			height=0.6,
			color=(
				INTENSITY_PALETTE[schema.INTENSITY_LABELS[2]]
				if row["reached_war"]
				else INTENSITY_PALETTE[schema.INTENSITY_LABELS[1]]
			),
			alpha=0.45 if ongoing else 1.0,
			edgecolor="#333333" if ongoing else "none",
			linewidth=1.0 if ongoing else 0,
		)
		labels.append(f"{row['location']} ({row['incompatibility_label']})")

	ax.set_yticks(range(len(data)))
	ax.set_yticklabels(labels, fontsize=8)
	ax.grid(axis="y", visible=False)
	_finish(ax, f"{top_n} longest conflict episodes", "", source=True)
	ax.figure.text(
		0.01,
		-0.04,
		"Red = reached war intensity (1,000+ deaths in a year). "
		"Outlined = still active in the final year, so duration is a lower bound.",
		fontsize=7,
		color="#666666",
	)
	return fig, ax


def plot_intensity_share(
	summary: pd.DataFrame,
	ax: plt.Axes | None = None,
	figsize: tuple[float, float] = (10, 5),
) -> tuple[plt.Figure, plt.Axes]:
	"""Plot the share of active conflicts at war intensity per year."""
	data = summary.loc[summary["dimension"] == "All conflicts"].copy()
	data["war_share"] = data["n_wars"] / data["n_conflicts"].replace(0, pd.NA)

	fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(figsize=figsize)
	sns.lineplot(
		data=data,
		x="year",
		y="war_share",
		color=INTENSITY_PALETTE[schema.INTENSITY_LABELS[2]],
		linewidth=1.6,
		ax=ax,
	)
	_finish(
		ax,
		"Share of active conflicts reaching war intensity",
		"Share of active conflicts",
		source=True,
	)
	ax.set_ylim(0, 1)
	return fig, ax

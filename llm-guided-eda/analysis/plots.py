"""Report figures (matplotlib + seaborn; 300-dpi PNG and PDF).

Colours are fixed per entity and never depend on rank or on which entities are
present: configurations take the Okabe-Ito colours in the order of
``config/experiment_config.yaml`` (colour-vision-deficiency separation checked
for adjacent pairs; line and scatter plots add marker shapes as a second
channel); outcome / error types take a fixed eight-hue colour-blind-checked
order, the rarer types reuse those hues with hatching, and ``success`` is a
neutral grey so that the failure composition stands out. Sequential heatmaps
use one hue from light to dark.
"""
from __future__ import annotations

import common.paths  # noqa: F401  (must precede matplotlib: keeps MPLCONFIGDIR inside the repository)

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402

from analysis.error_analysis import failed_attempts, outcome_order  # noqa: E402
from analysis.metrics import CATEGORY_ORDER, CONFIG_ORDER, order_configs, ordered  # noqa: E402

OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00", "#CC79A7"]
EXTRA_COLORS = ["#999999", "#000000", "#F0E442"]   # configurations beyond the planned six
CONFIG_COLORS: dict[str, str] = dict(zip(CONFIG_ORDER, OKABE_ITO))
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "h"]
CONFIG_LABELS = {
    "A_baseline": "A baseline", "B_rag": "B RAG", "C_feedback": "C feedback", "D_full": "D full",
    "E_vector_only": "E vector-only", "F_single_repair": "F single repair",
    "G_targeted_repair": "G targeted repair",
}
_HUES = ["#2A78D6", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4", "#008300", "#6250D6", "#E34948"]
OUTCOME_STYLE: dict[str, tuple[str, str]] = {   # outcome -> (face colour, hatch)
    "success": ("#D9D8D3", ""),
    "validation_failure": (_HUES[0], ""),
    "invalid_command": (_HUES[1], ""),
    "invalid_argument": (_HUES[2], ""),
    "tcl_syntax": (_HUES[3], ""),
    "missing_prerequisite": (_HUES[4], ""),
    "incorrect_design_context": (_HUES[5], ""),
    "runtime_failure": (_HUES[6], ""),
    "tool_error": (_HUES[7], ""),
    "missing_file": (_HUES[0], "////"),
    "unsafe_command": (_HUES[1], "////"),
    "unknown_error": (_HUES[2], "////"),
    "harness_error": ("#8C8B86", "////"),
    "no_attempt": ("#8C8B86", "...."),
}
BLUE_RAMP = LinearSegmentedColormap.from_list(
    "completion", ["#CDE2FB", "#9EC5F4", "#6DA7EC", "#3987E5", "#256ABF", "#184F95", "#0D366B"])
ORANGE_RAMP = matplotlib.colormaps["Oranges"]
INK, INK2, GRID, AXIS, SURFACE = "#0B0B0B", "#52514E", "#E1E0D9", "#C3C2B7", "#FFFFFF"
RC = {
    **sns.axes_style("whitegrid"), **sns.plotting_context("paper"),
    "font.size": 8, "axes.labelsize": 8.5, "axes.titlesize": 9, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "legend.title_fontsize": 8, "legend.frameon": False,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "pdf.fonttype": 42, "ps.fonttype": 42, "hatch.linewidth": 0.8,
}


# ------------------------------------------------------------------- helpers
def config_color(cfg: str) -> str:
    if cfg in CONFIG_COLORS:
        return CONFIG_COLORS[cfg]
    extras = sorted(c for c in _seen_extra if c not in CONFIG_COLORS)
    return EXTRA_COLORS[extras.index(cfg) % len(EXTRA_COLORS)] if cfg in extras else EXTRA_COLORS[0]


_seen_extra: set[str] = set()


def _register(configs: Sequence[str]) -> None:
    _seen_extra.update(c for c in configs if c not in CONFIG_COLORS)


def config_marker(cfg: str) -> str:
    order = list(CONFIG_ORDER) + sorted(c for c in _seen_extra if c not in CONFIG_ORDER)
    return MARKERS[order.index(cfg) % len(MARKERS)] if cfg in order else MARKERS[-1]


def config_label(cfg: str, wrap: bool = False) -> str:
    text = CONFIG_LABELS.get(cfg, cfg.replace("_", " "))
    return text.replace(" ", "\n", 1) if wrap else text


def outcome_style(outcome: str) -> tuple[str, str]:
    return OUTCOME_STYLE.get(outcome, ("#8C8B86", "xxxx"))


def outcome_label(outcome: str) -> str:
    return outcome.replace("_", " ")


def save(fig: plt.Figure, out_dir: Path, name: str) -> list[Path]:
    """Write ``<name>.png`` (300 dpi) and ``<name>.pdf`` and close the figure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    png, pdf = out_dir / f"{name}.png", out_dir / f"{name}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor=SURFACE)
    fig.savefig(pdf, bbox_inches="tight", facecolor=SURFACE, metadata={"CreationDate": None})
    plt.close(fig)
    return [png, pdf]


def _finite(v: float) -> bool:
    return v is not None and bool(np.isfinite(v))


# ------------------------------------------------------------------- figures
def plot_completion(main: pd.DataFrame, out_dir: Path, name: str = "completion_by_config") -> list[Path]:
    """Completion per configuration: bar = mean over runs, error bar = sample SD, dots = single runs."""
    configs = order_configs(main["config"])
    _register(configs)
    m = main.set_index("config")
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(max(4.0, 0.95 * len(configs) + 1.2), 3.3))
        for i, cfg in enumerate(configs):
            mean, std = float(m.at[cfg, "completion_mean"]), float(m.at[cfg, "completion_std"])
            ax.bar(i, mean, width=0.64, color=config_color(cfg), edgecolor=SURFACE, linewidth=1.5, zorder=2)
            if _finite(std):
                ax.errorbar(i, mean, yerr=std, color=INK, capsize=4, linewidth=1.0, capthick=1.0, zorder=4)
            runs = np.asarray(m.at[cfg, "completion_runs"], float)
            jitter = np.linspace(-0.13, 0.13, len(runs)) if len(runs) > 1 else np.zeros(len(runs))
            ax.scatter(i + jitter, runs, s=16, facecolor=SURFACE, edgecolor=INK, linewidth=0.8, zorder=5)
            top = max([mean + (std if _finite(std) else 0.0), *runs.tolist()])
            ax.text(i, top + 2.0, f"{mean:.1f}", ha="center", va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(range(len(configs)), [config_label(c, wrap=True) for c in configs])
        ax.set_xlim(-0.6, len(configs) - 0.4)
        ax.set_ylim(0, 112)
        ax.set_yticks(range(0, 101, 20))
        ax.set_ylabel("Task completion (%)")
        ax.grid(axis="x", visible=False)
        handles = [Patch(facecolor="#BDBCB6", label="mean over runs"),
                   Line2D([], [], color=INK, marker="_", markersize=8, linewidth=1.0, label="±1 SD over runs"),
                   Line2D([], [], color=INK, marker="o", markerfacecolor=SURFACE, linestyle="", markersize=4,
                          label="single run")]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0))
        return save(fig, out_dir, name)


def plot_category_heatmap(per_category: pd.DataFrame, out_dir: Path, name: str = "category_heatmap") -> list[Path]:
    """Completion (% mean over runs) for every category x configuration."""
    configs = order_configs(per_category["config"])
    cats = ordered(per_category["category"], CATEGORY_ORDER)
    pivot = per_category.pivot(index="category", columns="config", values="mean").reindex(index=cats, columns=configs)
    n_tasks = per_category.groupby("category")["n_tasks"].max()
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(max(4.2, 0.85 * len(configs) + 2.0), 0.42 * len(cats) + 1.3))
        sns.heatmap(pivot.astype(float), vmin=0, vmax=100, cmap=BLUE_RAMP, annot=True, fmt=".0f",
                    annot_kws={"fontsize": 7.5}, linewidths=2, linecolor=SURFACE, square=False, ax=ax,
                    cbar_kws={"label": "Task completion (%)", "shrink": 0.85})
        ax.set_xticklabels([config_label(c, wrap=True) for c in configs], rotation=0)
        ax.set_yticklabels([f"{c} (n={int(n_tasks.get(c, 0))})" for c in cats], rotation=0)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(length=0)
        return save(fig, out_dir, name)


def plot_error_stacks(dist: pd.DataFrame, out_dir: Path, name: str = "error_types_first_vs_final") -> list[Path]:
    """Outcome composition of attempt 1 vs the final attempt (% of episodes) per configuration."""
    d = dist[dist["stage"].isin(["first_attempt", "final"])]
    configs = order_configs(d["config"])
    outcomes = outcome_order(d["outcome"])
    width, gap = 0.36, 0.05
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(max(4.5, 1.05 * len(configs) + 2.6), 3.6))
        ticks, labels = [], []
        for i, cfg in enumerate(configs):
            for j, stage in enumerate(("first_attempt", "final")):
                x = i + (j - 0.5) * (width + gap)
                pct = d[(d["config"] == cfg) & (d["stage"] == stage)].set_index("outcome")["pct"]
                bottom = 0.0
                for o in outcomes:
                    v = float(pct.get(o, 0.0))
                    if v <= 0:
                        continue
                    face, hatch = outcome_style(o)
                    ax.bar(x, v, width, bottom=bottom, color=face, hatch=hatch, edgecolor=SURFACE, linewidth=1.0,
                           zorder=2)
                    bottom += v
                ticks.append(x)
                labels.append("1st" if j == 0 else "final")
        ax.set_xticks(ticks, labels, fontsize=6.5)
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        for i, cfg in enumerate(configs):
            ax.text(i, -0.09, config_label(cfg), transform=trans, ha="center", va="top", fontsize=7.5)
        ax.set_xlim(-0.6, len(configs) - 0.4)
        ax.set_ylim(0, 100)
        ax.set_ylabel("Episodes (%)")
        ax.grid(axis="x", visible=False)
        handles = [Patch(facecolor=outcome_style(o)[0], hatch=outcome_style(o)[1], edgecolor=SURFACE,
                         label=outcome_label(o)) for o in reversed(outcomes)]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), title="Outcome")
        return save(fig, out_dir, name)


def plot_cumulative_success(cumulative: pd.DataFrame, main: pd.DataFrame, out_dir: Path,
                            name: str = "cumulative_success_by_attempt") -> list[Path]:
    """Episodes solved within k attempts (mean over runs, SD bars) for multi-attempt configurations."""
    info = main.set_index("config")
    multi = [c for c in order_configs(main["config"]) if int(info.at[c, "max_attempts"]) > 1]
    single = [c for c in order_configs(main["config"]) if int(info.at[c, "max_attempts"]) <= 1]
    if not multi:
        return []
    _register(order_configs(main["config"]))
    kmax = int(cumulative[cumulative["config"].isin(multi)]["attempt"].max())
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(4.8, 3.3))
        for cfg in single:
            ax.axhline(float(info.at[cfg, "completion_mean"]), color=config_color(cfg), linewidth=1.2,
                       linestyle=(0, (4, 3)), zorder=1, label=f"{config_label(cfg)} (single shot)")
        offsets = np.linspace(-0.08, 0.08, len(multi)) if len(multi) > 1 else [0.0]
        for cfg, dx in zip(multi, offsets):
            c = cumulative[cumulative["config"] == cfg].sort_values("attempt")
            ax.errorbar(c["attempt"] + dx, c["mean"], yerr=c["std"].fillna(0.0), color=config_color(cfg),
                        marker=config_marker(cfg), markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.0,
                        linewidth=2.0, capsize=3, elinewidth=1.0, label=config_label(cfg), zorder=3)
        ax.set_xticks(range(1, kmax + 1))
        ax.set_xlim(0.7, kmax + 0.3)
        ax.set_ylim(0, 100)
        ax.set_xlabel("Attempt number k")
        ax.set_ylabel("Episodes solved within k attempts (%)")
        ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
        return save(fig, out_dir, name)


def plot_cost_vs_completion(main: pd.DataFrame, cost: pd.DataFrame, out_dir: Path,
                            name: str = "cost_vs_completion") -> list[Path]:
    """Mean LLM cost per task vs completion (SD over runs on both axes)."""
    configs = order_configs(main["config"])
    _register(configs)
    m, c = main.set_index("config"), cost.set_index("config")
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(4.8, 3.3))
        for cfg in configs:
            x, y = float(c.at[cfg, "cost_per_episode_usd"]), float(m.at[cfg, "completion_mean"])
            xerr, yerr = float(c.at[cfg, "cost_per_episode_std_runs"]), float(m.at[cfg, "completion_std"])
            ax.errorbar(x, y, xerr=xerr if _finite(xerr) else None, yerr=yerr if _finite(yerr) else None,
                        fmt=config_marker(cfg), color=config_color(cfg), markersize=8, markeredgecolor=SURFACE,
                        markeredgewidth=1.5, ecolor=config_color(cfg), elinewidth=1.0, capsize=2.5,
                        label=config_label(cfg), zorder=3)
        ax.set_xlim(left=0)
        ax.set_ylim(0, 100)
        ax.set_xlabel("Mean LLM cost per task (USD)")
        ax.set_ylabel("Task completion (%)")
        ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
        return save(fig, out_dir, name)


def plot_failed_executions(dist: pd.DataFrame, episodes: pd.DataFrame, attempts: pd.DataFrame, out_dir: Path,
                           name: str = "failed_executions_per_task") -> list[Path]:
    """Failed OpenROAD executions per task, stacked by error type (bar), SD of per-run means (error bar)."""
    d = dist[dist["stage"] == "failed_executions"]
    configs = order_configs(episodes["config"])
    outcomes = outcome_order(d["outcome"])
    n_ep = episodes.groupby(["config", "run"]).size()
    n_fail = failed_attempts(attempts).groupby(["config", "run"]).size().reindex(n_ep.index, fill_value=0)
    per_run = (n_fail / n_ep).groupby(level="config").agg(["mean", "std"])
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(max(4.5, 0.95 * len(configs) + 2.6), 3.3))
        for i, cfg in enumerate(configs):
            per_ep = d[d["config"] == cfg].set_index("outcome")["per_episode"]
            bottom = 0.0
            for o in outcomes:
                v = float(per_ep.get(o, 0.0))
                if v <= 0:
                    continue
                face, hatch = outcome_style(o)
                ax.bar(i, v, 0.64, bottom=bottom, color=face, hatch=hatch, edgecolor=SURFACE, linewidth=1.0, zorder=2)
                bottom += v
            std = float(per_run["std"].get(cfg, np.nan))
            if _finite(std) and bottom > 0:
                ax.errorbar(i, bottom, yerr=std, color=INK, capsize=4, linewidth=1.0, zorder=4)
        ax.set_xticks(range(len(configs)), [config_label(c, wrap=True) for c in configs])
        ax.set_xlim(-0.6, len(configs) - 0.4)
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Failed executions per task")
        ax.grid(axis="x", visible=False)
        handles = [Patch(facecolor=outcome_style(o)[0], hatch=outcome_style(o)[1], edgecolor=SURFACE,
                         label=outcome_label(o)) for o in reversed(outcomes)]
        handles.append(Line2D([], [], color=INK, marker="_", markersize=8, linewidth=1.0, label="±1 SD over runs"))
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), title="Error type")
        return save(fig, out_dir, name)


def plot_task_heatmap(episodes: pd.DataFrame, value: str, out_dir: Path, name: str, *, cbar_label: str,
                      percent: bool) -> list[Path]:
    """Task x configuration heatmap of the mean over runs of an episode column, tasks grouped by category."""
    configs = order_configs(episodes["config"])
    cats = ordered(episodes["category"], CATEGORY_ORDER)
    tasks = (episodes[["task_id", "category"]].drop_duplicates("task_id")
             .assign(__c=lambda f: f["category"].map({c: i for i, c in enumerate(cats)}))
             .sort_values(["__c", "task_id"]))
    vals = episodes.assign(__v=episodes[value].astype(float) * (100.0 if percent else 1.0))
    pivot = (vals.pivot_table(index="task_id", columns="config", values="__v", aggfunc="mean")
             .reindex(index=tasks["task_id"], columns=configs))
    vmax = 100.0 if percent else max(1.0, float(np.nanmax(pivot.to_numpy(float))) if pivot.size else 1.0)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(max(4.0, 0.7 * len(configs) + 2.4), 0.17 * len(tasks) + 1.6))
        sns.heatmap(pivot.astype(float), vmin=0, vmax=vmax, cmap=BLUE_RAMP if percent else ORANGE_RAMP,
                    linewidths=0.5, linecolor=SURFACE, ax=ax,
                    cbar_kws={"label": cbar_label, "orientation": "horizontal", "pad": 0.08, "shrink": 0.8,
                              "aspect": 30, "location": "top"})
        ax.set_xticklabels([config_label(c, wrap=True) for c in configs], rotation=0)
        ax.set_yticks(np.arange(len(tasks)) + 0.5, tasks["task_id"], fontsize=5.5, rotation=0)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(length=0)
        bounds = np.flatnonzero(tasks["category"].to_numpy()[1:] != tasks["category"].to_numpy()[:-1]) + 1
        for b in bounds:
            ax.axhline(b, color=INK, linewidth=0.8)
        trans = blended_transform_factory(ax.transAxes, ax.transData)
        edges = [0, *bounds.tolist(), len(tasks)]
        for lo, hi in zip(edges[:-1], edges[1:]):
            ax.text(1.02, (lo + hi) / 2, str(tasks["category"].iloc[lo]), transform=trans, va="center",
                    ha="left", fontsize=7, color=INK2)
        return save(fig, out_dir, name)


def make_figures(tables: dict[str, pd.DataFrame], episodes: pd.DataFrame, attempts: pd.DataFrame,
                 out_dir: Path) -> list[Path]:
    """Every report figure; returns the written files."""
    if episodes.empty:
        return []
    _register(order_configs(episodes["config"]))
    paths = plot_completion(tables["main_results"], out_dir)
    paths += plot_category_heatmap(tables["per_category"], out_dir)
    paths += plot_error_stacks(tables["errors"], out_dir)
    paths += plot_cumulative_success(tables["cumulative_success"], tables["main_results"], out_dir)
    paths += plot_cost_vs_completion(tables["main_results"], tables["cost"], out_dir)
    paths += plot_failed_executions(tables["errors"], episodes, attempts, out_dir)
    paths += plot_task_heatmap(episodes, "failed_executions", out_dir, "failed_executions_by_task",
                               cbar_label="Failed executions per episode (mean over runs)", percent=False)
    paths += plot_task_heatmap(episodes, "success", out_dir, "success_by_task",
                               cbar_label="Success rate over runs (%)", percent=True)
    return paths

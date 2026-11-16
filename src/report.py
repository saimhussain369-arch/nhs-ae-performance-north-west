"""Charts, CSV extracts and the executive summary."""
from __future__ import annotations

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

import config

INK, MUTED, GRID = "#1f2d33", "#5b6b70", "#e3e8ea"
ENGLAND, REGION = "#8aa0a6", "#005eb8"   # NHS blue for the region
GOOD, BAD = "#2f8f74", "#c8553d"


def _style(ax, grid_axis="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _short(name: str) -> str:
    s = name.title()
    for a, b in [(" Nhs Foundation Trust", ""), (" Nhs Trust", ""), (" University Hospitals", " Univ. Hospitals"),
                 ("University Hospitals Of ", "UH "), (" Teaching Hospitals", " Teaching"), (" And ", " & ")]:
        s = s.replace(a, b)
    return s


def extracts(con: duckdb.DuckDBPyConnection) -> None:
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    for t in ("area_month", "trust_month", "trust_latest_quarter", "dq_summary"):
        con.sql(f"SELECT * FROM {t}").df().to_csv(config.OUTPUTS / f"{t}.csv", index=False)


def charts(con: duckdb.DuckDBPyConnection) -> None:
    config.IMAGES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titlesize": 12, "axes.titleweight": "bold"})
    area = con.sql("SELECT * FROM area_month ORDER BY month").df()
    area["month"] = pd.to_datetime(area["month"])

    # 1. four-hour performance against the planning targets
    fig, ax = plt.subplots(figsize=(8.5, 4), dpi=150)
    for name, colour, lw in (("England", ENGLAND, 2), (config.REGION_LABEL, REGION, 2.6)):
        d = area[area.area == name]
        ax.plot(d.month, d.pct_within_4h, color=colour, lw=lw, marker="o", ms=3.5, label=name)
        last = d.iloc[-1]
        ax.annotate(f"{last.pct_within_4h:.1f}%", (last.month, last.pct_within_4h), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=colour, fontweight="bold")
    for t in config.TARGETS:
        start, end = pd.Timestamp(t["from"] + "-01"), pd.Timestamp(t["to"] + "-01")
        start, end = max(start, area.month.min()), min(end, area.month.max())
        if start <= end:
            ax.hlines(t["value"], start, end, colors=INK, linestyles=(0, (4, 3)), lw=1.2)
            ax.text(start, t["value"] + 0.4, t["label"], fontsize=8, color=INK)
    lo = min(area.pct_within_4h.min(), 70) - 2
    ax.set_ylim(lo, 86)
    ax.set_ylabel("% seen within 4 hours", color=MUTED, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_title("A&E four-hour performance, all department types", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _style(ax)
    fig.tight_layout()
    fig.savefig(config.IMAGES / "four_hour_performance_trend.png")
    plt.close(fig)

    # 2. North West trusts, latest three months
    lq = con.sql("SELECT * FROM trust_latest_quarter ORDER BY pct_within_4h").df()
    latest = pd.to_datetime(con.sql("SELECT max(month) FROM ae_provider_month").fetchone()[0])
    first = latest - pd.DateOffset(months=2)
    target = next(t["value"] for t in config.TARGETS if t["from"] <= latest.strftime("%Y-%m") <= t["to"])
    fig, ax = plt.subplots(figsize=(8.5, max(4, 0.32 * len(lq) + 1.2)), dpi=150)
    colours = [GOOD if v >= target else REGION for v in lq.pct_within_4h]
    ax.barh([_short(n) for n in lq.org_name], lq.pct_within_4h, color=colours)
    for y, v in enumerate(lq.pct_within_4h):
        ax.text(v + 0.4, y, f"{v:.1f}%", va="center", fontsize=8, color=INK)
    ax.axvline(target, color=INK, ls=(0, (4, 3)), lw=1.2)
    ax.text(target + 0.3, len(lq) - 0.4, f"{target:.0f}% target", fontsize=8, color=INK)
    ax.set_xlim(max(0, lq.pct_within_4h.min() - 10), 100)
    ax.set_xlabel("% seen within 4 hours (all types)", color=MUTED, fontsize=9)
    ax.set_title(f"North West trusts with a major A&E, {first:%b} to {latest:%b %Y}", loc="left", color=INK)
    ax.tick_params(axis="y", labelsize=8)
    _style(ax, "x")
    fig.tight_layout()
    fig.savefig(config.IMAGES / "north_west_trusts_latest_quarter.png")
    plt.close(fig)

    # 3. twelve-hour waits from decision to admit
    nw = area[area.area == config.REGION_LABEL]
    fig, ax = plt.subplots(figsize=(8.5, 3.6), dpi=150)
    ax.bar(nw.month, nw.waits_12h_plus_from_decision_to_admit, width=20, color=BAD)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_ylabel("Patients", color=MUTED, fontsize=9)
    ax.set_title("North West: patients waiting 12+ hours from decision to admit", loc="left", color=INK)
    _style(ax)
    fig.tight_layout()
    fig.savefig(config.IMAGES / "north_west_12_hour_waits.png")
    plt.close(fig)


def summary(con: duckdb.DuckDBPyConnection) -> dict:
    area = con.sql("SELECT * FROM area_month ORDER BY month").df()
    area["month"] = pd.to_datetime(area["month"])
    latest = area.month.max()
    year_ago = latest - pd.DateOffset(years=1)
    eng = area[area.area == "England"].set_index("month")
    nw = area[area.area == config.REGION_LABEL].set_index("month")
    lq = con.sql("SELECT * FROM trust_latest_quarter ORDER BY pct_within_4h DESC").df()
    dq = con.sql("SELECT * FROM dq_summary").df()
    target = next(t["value"] for t in config.TARGETS if t["from"] <= latest.strftime("%Y-%m") <= t["to"])
    mar26 = pd.Timestamp("2026-03-01")

    facts = {
        "latest": latest, "nw_pct": nw.loc[latest, "pct_within_4h"], "eng_pct": eng.loc[latest, "pct_within_4h"],
        "nw_type1": nw.loc[latest, "pct_within_4h_type1"], "eng_type1": eng.loc[latest, "pct_within_4h_type1"],
        "nw_att": int(nw.loc[latest, "attendances"]), "target": target,
        "nw_12h": int(nw.loc[latest, "waits_12h_plus_from_decision_to_admit"]),
        "nw_12h_year_ago": int(nw.loc[year_ago, "waits_12h_plus_from_decision_to_admit"]) if year_ago in nw.index else None,
        "nw_pct_year_ago": nw.loc[year_ago, "pct_within_4h"] if year_ago in nw.index else None,
        "nw_mar26": nw.loc[mar26, "pct_within_4h"] if mar26 in nw.index else None,
        "eng_mar26": eng.loc[mar26, "pct_within_4h"] if mar26 in eng.index else None,
        "trusts": len(lq), "trusts_meeting": int((lq.pct_within_4h >= target).sum()),
        "best": lq.iloc[0], "worst": lq.iloc[-1],
        "months": len(nw), "first": area.month.min(),
        "dq_pass": int((dq.status == "Pass").sum()), "dq_total": len(dq),
        "rows": con.sql("SELECT count(*) FROM ae_provider_month").fetchone()[0],
    }

    f = facts
    gap = f["nw_pct"] - f["eng_pct"]
    lines = [
        "# Executive summary - North West A&E performance",
        "",
        f"*Source: NHS England, Monthly A&E Attendances and Emergency Admissions, {f['first']:%B %Y} to {f['latest']:%B %Y}. "
        "Generated by `src/report.py` - do not edit by hand.*",
        "",
        "## Headline",
        "",
        f"- In **{f['latest']:%B %Y}**, **{f['nw_pct']:.1f}%** of North West A&E patients were seen within four hours, "
        f"{'above' if gap >= 0 else 'below'} England's **{f['eng_pct']:.1f}%** "
        f"({abs(gap):.1f} points) and {'above' if f['nw_pct'] >= f['target'] else 'below'} the **{f['target']:.0f}%** 2026/27 target.",
        f"- In major (Type 1) emergency departments the figure was **{f['nw_type1']:.1f}%**, against **{f['eng_type1']:.1f}%** for England.",
    ]
    if f["nw_mar26"] is not None:
        lines.append(f"- In **March 2026**, the deadline for the 78% target, the North West reached **{f['nw_mar26']:.1f}%** "
                     f"(England **{f['eng_mar26']:.1f}%**).")
    if f["nw_12h_year_ago"] is not None:
        change = f["nw_12h"] - f["nw_12h_year_ago"]
        lines.append(f"- **{f['nw_12h']:,}** patients waited 12+ hours from a decision to admit, "
                     f"{'up' if change >= 0 else 'down'} **{abs(change):,}** on {f['latest'] - pd.DateOffset(years=1):%B %Y}.")
    lines += [
        f"- Over the latest three months, **{f['trusts_meeting']} of {f['trusts']}** North West trusts with a major A&E "
        f"met {f['target']:.0f}%. Highest: {_short(f['best'].org_name)} (**{f['best'].pct_within_4h:.1f}%**); "
        f"lowest: {_short(f['worst'].org_name)} (**{f['worst'].pct_within_4h:.1f}%**).",
        "",
        "## Data quality",
        "",
        f"**{f['dq_pass']} of {f['dq_total']}** checks passed across {f['rows']:,} provider-month rows.",
        "",
        "| Check | Result | Failures |",
        "|---|---|---:|",
    ]
    for _, r in dq.iterrows():
        lines.append(f"| {r.description} | {r.status} | {r.failures} |")
    lines += [
        "",
        "## Method",
        "",
        "- Four-hour performance = 1 − (attendances over 4 hours ÷ attendances), across all department types and including "
        "booked appointments, which is how NHS England calculates its headline figure.",
        "- North West = providers whose parent organisation is NHS England North West.",
        f"- The trust league table covers providers with at least {config.MIN_TYPE1_ATTENDANCES:,} Type 1 attendances in a month, "
        "pooled over the latest three months.",
        "- 12-hour waits are measured from the decision to admit (\"trolley waits\"), as published in the monthly file.",
        "",
    ]
    (config.DOCS / "executive_summary.md").write_text("\n".join(lines))
    return facts

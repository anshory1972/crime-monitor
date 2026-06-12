import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

IN_FILE  = r"C:\WORK\crime-monitor\data\gdelt_weekly_province.csv"
OUT_FILE = r"C:\WORK\crime-monitor\charts\chart_national_trend.png"

def main():
    df = pd.read_csv(IN_FILE, parse_dates=["week"])

    # ── National weekly series ────────────────────────────────────────────
    national = (
        df.groupby("week", sort=True)["total_intensity"]
        .sum()
        .reset_index()
        .rename(columns={"total_intensity": "intensity"})
    )
    national["rolling4"]  = national["intensity"].rolling(4, center=False).mean()
    grand_mean            = national["intensity"].mean()

    # ── Plot ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    # (1) Weekly bars — light gray background
    ax.bar(
        national["week"],
        national["intensity"],
        width=6,
        color="#CCCCCC",
        zorder=1,
        label="Weekly intensity",
    )

    # (2) 4-week rolling average — bold foreground line
    ax.plot(
        national["week"],
        national["rolling4"],
        color="#C0392B",
        linewidth=2.5,
        zorder=3,
        label="4-week rolling avg",
    )

    # (3) 24-month mean baseline
    ax.axhline(
        grand_mean,
        color="#2C3E50",
        linewidth=1.2,
        linestyle="--",
        zorder=2,
        label=f"24-month mean ({grand_mean:,.0f})",
    )

    # (4) X-axis — monthly labels
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=8.5)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlim(national["week"].min() - pd.Timedelta(days=7),
                national["week"].max() + pd.Timedelta(days=7))
    ax.set_ylim(0, national["intensity"].max() * 1.12)

    # (5) Labels and title
    ax.set_title(
        "Indonesia Crime Intensity Trend (GDELT-based, 2023–2025)",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlabel("Week", fontsize=10)
    ax.set_ylabel("Total Intensity\n(NumMentions × |GoldsteinScale|)", fontsize=10)

    ax.legend(frameon=True, fontsize=9, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E0E0E0", linewidth=0.7, zorder=0)

    fig.tight_layout()
    fig.savefig(OUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUT_FILE}")
    print(f"Weeks plotted : {len(national)}")
    print(f"24-month mean : {grand_mean:,.1f}")
    print(f"Peak week     : {national.loc[national['intensity'].idxmax(), 'week'].date()}  "
          f"({national['intensity'].max():,.1f})")

if __name__ == "__main__":
    main()

"""Small plotting helpers: consistent style, one place to save figures."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .config import FIGURES, TABLES  # noqa: E402

# IEEE two-column figure width is ~3.5 in; keep fonts readable at that size.
plt.rcParams.update({
    "figure.figsize": (3.5, 2.4), "figure.dpi": 150, "font.size": 8,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight",
})


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"{name}.{ext}")
    plt.close(fig)
    print(f"  figure -> results/figures/{name}.pdf")


def save_table(df, name: str, latex: bool = True) -> None:
    df.to_csv(TABLES / f"{name}.csv", index=False)
    if latex:
        (TABLES / f"{name}.tex").write_text(df.to_latex(index=False, float_format="%.2f"))
    print(f"  table  -> results/tables/{name}.csv")

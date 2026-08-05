import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger

from config import SETTINGS


def plot_signals(signals: pd.DataFrame, max_points: int = 400) -> None:
    if signals.empty:
        logger.warning("No signals available for plotting")
        return

    plot_data = sample_for_plot(signals, max_points)
    SETTINGS.plot_file.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(plot_data["timestamp"], plot_data["composite_signal"], color="#146C94", linewidth=1.8)
    ax.fill_between(
        plot_data["timestamp"],
        plot_data["composite_signal"] - plot_data["confidence"],
        plot_data["composite_signal"] + plot_data["confidence"],
        color="#AFD3E2",
        alpha=0.35,
    )
    ax.axhline(0, color="#444444", linewidth=0.8)
    ax.set_title("Indian Market Twitter Signal")
    ax.set_xlabel("Time")
    ax.set_ylabel("Composite signal")
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(SETTINGS.plot_file, dpi=140)
    plt.close(fig)
    logger.info("Saved signal plot to {}", SETTINGS.plot_file)


def sample_for_plot(data: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(data) <= max_points:
        return data
    step = max(1, len(data) // max_points)
    return data.iloc[::step].copy()

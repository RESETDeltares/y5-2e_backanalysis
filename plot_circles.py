import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Patch


def plot_moonshot_radial_chart(
    data,
    class_colors=None,
    moonshot_labels=None,
    ring_step=20,
    figsize=(10, 10),
    outer_radius=1.0,
    title=None,
    save_path=None,
):
    """
    Plot a radial moonshot chart with 5 sectors and multiple classes per sector.

    Parameters
    ----------
    data : dict
        Format:
        {
            "Moonshot 1": {"AI": 10, "IAP": 20, "FDR": 25, "Clean": 5},
            "Moonshot 2": {"AI": 30, "IAP": 40, "FDR": 15, "Clean": 25},
            ...
        }

    class_colors : dict, optional
        Example:
        {
            "AI": "#31C4F3",
            "IAP": "#4CAF50",
            "FDR": "#F4EA2A",
            "Clean": "#B85C6B",
        }

    moonshot_labels : list, optional
        Ordered list of moonshot names. If None, uses keys from `data`.

    ring_step : int
        Distance between rings in percent. Default = 20.

    figsize : tuple
        Figure size.

    outer_radius : float
        Radius corresponding to 100%.

    title : str, optional
        Figure title.

    save_path : str, optional
        If given, saves the figure to this path.
    """

    if class_colors is None:
        class_colors = {
            "AI": "#31C4F3",  # light blue
            "IAP": "#4CAF50",  # green
            "FDR": "#F4EA2A",  # yellow
            "Clean": "#B85C6B",  # dark pink / red
        }

    if moonshot_labels is None:
        moonshot_labels = list(data.keys())

    n_moonshots = len(moonshot_labels)
    if n_moonshots != 5:
        raise ValueError("This plot is designed for exactly 5 moonshots.")

    class_names = list(class_colors.keys())
    n_classes = len(class_names)

    # Geometry
    sector_width = 360 / n_moonshots
    angle_offset = 90  # start at top
    pad_fraction = 0.0  # no gap between moonshots
    sector_pad = sector_width * pad_fraction
    usable_sector_width = sector_width - sector_pad

    # Each class gets an equal angular slot inside each moonshot, no gap between classes
    class_slot_width = usable_sector_width / n_classes
    class_wedge_width = class_slot_width  # no padding between classes

    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"aspect": "equal"})

    # ---- Draw concentric rings ----
    ring_values = list(range(ring_step, 101, ring_step))
    for p in ring_values:
        r = (p / 100) * outer_radius
        circle = plt.Circle(
            (0, 0), r, fill=False, edgecolor="black", linewidth=1.0, alpha=0.25
        )
        ax.add_patch(circle)

    # ---- Draw main moonshot boundaries ----
    for i in range(n_moonshots):
        theta_deg = angle_offset - i * sector_width
        theta = np.deg2rad(theta_deg)
        x = [0, outer_radius * np.cos(theta)]
        y = [0, outer_radius * np.sin(theta)]
        ax.plot(x, y, color="black", linewidth=1.5)

    # Close last boundary
    theta_deg = angle_offset - n_moonshots * sector_width
    theta = np.deg2rad(theta_deg)
    ax.plot(
        [0, outer_radius * np.cos(theta)],
        [0, outer_radius * np.sin(theta)],
        color="black",
        linewidth=1.5,
    )

    # ---- Draw wedges for each moonshot and class ----
    for i, moonshot in enumerate(moonshot_labels):
        sector_start = angle_offset - i * sector_width
        sector_end = sector_start - sector_width

        # Use the middle part of the sector, leaving a bit of whitespace at edges
        usable_start = sector_start - sector_pad / 2
        usable_end = sector_end + sector_pad / 2

        # Because angles decrease clockwise, build class wedges from high angle to low angle
        current_start = usable_start

        for class_name in class_names:
            value = data[moonshot].get(class_name, 0)
            value = max(0, min(100, value))  # clamp to [0, 100]

            r = (value / 100) * outer_radius

            theta1 = current_start - class_wedge_width
            theta2 = current_start

            wedge = Wedge(
                center=(0, 0),
                r=r,
                theta1=theta1,
                theta2=theta2,
                facecolor=class_colors[class_name],
                edgecolor="none",
                alpha=0.9,
            )
            ax.add_patch(wedge)

            current_start -= class_slot_width

    # ---- Add moonshot labels ----
    label_radius = outer_radius * 1.08
    for i, moonshot in enumerate(moonshot_labels):
        mid_angle_deg = angle_offset - (i + 0.5) * sector_width
        mid_angle = np.deg2rad(mid_angle_deg)

        x = label_radius * np.cos(mid_angle)
        y = label_radius * np.sin(mid_angle)

        rotation = mid_angle_deg - 90
        rotation = rotation % 360  # normalize to [0, 360)
        if rotation > 180:
            rotation -= 360  # bring to (-180, 180]
        if rotation > 90:
            rotation -= 180
        elif rotation < -90:
            rotation += 180

        ax.text(
            x,
            y,
            moonshot,
            ha="center",
            va="center",
            rotation=rotation,
            rotation_mode="anchor",
            fontsize=12,
        )

    # ---- Legend ----
    legend_handles = [
        Patch(facecolor=class_colors[name], edgecolor="none", label=name)
        for name in class_names
    ]
    ax.legend(handles=legend_handles, loc="upper right", bbox_to_anchor=(1.25, 1.05))

    # ---- Final formatting ----
    margin = 1.25
    ax.set_xlim(-margin * outer_radius, margin * outer_radius)
    ax.set_ylim(-margin * outer_radius, margin * outer_radius)
    ax.axis("off")

    if title:
        ax.set_title(title, pad=20)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()


def plot_moonshot_grouped_bar(
    data,
    class_colors=None,
    moonshot_labels=None,
    figsize=(12, 6),
    title=None,
    save_path=None,
):
    """Grouped bar chart: one group per moonshot, one bar per class."""
    import matplotlib.pyplot as plt
    import numpy as np

    if moonshot_labels is None:
        moonshot_labels = list(data.keys())
    class_names = list(next(iter(data.values())).keys())

    if class_colors is None:
        cmap = plt.colormaps["viridis"]
        class_colors = {
            c: cmap(i / (len(class_names) - 1)) for i, c in enumerate(class_names)
        }

    n_moonshots = len(moonshot_labels)
    n_classes = len(class_names)
    x = np.arange(n_moonshots)
    bar_width = 0.8 / n_classes

    fig, ax = plt.subplots(figsize=figsize)

    for i, class_name in enumerate(class_names):
        values = [data[m].get(class_name, 0) for m in moonshot_labels]
        offset = (i - n_classes / 2 + 0.5) * bar_width
        ax.bar(
            x + offset,
            values,
            width=bar_width,
            label=class_name,
            color=class_colors[class_name],
            edgecolor="white",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(moonshot_labels, fontsize=11)
    ax.set_ylabel("Percentage (%)")
    ax.set_ylim(0, 105)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left")

    if title:
        ax.set_title(title, pad=14)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def plot_moonshot_heatmap(
    data,
    moonshot_labels=None,
    figsize=(9, 4),
    title=None,
    save_path=None,
):
    """Heatmap: moonshots on x-axis, classes on y-axis, color = percentage."""
    import matplotlib.pyplot as plt
    import numpy as np

    if moonshot_labels is None:
        moonshot_labels = list(data.keys())
    class_names = list(next(iter(data.values())).keys())

    matrix = np.array(
        [[data[m].get(c, 0) for m in moonshot_labels] for c in class_names],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=100)

    ax.set_xticks(range(len(moonshot_labels)))
    ax.set_xticklabels(moonshot_labels, fontsize=11)
    ax.set_yticks(range(len(class_names)))
    ax.set_yticklabels(class_names, fontsize=11)

    # Annotate each cell with its value
    for r in range(len(class_names)):
        for c in range(len(moonshot_labels)):
            val = matrix[r, c]
            text_color = "white" if val < 55 else "black"
            ax.text(
                c,
                r,
                f"{val:.0f}",
                ha="center",
                va="center",
                fontsize=11,
                color=text_color,
                fontweight="bold",
            )

    plt.colorbar(im, ax=ax, label="Percentage (%)")

    if title:
        ax.set_title(title, pad=14)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def plot_moonshot_stacked_hbar(
    data,
    moonshot_labels=None,
    figsize=(10, 5),
    title=None,
    save_path=None,
):
    """Stacked horizontal bar chart: one bar per class, stacked by moonshot share."""
    import matplotlib.pyplot as plt
    import numpy as np

    if moonshot_labels is None:
        moonshot_labels = list(data.keys())
    class_names = list(next(iter(data.values())).keys())
    n_moonshots = len(moonshot_labels)

    # Color each moonshot segment with viridis
    cmap = plt.colormaps["viridis"]
    moonshot_colors = [cmap(i / (n_moonshots - 1)) for i in range(n_moonshots)]

    fig, ax = plt.subplots(figsize=figsize)

    for ci, class_name in enumerate(class_names):
        left = 0.0
        for mi, moonshot in enumerate(moonshot_labels):
            val = data[moonshot].get(class_name, 0)
            bar = ax.barh(
                class_name,
                val,
                left=left,
                color=moonshot_colors[mi],
                edgecolor="white",
                linewidth=0.5,
                label=moonshot if ci == 0 else "_nolegend_",
            )
            if val > 3:
                ax.text(
                    left + val / 2,
                    ci,
                    f"{val:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if val < 55 else "black",
                    fontweight="bold",
                )
            left += val

    ax.set_xlim(0, 100)
    ax.set_xlabel("Percentage (%)")
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", title="Moonshot")

    if title:
        ax.set_title(title, pad=14)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    example_data = {
        "Moonshot 1": {"AI": 0, "IAP": 10, "FDR": 30, "Clean": 2},
        "Moonshot 2": {"AI": 15, "IAP": 20, "FDR": 55, "Clean": 20},
        "Moonshot 3": {"AI": 0, "IAP": 0, "FDR": 0, "Clean": 3},
        "Moonshot 4": {"AI": 0, "IAP": 20, "FDR": 0, "Clean": 0},
        "Moonshot 5": {"AI": 85, "IAP": 50, "FDR": 15, "Clean": 75},
    }

    class_colors = {
        "AI": "#440154",
        "IAP": "#31688e",
        "FDR": "#35b779",
        "Clean": "#fde725",
    }

    plot_moonshot_radial_chart(
        data=example_data,
        class_colors=class_colors,
        title="Moonshot Radial Chart",
        save_path="moonshot_radial_chart.png",
    )

    plot_moonshot_grouped_bar(
        data=example_data,
        class_colors=class_colors,
        title="Moonshot Grouped Bar Chart",
        save_path="moonshot_grouped_bar.png",
    )

    plot_moonshot_heatmap(
        data=example_data,
        title="Moonshot Heatmap",
        save_path="moonshot_heatmap.png",
    )

    plot_moonshot_stacked_hbar(
        data=example_data,
        title="Moonshot Stacked Horizontal Bar",
        save_path="moonshot_stacked_hbar.png",
    )

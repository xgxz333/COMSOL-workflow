from dataclasses import asdict, dataclass
import json
import os


class GeometryError(ValueError):
    pass


@dataclass(frozen=True)
class Rectangle:
    name: str
    material: str
    x0: float
    x1: float
    z0: float
    z1: float

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.z1 - self.z0


@dataclass(frozen=True)
class BilayerGeometry:
    design: dict
    domains: tuple
    boundaries: dict

    def to_dict(self):
        return {
            "design": self.design,
            "domains": [asdict(domain) for domain in self.domains],
            "boundaries": self.boundaries,
        }

    def save_json(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)


def _require_positive(design, key):
    value = float(design[key])
    if value <= 0:
        raise GeometryError(f"{key} must be positive, got {value}")
    return value


def build_geometry(design):
    period = _require_positive(design, "period_um")
    duty = float(design["duty_cycle"])
    if not 0.0 < duty < 1.0:
        raise GeometryError(f"duty_cycle must be between 0 and 1, got {duty}")

    si_h = _require_positive(design, "si_thickness_um")
    gap = _require_positive(design, "vertical_gap_um")
    pcm_h = _require_positive(design, "pcm_thickness_um")
    cap_h = _require_positive(design, "sio2_cap_thickness_um")
    clad_h = _require_positive(design, "cladding_um")
    pml_h = _require_positive(design, "pml_um")

    width = period * duty
    x_left, x_right = -period / 2.0, period / 2.0
    ridge_left, ridge_right = -width / 2.0, width / 2.0

    lower_top = -gap / 2.0
    lower_bottom = lower_top - si_h
    upper_bottom = gap / 2.0
    upper_top = upper_bottom + si_h
    pcm_top = upper_top + pcm_h
    cap_top = pcm_top + cap_h
    main_bottom = lower_bottom - clad_h
    main_top = cap_top + clad_h

    domains = (
        Rectangle("background", "background", x_left, x_right, main_bottom, main_top),
        Rectangle("bottom_pml", "background", x_left, x_right, main_bottom - pml_h, main_bottom),
        Rectangle("top_pml", "background", x_left, x_right, main_top, main_top + pml_h),
        Rectangle("lower_si_grating", "si", ridge_left, ridge_right, lower_bottom, lower_top),
        Rectangle("upper_si_grating", "si", ridge_left, ridge_right, upper_bottom, upper_top),
        Rectangle("top_sio2_left", "sio2", x_left, ridge_left, upper_top, cap_top),
        Rectangle("top_sio2_right", "sio2", ridge_right, x_right, upper_top, cap_top),
        Rectangle("top_sio2_over_pcm", "sio2", ridge_left, ridge_right, pcm_top, cap_top),
        Rectangle("upper_pcm_cap", "pcm", ridge_left, ridge_right, upper_top, pcm_top),
    )

    boundaries = {
        "periodic_left_x": x_left,
        "periodic_right_x": x_right,
        "power_bottom_z": main_bottom,
        "power_top_z": main_top,
        "pml_bottom_z": main_bottom - pml_h,
        "pml_top_z": main_top + pml_h,
    }
    return BilayerGeometry(dict(design), domains, boundaries)


def visualize_geometry(geometry, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle as PatchRectangle

    colors = {
        "background": "#eff6ff",
        "si": "#156f83",
        "sio2": "#bfd8ef",
        "pcm": "#e06b4f",
    }
    fig, ax = plt.subplots(figsize=(6.2, 7.2))
    for domain in geometry.domains:
        alpha = 0.30 if "pml" in domain.name else 0.9
        hatch = "//" if "pml" in domain.name else None
        patch = PatchRectangle(
            (domain.x0, domain.z0),
            domain.width,
            domain.height,
            facecolor=colors[domain.material],
            edgecolor="#273444",
            linewidth=1.0,
            hatch=hatch,
            alpha=alpha,
        )
        ax.add_patch(patch)
        if domain.name not in {"background", "bottom_pml", "top_pml"}:
            ax.text(
                (domain.x0 + domain.x1) / 2.0,
                (domain.z0 + domain.z1) / 2.0,
                domain.name,
                ha="center",
                va="center",
                fontsize=8,
            )

    x0 = -geometry.design["period_um"] / 2.0
    x1 = geometry.design["period_um"] / 2.0
    z0 = geometry.boundaries["pml_bottom_z"]
    z1 = geometry.boundaries["pml_top_z"]
    ax.set_xlim(x0 - 0.06, x1 + 0.06)
    ax.set_ylim(z0 - 0.06, z1 + 0.06)
    ax.set_aspect("equal")
    ax.set_xlabel("x [um], one period")
    ax.set_ylabel("z [um]")
    ax.set_title("2D bilayer grating unit cell")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)

"""Regenerate the user's three-panel Kalimantan map with revised typography.

All spatial data and polygon colors follow Make_Figure1_study_area.py. The
display geometry is simplified for plotting; these layers are not used for
the MODIS spatial analysis here. No field sites are depicted.
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch, Rectangle


import argparse
ap=argparse.ArgumentParser(); ap.add_argument("--raw",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
OUT = args.output / "figures"
OUT.mkdir(parents=True,exist_ok=True)


def features(paths, id_field=None):
    if isinstance(paths, Path):
        paths = [paths]
    by_id, collected = {}, []
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            rows = json.load(stream)["features"]
        if id_field:
            for row in rows:
                by_id[row["properties"][id_field]] = row
        else:
            collected.extend(rows)
    return list(by_id.values()) if id_field else collected


upload = args.raw
provinces = features(upload / "batas_5_provinsi_kalimantan.geojson")
peat = features(upload / "BIGID6 200", "objectid")
khg = features(sorted(upload.glob("ID37_offset_*.geojson")), "objectid_1")
feg = features(sorted(upload.glob("ID48_offset_*.geojson")), "objectid_1")
assert tuple(map(len, (provinces, peat, khg, feg))) == (5, 100, 101, 4359)
assert all("Gambut" in item["properties"]["landform"] for item in peat)


def rings(items, max_vertices=900):
    result = []
    for item in items:
        geom = item["geometry"]
        polygons = ([geom["coordinates"]] if geom["type"] == "Polygon"
                    else geom["coordinates"])
        for polygon in polygons:
            ring = np.asarray(polygon[0], dtype=float)
            stride = max(1, math.ceil(len(ring) / max_vertices))
            simple = ring[::stride]
            if len(simple) and not np.array_equal(simple[-1], ring[-1]):
                simple = np.vstack((simple, ring[-1]))
            if len(simple) >= 4:
                result.append(simple)
    return result


def fill(ax, items, color, alpha=1, zorder=2):
    ax.add_collection(PolyCollection(rings(items), closed=True,
                                     facecolors=color, edgecolors="none",
                                     alpha=alpha, zorder=zorder,
                                     rasterized=True))


def outlines(ax, items, width=.45):
    for ring in rings(items):
        ax.plot(ring[:, 0], ring[:, 1], color="#596f80",
                linewidth=width, zorder=5)


def setup(ax, with_axes=False):
    ax.set_xlim(108, 120)
    ax.set_ylim(-5, 5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_color("#b3c5cc")
        spine.set_linewidth(.72)
    if with_axes:
        ax.set_xticks([108, 111, 114, 117, 120])
        ax.set_yticks([-5, -2.5, 0, 2.5, 5])
        ax.tick_params(labelsize=11.5, colors="#3c5365", length=3,
                       pad=4, direction="out")
        ax.grid(color="#cbd4da", linewidth=.5, alpha=.65, zorder=0)
        ax.set_xlabel("Longitude (°E)", fontsize=12, labelpad=6,
                      color="#253e4d")
        ax.set_ylabel("Latitude (°)", fontsize=12, labelpad=6,
                      color="#253e4d")
    else:
        ax.set_xticks([])
        ax.set_yticks([])


plt.rcParams.update({"font.family": "DejaVu Sans",
                     "savefig.facecolor": "white"})
fig = plt.figure(figsize=(13.5, 8.05), facecolor="white")

# The figure follows the uploaded layout: one large map at left and two
# stacked map products at right. There are no titles above the three panels.
main = fig.add_axes([.087, .10, .575, .814])
setup(main, with_axes=True)
fill(main, peat, "#378970", alpha=.9)
outlines(main, provinces, width=.75)

for name, x, y in [
    ("West Kalimantan", 110.35, .9),
    ("Central Kalimantan", 112.9, -1.35),
    ("South Kalimantan", 115.25, -3.22),
    ("East Kalimantan", 116.55, .45),
    ("North Kalimantan", 116.45, 3.05),
]:
    label = main.text(x, y, name, fontsize=8.3, ha="center", va="center",
                      color="#20394c", zorder=8)
    label.set_path_effects([pe.withStroke(linewidth=2.5,
                                          foreground="white")])

main.annotate("N", xy=(108.75, 4.5), xytext=(108.75, 3.8),
              ha="center", va="bottom", fontsize=11, fontweight="bold",
              arrowprops={"arrowstyle": "-|>", "color": "#233d50",
                          "lw": 1.4}, zorder=11)

# Approximate 200 km east-west at the indicated reference latitude.
bar_y, bar_lon = -4.35, 109.15
half_lon = 100 / (111.31949 * math.cos(math.radians(bar_y)))
for step, color in ((0, "#24495b"), (1, "white")):
    main.add_patch(Rectangle((bar_lon + step * half_lon, bar_y),
                             half_lon, .085, facecolor=color,
                             edgecolor="#24495b", linewidth=.8, zorder=10))
for step, value in ((0, "0"), (1, "100"), (2, "200 km")):
    main.text(bar_lon + step * half_lon, bar_y - .12, value,
              fontsize=8.3, ha="center", va="top", color="#183848")

b = fig.add_axes([.683, .538, .268, .376])
setup(b)
fill(b, khg, "#5288ba", alpha=.84)
outlines(b, provinces, width=.5)

c = fig.add_axes([.683, .105, .268, .376])
setup(c)
fill(c, [x for x in feg if x["properties"]["tnh_gambut"] == "Non Gambut (Mineral)"],
     "#d5b07f", alpha=.94)
fill(c, [x for x in feg if x["properties"]["tnh_gambut"] == "Tanah Gambut"],
     "#a7506f", alpha=.9, zorder=3)
outlines(c, provinces, width=.5)

# Keep the legend in the southeast corner of the main panel, as uploaded.
legend = main.legend(handles=[
    Patch(facecolor="#378970", label="ID 6: mapped peatland"),
    Patch(facecolor="#5288ba", label="ID 37: hydrological unit"),
    Patch(facecolor="#a7506f", label="ID 48: peat soil"),
    Patch(facecolor="#d5b07f", label="ID 48: mineral soil"),
], loc="lower right", bbox_to_anchor=(.995, .018), frameon=True,
   facecolor="white", edgecolor="none", framealpha=.94,
   fontsize=8.0, handlelength=1.4, labelspacing=.65, borderpad=.5)
legend.set_zorder(20)

for fmt in ("png", "pdf"):
    target = OUT / f"Figure_1_Peatland_Map_Coverage.{fmt}"
    fig.savefig(target, dpi=300, bbox_inches="tight", pad_inches=.13)
    print(target, target.stat().st_size)

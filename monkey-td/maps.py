"""Ten playable maps: coarse polylines → densified waypoints (see path.densify)."""

from __future__ import annotations

from typing import Any

from config import PLAY_HEIGHT, PLAY_WIDTH
from path import densify

PW = float(PLAY_WIDTH)
PH = float(PLAY_HEIGHT)

# Coarse paths: start ~left, end ~right at base; stay inside margins.
MAP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": 0,
        "name": "Meadow",
        "subtitle": "Classic S-curve",
        "grass": (34, 72, 48),
        "coarse": [
            (24.0, 360.0),
            (130.0, 360.0),
            (210.0, 300.0),
            (280.0, 160.0),
            (400.0, 90.0),
            (520.0, 120.0),
            (620.0, 240.0),
            (700.0, 400.0),
            (620.0, 560.0),
            (480.0, 620.0),
            (360.0, 540.0),
            (420.0, 400.0),
            (560.0, 360.0),
            (720.0, 420.0),
            (820.0, 340.0),
            (PW - 36.0, 300.0),
        ],
    },
    {
        "id": 1,
        "name": "Riverbend",
        "subtitle": "Gentle bends",
        "grass": (32, 78, 52),
        "coarse": [
            (24.0, 420.0),
            (180.0, 420.0),
            (320.0, 300.0),
            (480.0, 280.0),
            (620.0, 380.0),
            (760.0, 320.0),
            (PW - 36.0, 340.0),
        ],
    },
    {
        "id": 2,
        "name": "Switchback",
        "subtitle": "Tight zig-zags",
        "grass": (28, 68, 44),
        "coarse": [
            (24.0, 520.0),
            (220.0, 520.0),
            (220.0, 180.0),
            (420.0, 180.0),
            (420.0, 580.0),
            (640.0, 580.0),
            (640.0, 220.0),
            (PW - 36.0, 220.0),
        ],
    },
    {
        "id": 3,
        "name": "Shoreline",
        "subtitle": "Low route along the edge",
        "grass": (40, 85, 58),
        "coarse": [
            (24.0, 620.0),
            (200.0, 620.0),
            (380.0, 480.0),
            (520.0, 620.0),
            (700.0, 500.0),
            (PW - 36.0, 520.0),
        ],
    },
    {
        "id": 4,
        "name": "Highlands",
        "subtitle": "High path, steep drops",
        "grass": (30, 65, 42),
        "coarse": [
            (24.0, 120.0),
            (200.0, 100.0),
            (400.0, 180.0),
            (560.0, 90.0),
            (700.0, 200.0),
            (820.0, 140.0),
            (PW - 36.0, 200.0),
        ],
    },
    {
        "id": 5,
        "name": "Sprint",
        "subtitle": "Short track — fast waves",
        "grass": (38, 70, 50),
        "coarse": [
            (24.0, PH / 2),
            (PW * 0.35, PH / 2),
            (PW * 0.65, PH / 2),
            (PW - 36.0, PH / 2),
        ],
    },
    {
        "id": 6,
        "name": "Marathon",
        "subtitle": "Long road — more time to shoot",
        "grass": (26, 62, 40),
        "coarse": [
            (24.0, 500.0),
            (120.0, 400.0),
            (220.0, 520.0),
            (340.0, 300.0),
            (460.0, 450.0),
            (520.0, 200.0),
            (640.0, 380.0),
            (720.0, 150.0),
            (780.0, 520.0),
            (640.0, 600.0),
            (500.0, 480.0),
            (420.0, 620.0),
            (300.0, 400.0),
            (200.0, 280.0),
            (400.0, 180.0),
            (600.0, 240.0),
            (PW - 36.0, 300.0),
        ],
    },
    {
        "id": 7,
        "name": "Corkscrew",
        "subtitle": "Spirals through the middle",
        "grass": (36, 68, 46),
        "coarse": [
            (24.0, 350.0),
            (200.0, 350.0),
            (200.0, 550.0),
            (500.0, 550.0),
            (500.0, 150.0),
            (750.0, 150.0),
            (750.0, 450.0),
            (400.0, 450.0),
            (400.0, 280.0),
            (PW - 36.0, 280.0),
        ],
    },
    {
        "id": 8,
        "name": "Ravine",
        "subtitle": "Deep V — choke in the center",
        "grass": (24, 58, 38),
        "coarse": [
            (24.0, 120.0),
            (300.0, 120.0),
            (440.0, 380.0),
            (520.0, 620.0),
            (640.0, 380.0),
            (780.0, 120.0),
            (PW - 36.0, 120.0),
        ],
    },
    {
        "id": 9,
        "name": "Twin Peaks",
        "subtitle": "Two humps before the base",
        "grass": (33, 75, 50),
        "coarse": [
            (24.0, 580.0),
            (180.0, 400.0),
            (340.0, 200.0),
            (500.0, 400.0),
            (660.0, 200.0),
            (820.0, 380.0),
            (PW - 36.0, 300.0),
        ],
    },
]


def map_count() -> int:
    return len(MAP_DEFINITIONS)


def build_waypoints(index: int) -> list[tuple[float, float]]:
    if index < 0 or index >= len(MAP_DEFINITIONS):
        index = 0
    coarse = MAP_DEFINITIONS[index]["coarse"]
    return densify(coarse, 7)


def map_grass(index: int) -> tuple[int, int, int]:
    if index < 0 or index >= len(MAP_DEFINITIONS):
        index = 0
    g = MAP_DEFINITIONS[index]["grass"]
    return int(g[0]), int(g[1]), int(g[2])

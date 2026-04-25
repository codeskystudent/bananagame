"""Polyline path: length, position at distance, distance from point to path."""

from __future__ import annotations

import math


def segment_lengths(waypoints: list[tuple[float, float]]) -> tuple[list[float], float]:
    segs: list[float] = []
    total = 0.0
    for i in range(len(waypoints) - 1):
        x0, y0 = waypoints[i]
        x1, y1 = waypoints[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        segs.append(ln)
        total += ln
    return segs, total


def pos_at_distance(waypoints: list[tuple[float, float]], dist: float) -> tuple[float, float, int]:
    """Return (x, y, segment_index). dist clamped to [0, total_length]."""
    segs, total = segment_lengths(waypoints)
    if total <= 0:
        return waypoints[0][0], waypoints[0][1], 0
    d = max(0.0, min(dist, total))
    i = 0
    while i < len(segs) and d > segs[i] + 1e-6:
        d -= segs[i]
        i += 1
    if i >= len(waypoints) - 1:
        return waypoints[-1][0], waypoints[-1][1], len(waypoints) - 2
    x0, y0 = waypoints[i]
    x1, y1 = waypoints[i + 1]
    ln = segs[i] if segs[i] > 1e-6 else 1.0
    t = d / ln
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * t
    return x, y, i


def dist_point_to_segment(
    px: float, py: float, x0: float, y0: float, x1: float, y1: float
) -> float:
    dx, dy = x1 - x0, y1 - y0
    ll = dx * dx + dy * dy
    if ll < 1e-12:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / ll))
    qx, qy = x0 + t * dx, y0 + t * dy
    return math.hypot(px - qx, py - qy)


def distance_point_to_path(px: float, py: float, waypoints: list[tuple[float, float]]) -> float:
    if len(waypoints) < 2:
        return math.hypot(px - waypoints[0][0], py - waypoints[0][1])
    best = float("inf")
    for i in range(len(waypoints) - 1):
        x0, y0 = waypoints[i]
        x1, y1 = waypoints[i + 1]
        d = dist_point_to_segment(px, py, x0, y0, x1, y1)
        best = min(best, d)
    return best


def total_length(waypoints: list[tuple[float, float]]) -> float:
    return segment_lengths(waypoints)[1]


def densify(waypoints: list[tuple[float, float]], steps_per_segment: int = 6) -> list[tuple[float, float]]:
    """Insert points along each segment for a smoother polyline (same route, finer samples)."""
    if len(waypoints) < 2:
        return list(waypoints)
    if steps_per_segment < 2:
        return list(waypoints)
    out: list[tuple[float, float]] = []
    for i in range(len(waypoints) - 1):
        x0, y0 = waypoints[i]
        x1, y1 = waypoints[i + 1]
        for j in range(steps_per_segment):
            t = j / steps_per_segment
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out.append(waypoints[-1])
    return out

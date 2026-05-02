"""HUD, sidebar, panels, fonts."""

from __future__ import annotations

import math
from collections.abc import Callable

import pygame

from config import (
    COLOR_HUD_BG,
    COLOR_TEXT,
    COLOR_UI_ACCENT,
    CROSSPATH_MAJOR_TIER,
    DIFFICULTY_SETTINGS,
    SNIPER_SPECIAL_TIER,
    TOWER_DAMAGE_TYPE,
    TOWER_SHOP_ORDER,
    CROSSPATH_OTHER_MAX,
    GLOBAL_UPGRADE_COST_MULT,
    GLOBAL_UPGRADES,
    MAX_PATH_TIER,
    PATH_LANE_NAMES,
    PLAY_HEIGHT,
    PLAY_WIDTH,
    SIDEBAR_WIDTH,
    TOWER_PATH_PALETTES,
    TOWER_PATH_UPGRADES,
    TOWER_TYPES,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from entities import Enemy, MonkeyTower
from maps import MAP_DEFINITIONS

# Sidebar layout — shared by drawing and hit-testing (game.handle_click).
SIDEBAR_PAD_X = 18
TOWER_ROW_HEIGHT = 64
TOWER_ROW_GAP = 14
TOWER_ROW_STEP = TOWER_ROW_HEIGHT + TOWER_ROW_GAP
TOWER_SHOP_TOP = 134

UPGRADE_PANEL_Y0 = 518
UPGRADE_ROW_HEIGHT = 80
UPGRADE_ROW_STEP = 92
UPGRADE_PARAGON_GAP = 16
_STATS_LINES = 5
# Tower stats block above path rows — keep draw + ``compute_upgrade_paths_row_y`` aligned.
_UPGRADE_STAT_TOP_PAD = 8
_UPGRADE_STAT_LINE_EXTRA = 8
_UPGRADE_STAT_GAP_BEFORE_PATHS = 22


def _upgrade_panel_stat_metrics(font_small: pygame.font.Font) -> tuple[int, int]:
    """Returns ``line_skip``, ``text_top`` (absolute Y for first stat line)."""
    line_skip = font_small.get_linesize() + _UPGRADE_STAT_LINE_EXTRA
    text_top = UPGRADE_PANEL_Y0 + _UPGRADE_STAT_TOP_PAD
    return line_skip, text_top


PATH_UPGRADE_STAT_LABEL: dict[str, str] = {
    "damage": "Damage",
    "range": "Range",
    "firerate": "Fire rate",
    "splash": "Splash",
    "slow": "Slow",
    "farm_mult": "Farm mult",
    "farm_mult_b": "Farm bonus",
    "farm_flat": "Farm flat",
}


def _rounded_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    *,
    border: tuple[int, int, int] | None = None,
    border_width: int = 1,
    border_radius: int = 0,
) -> None:
    pygame.draw.rect(screen, fill, rect, border_radius=border_radius)
    if border is not None:
        pygame.draw.rect(screen, border, rect, border_width, border_radius=border_radius)


def _draw_labeled_toggle_button_row(
    screen: pygame.Surface,
    font: pygame.font.Font,
    items: list[tuple[str, str]],
    rect_at_index: Callable[[int], pygame.Rect],
    selected_key: str,
) -> None:
    for i, (key, label) in enumerate(items):
        r = rect_at_index(i)
        sel = selected_key == key
        fill = (55, 85, 130) if sel else (42, 52, 68)
        stroke = COLOR_UI_ACCENT if sel else (70, 82, 100)
        _rounded_panel(screen, r, fill, border=stroke, border_width=2, border_radius=10)
        lx = r.x + (r.width - font.size(label)[0]) // 2
        ly = r.y + (r.height - font.get_height()) // 2
        draw_text(screen, font, label, lx, ly)


def format_path_upgrade_effect(stat: str, val: float) -> str:
    label = PATH_UPGRADE_STAT_LABEL.get(stat, stat)
    if stat == "farm_flat":
        return f"{label} +{int(val)} / tier"
    if stat == "slow":
        return f"{label} +{int(val * 100)}% / tier"
    return f"{label} +{val * 100:.1f}% / tier"


def tower_upgrade_stat_lines(tower: MonkeyTower) -> list[tuple[str, tuple[int, int, int]]]:
    """One text/colour pair per line; length must match ``_STATS_LINES``."""
    dp = tower.dominant_path()
    lane_of = {"a": 0, "b": 1, "c": 2}
    lane_label = PATH_LANE_NAMES[lane_of[dp]] if dp else "—"

    base = tower.base()
    dmg_pct = (
        max(0.0, (tower.effective_damage(0.0) / max(1.0, float(base["damage"])) - 1.0) * 100.0)
        if float(base["damage"]) > 0
        else 0.0
    )
    rng_pct = (
        max(0.0, (tower.effective_range(0.0) / max(1.0, float(base["range"])) - 1.0) * 100.0)
        if float(base["range"]) > 0
        else 0.0
    )
    fr_pct = max(0.0, (float(base["cooldown"]) / max(1.0, float(tower.effective_cooldown())) - 1.0) * 100.0)

    if tower.tower_type == "sniper":
        if tower.paragon:
            mods_txt = "Top: lead · Mid: camo · Bot: flying (Paragon)"
            mods_col: tuple[int, int, int] = (158, 208, 168)
        else:
            have = []
            if tower.tier_a >= SNIPER_SPECIAL_TIER:
                have.append("lead")
            if tower.tier_b >= SNIPER_SPECIAL_TIER:
                have.append("camo")
            if tower.tier_c >= SNIPER_SPECIAL_TIER:
                have.append("flying")
            if have:
                mods_txt = (
                    "Paths unlocked: "
                    + " · ".join(have)
                    + " · regen bloons: damaged by all (they heal over time)"
                )
                mods_col = (158, 208, 168)
            else:
                mods_txt = (
                    f"Each path adds one layer @ tier {SNIPER_SPECIAL_TIER}+ "
                    "(Top=lead · Mid=camo · Bot=flying)"
                )
                mods_col = (190, 175, 145)
    elif tower.tower_type == "village":
        mods_txt = (
            f"Middle t{SNIPER_SPECIAL_TIER}+: allies gain camo vision · "
            f"Bottom t{SNIPER_SPECIAL_TIER}+: allies +7% dmg vs regen (in aura)"
        )
        mods_col = (175, 195, 215)
    else:
        dt = TOWER_DAMAGE_TYPE.get(tower.tower_type, "sharp")
        lead_note = "explosive/plasma pop lead" if dt in ("explosive", "plasma") else "no lead pop (sharp/cold)"
        mods_txt = (
            f"{lead_note} · camo: Sniper mid or Village mid aura · "
            f"flying: Sniper bot · regen: always damaged (heals)"
        )
        mods_col = (150, 175, 195)

    return [
        (tower.display_name(), COLOR_TEXT),
        (
            f"{PATH_LANE_NAMES[0]}/{PATH_LANE_NAMES[1]}/{PATH_LANE_NAMES[2]}  ·  lead {lane_label}",
            (130, 165, 188),
        ),
        (
            f"Crosspath: one t{CROSSPATH_MAJOR_TIER}+ path, others ≤t{CROSSPATH_OTHER_MAX}",
            (110, 150, 175),
        ),
        (
            f"Upg bonus: dmg +{int(dmg_pct)}%  rng +{int(rng_pct)}%  fire +{int(fr_pct)}%",
            (150, 198, 220),
        ),
        ("Bloon handling: " + mods_txt, mods_col),
    ]


def _upgrade_row_fill(maxed: bool, locked: bool, can_buy: bool) -> tuple[int, int, int]:
    if locked:
        return (36, 34, 42)
    if not can_buy and not maxed:
        return (40, 36, 38)
    if can_buy or maxed:
        return (38, 48, 62)
    return (34, 38, 46)


def _draw_paragon_upgrade_slot(
    screen: pygame.Surface,
    font_small: pygame.font.Font,
    pr: pygame.Rect,
    tower: MonkeyTower,
    cash: int,
) -> None:
    if tower.paragon:
        _rounded_panel(screen, pr, (52, 44, 72), border=(210, 160, 255), border_width=2, border_radius=6)
        draw_text(screen, font_small, "PARAGON", pr.x + 10, pr.y + 10, (235, 215, 255))
        draw_text(screen, font_small, "Apex power — maxed", pr.x + 10, pr.y + 30, (175, 160, 195))
        return
    if tower.can_paragon():
        pc = tower.paragon_cost()
        can_p = pc is not None and cash >= pc
        fill = (48, 40, 78) if can_p else (36, 34, 42)
        stroke = (190, 130, 255) if can_p else (85, 72, 95)
        _rounded_panel(screen, pr, fill, border=stroke, border_width=2, border_radius=6)
        draw_text(screen, font_small, "[G] Paragon", pr.x + 10, pr.y + 10, (225, 195, 255))
        if pc is not None:
            draw_text(
                screen,
                font_small,
                f"${pc}",
                pr.x + 10,
                pr.y + 30,
                (210, 190, 235) if can_p else (145, 125, 155),
            )
        return
    _rounded_panel(screen, pr, (32, 34, 40), border=(55, 60, 70), border_radius=6)
    draw_text(
        screen,
        font_small,
        "Paragon: max paths (6/2/2)",
        pr.x + 10,
        pr.y + 18,
        (105, 115, 130),
    )


def compute_upgrade_paths_row_y(font_small: pygame.font.Font) -> int:
    """Y of the first path upgrade row; must match ``draw_upgrade_panel``."""
    line_skip, text_top = _upgrade_panel_stat_metrics(font_small)
    return text_top + _STATS_LINES * line_skip + _UPGRADE_STAT_GAP_BEFORE_PATHS


def difficulty_button_rect(index: int) -> pygame.Rect:
    """Easy / Medium / Hard row above bottom margin."""
    w = 220
    h = 52
    gap = 18
    total = 4 * w + 3 * gap
    x0 = (WINDOW_WIDTH - total) // 2
    y = WINDOW_HEIGHT - 92
    return pygame.Rect(x0 + index * (w + gap), y, w, h)


def mode_button_rect(index: int) -> pygame.Rect:
    """Mode row: Normal / Sandbox above difficulty buttons."""
    w = 236
    h = 46
    gap = 18
    total = 2 * w + gap
    x0 = (WINDOW_WIDTH - total) // 2
    y = WINDOW_HEIGHT - 156
    return pygame.Rect(x0 + index * (w + gap), y, w, h)


def map_button_rect(index: int) -> pygame.Rect:
    """Full-window map picker: 2 columns × 5 rows."""
    cols = 2
    pad = 34
    bw = (WINDOW_WIDTH - pad * 3) // 2
    bh = 78
    row = index // cols
    col = index % cols
    x = pad + col * (bw + pad)
    y = 108 + row * (bh + 16)
    return pygame.Rect(x, y, bw, bh)


def draw_map_select(
    screen: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    selected_difficulty: str,
    selected_mode: str,
) -> None:
    screen.fill((22, 28, 38))
    draw_text(screen, font_title, "Choose a map", 44, 30, COLOR_UI_ACCENT)
    draw_text(
        screen,
        font_small,
        "Pick difficulty, then a map  ·  Camo / Lead / Fortified / Regen bloons appear in later waves",
        44,
        60,
        (150, 165, 185),
    )
    for i, m in enumerate(MAP_DEFINITIONS):
        r = map_button_rect(i)
        g = m["grass"]
        edge = _lerp_color(g, (255, 255, 255), 0.15)
        _rounded_panel(screen, r, (38, 46, 58), border=edge, border_width=2, border_radius=10)
        preview = pygame.Surface((40, 40))
        preview.fill(g)
        screen.blit(preview, (r.x + 10, r.y + 11))
        draw_text(screen, font, m["name"], r.x + 62, r.y + 14)
        draw_text(screen, font_small, m["subtitle"], r.x + 62, r.y + 42, (170, 185, 200))

    diff_items = [
        (dk, str(DIFFICULTY_SETTINGS[dk]["label"]))
        for dk in ("easy", "medium", "hard", "impossible")
    ]
    _draw_labeled_toggle_button_row(screen, font, diff_items, difficulty_button_rect, selected_difficulty)
    mode_items = [("normal", "Normal"), ("sandbox", "Sandbox")]
    _draw_labeled_toggle_button_row(screen, font, mode_items, mode_button_rect, selected_mode)
    draw_text(
        screen,
        font_small,
        "[1] [2] [3] [4] difficulty  ·  [M] mode  ·  [R] title  ·  Esc quit",
        44,
        WINDOW_HEIGHT - 30,
        (130, 145, 165),
    )


def init_fonts() -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    pygame.font.init()
    s = max(1.0, min(1.35, WINDOW_HEIGHT / 768.0))
    return (
        pygame.font.SysFont("segoeui", int(18 * s)),
        pygame.font.SysFont("segoeui", int(14 * s)),
        pygame.font.SysFont("segoeui", int(22 * s), bold=True),
    )


def _lerp_color(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _tower_body_color(base: tuple[int, int, int], visual_tier: int) -> tuple[int, int, int]:
    gold = (255, 228, 140)
    return _lerp_color(base, gold, 0.055 * min(MAX_PATH_TIER, visual_tier))


def _dominant_path_from_tiers(ta: int, tb: int, tc: int) -> tuple[str | None, int]:
    m = max(ta, tb, tc)
    if m == 0:
        return None, 0
    for path, t in (("a", ta), ("b", tb), ("c", tc)):
        if t == m:
            return path, m
    return None, 0


def _path_body_accent_for_tiers(
    tower_key: str,
    ta: int,
    tb: int,
    tc: int,
) -> tuple[tuple[int, int, int], tuple[int, int, int], str | None, int]:
    base_col = TOWER_TYPES[tower_key]["color"]
    dp, dt = _dominant_path_from_tiers(ta, tb, tc)
    if dp is None:
        vt = max(ta, tb, tc)
        body = _tower_body_color(base_col, vt)
        accent = _lerp_color((200, 175, 90), (255, 220, 120), 0.12 * min(MAX_PATH_TIER, vt))
        return body, accent, None, 0
    pal_body, pal_accent = TOWER_PATH_PALETTES[tower_key][dp]
    blend = min(1.0, 0.26 + 0.11 * (dt - 1))
    body = _lerp_color(base_col, pal_body, blend)
    accent = _lerp_color(base_col, pal_accent, min(1.0, blend + 0.12))
    return body, accent, dp, dt


def _draw_tower_base_shape(
    screen: pygame.Surface,
    cx: int,
    cy: int,
    radius: int,
    tower_key: str,
    body: tuple[int, int, int],
    accent: tuple[int, int, int],
) -> None:
    """Distinct silhouette per tower type (before path-upgrade overlays)."""
    r = max(6, radius)
    shx, shy = cx + 1, cy + 2
    if tower_key == "dart":
        pygame.draw.circle(screen, (18, 24, 20), (shx, shy), r + 1)
        pygame.draw.circle(screen, body, (cx, cy), r)
        tip = max(6, r // 2 + 4)
        pygame.draw.polygon(
            screen,
            accent,
            ((cx + r - 3, cy - 4), (cx + r + tip, cy), (cx + r - 3, cy + 4)),
        )
    elif tower_key == "cannon":
        ew, eh = 2 * r, r + r // 2 + 2
        pygame.draw.ellipse(screen, (18, 24, 20), (cx - r - 1, cy - eh // 2 + 1, ew + 2, eh + 2))
        pygame.draw.ellipse(screen, body, (cx - r, cy - eh // 2, ew, eh))
        tr = max(3, r // 5)
        pygame.draw.circle(screen, _lerp_color(body, (35, 30, 28), 0.35), (cx - r // 2, cy + eh // 2 - tr), tr)
        pygame.draw.circle(screen, _lerp_color(body, (35, 30, 28), 0.35), (cx + r // 2, cy + eh // 2 - tr), tr)
        br = max(6, r // 2)
        pygame.draw.rect(screen, accent, (cx + r - 6, cy - br // 2, br + 4, br), border_radius=3)
    elif tower_key == "ice":
        pts: list[tuple[float, float]] = []
        for i in range(6):
            ang = math.pi / 2 + i * math.pi / 3
            pts.append((cx + r * math.cos(ang), cy + r * 0.88 * math.sin(ang)))
        pts_i = [(int(p[0]), int(p[1])) for p in pts]
        pygame.draw.polygon(screen, (18, 24, 20), [(p[0] + 1, p[1] + 2) for p in pts_i])
        pygame.draw.polygon(screen, body, pts_i)
        pygame.draw.polygon(screen, accent, pts_i, 2)
    elif tower_key == "sniper":
        w = max(10, r)
        h = max(20, int(r * 2.1))
        pygame.draw.ellipse(screen, (18, 24, 20), (cx - w // 2 + 1, cy - h // 2 + 2, w + 2, h + 2))
        pygame.draw.ellipse(screen, body, (cx - w // 2, cy - h // 2, w, h))
        pygame.draw.line(
            screen,
            accent,
            (cx + w // 2 - 2, cy - h // 5),
            (cx + w // 2 + r + 8, cy - h // 5),
            max(2, r // 7),
        )
        pygame.draw.circle(screen, (25, 35, 32), (cx + w // 2 + r + 6, cy - h // 5), max(4, r // 5))
    elif tower_key == "boom":
        pygame.draw.circle(screen, (18, 24, 20), (shx, shy), r + 1)
        pygame.draw.circle(screen, body, (cx, cy), r)
        arc_rect = pygame.Rect(cx - r - 4, cy - r - 2, (r + 4) * 2, (r + 4) * 2)
        pygame.draw.arc(screen, accent, arc_rect, 0.35, 2.25, max(2, r // 6))
        pygame.draw.arc(
            screen,
            _lerp_color(accent, body, 0.45),
            arc_rect.inflate(-6, -6),
            0.45,
            2.15,
            2,
        )
    elif tower_key == "farm":
        bw, bh = 2 * r, int(r * 1.15)
        top = cy - bh // 4
        pygame.draw.rect(screen, (18, 24, 20), (cx - bw // 2 + 1, top + 2, bw + 2, bh))
        pygame.draw.rect(screen, body, (cx - bw // 2, top, bw, bh), border_radius=3)
        peak = top - max(10, r // 2)
        pygame.draw.polygon(
            screen,
            accent,
            ((cx - bw // 2 - 2, top), (cx + bw // 2 + 2, top), (cx, peak)),
        )
        pygame.draw.rect(screen, _lerp_color(body, (40, 35, 30), 0.3), (cx - 5, cy + 2, 10, 8))
    elif tower_key == "village":
        bw, bh = int(r * 2.1), int(r * 1.45)
        top = cy - bh // 3
        pygame.draw.rect(screen, (18, 24, 20), (cx - bw // 2 + 1, top + 2, bw, bh))
        pygame.draw.rect(screen, body, (cx - bw // 2, top, bw, bh), border_radius=4)
        peak = top - max(8, r // 2)
        pygame.draw.polygon(
            screen,
            accent,
            ((cx - bw // 2 - 2, top), (cx + bw // 2 + 2, top), (cx, peak)),
        )
        pygame.draw.rect(screen, _lerp_color(accent, (255, 255, 255), 0.25), (cx - 4, top + bh // 3, 8, 7))
    elif tower_key == "workshop":
        bw, bh = int(r * 2.05), int(r * 1.5)
        pygame.draw.rect(screen, (18, 24, 20), (cx - bw // 2 + 1, cy - bh // 2 + 2, bw, bh))
        pygame.draw.rect(screen, body, (cx - bw // 2, cy - bh // 2, bw, bh), border_radius=3)
        pygame.draw.rect(screen, accent, (cx - bw // 2 + 4, cy - bh // 2 + 4, bw - 8, bh // 3), border_radius=2)
        pygame.draw.circle(screen, accent, (cx - bw // 3, cy + bh // 4), max(3, r // 6))
        pygame.draw.circle(screen, accent, (cx + bw // 3, cy + bh // 4), max(3, r // 6))
    elif tower_key == "super":
        pygame.draw.circle(screen, (18, 24, 20), (shx, shy), r + 1)
        pygame.draw.circle(screen, body, (cx, cy), r)
        cape_w = max(14, r + r // 2)
        pygame.draw.polygon(
            screen,
            _lerp_color(body, (180, 60, 70), 0.35),
            (
                (cx - cape_w // 2, cy - r // 2),
                (cx + cape_w // 2, cy - r // 2),
                (cx + r // 2, cy + r + 4),
                (cx - r // 2, cy + r + 4),
            ),
        )
        pygame.draw.arc(
            screen,
            accent,
            pygame.Rect(cx - r - 2, cy - r - 4, (r + 2) * 2, (r + 2) * 2),
            3.6,
            5.9,
            max(2, r // 7),
        )
    else:
        pygame.draw.circle(screen, (18, 24, 20), (shx, shy), r + 1)
        pygame.draw.circle(screen, body, (cx, cy), r)


def _draw_tower_face(
    screen: pygame.Surface,
    cx: int,
    cy: int,
    radius: int,
    tower_key: str,
    vt: int,
) -> None:
    r = max(6, radius)
    dim = 0.08 * min(MAX_PATH_TIER, max(0, vt))
    eye = _lerp_color((40, 30, 20), (30, 24, 18), dim)
    er = max(2, r // 5)
    if tower_key == "dart":
        pygame.draw.circle(screen, eye, (cx - r // 3, cy - r // 4), er)
        pygame.draw.circle(screen, eye, (cx + r // 3, cy - r // 4), er)
    elif tower_key == "cannon":
        pygame.draw.rect(screen, eye, (cx - r // 3, cy - r // 3, 2 * r // 3, max(3, r // 6)))
    elif tower_key == "ice":
        pygame.draw.circle(screen, (190, 235, 255), (cx, cy - r // 5), max(3, r // 6))
        pygame.draw.circle(screen, (255, 255, 255), (cx - 1, cy - r // 5 - 1), 2)
    elif tower_key == "sniper":
        pygame.draw.circle(screen, (45, 55, 50), (cx - r // 10, cy - r // 8), max(5, r // 3))
        pygame.draw.circle(screen, (160, 210, 190), (cx - r // 10, cy - r // 8), max(2, r // 6))
    elif tower_key == "boom":
        pygame.draw.circle(screen, eye, (cx - r // 4, cy - r // 5), er - 1)
        pygame.draw.circle(screen, eye, (cx + r // 4, cy - r // 5), er - 1)
    elif tower_key == "farm":
        pygame.draw.line(screen, (55, 45, 38), (cx - 5, cy - r // 5), (cx + 5, cy - r // 5), 2)
        pygame.draw.line(screen, (55, 45, 38), (cx, cy - r // 5 - 5), (cx, cy - r // 5 + 5), 2)
    elif tower_key == "village":
        pygame.draw.circle(screen, eye, (cx - r // 3, cy - r // 5), er)
        pygame.draw.circle(screen, eye, (cx + r // 3, cy - r // 5), er)
        pygame.draw.arc(screen, (90, 120, 90), (cx - r // 2, cy, r, r // 2), 0.1, 3.0, 2)
    elif tower_key == "workshop":
        pygame.draw.rect(screen, (60, 75, 85), (cx - r // 2, cy - r // 3, r, r // 2), border_radius=2)
        pygame.draw.circle(screen, eye, (cx - r // 4, cy - r // 6), er - 1)
        pygame.draw.circle(screen, eye, (cx + r // 4, cy - r // 6), er - 1)
    elif tower_key == "super":
        pygame.draw.circle(screen, (95, 175, 255), (cx - r // 4, cy - r // 5), max(3, r // 5))
        pygame.draw.circle(screen, (95, 175, 255), (cx + r // 4, cy - r // 5), max(3, r // 5))
        pygame.draw.circle(screen, (255, 255, 255), (cx - r // 4 - 1, cy - r // 5 - 1), 2)
        pygame.draw.circle(screen, (255, 255, 255), (cx + r // 4 - 1, cy - r // 5 - 1), 2)
    else:
        pygame.draw.circle(screen, eye, (cx - r // 3, cy - r // 4), er)
        pygame.draw.circle(screen, eye, (cx + r // 3, cy - r // 4), er)


def _draw_path_silhouette(
    screen: pygame.Surface,
    cx: int,
    cy: int,
    radius: int,
    path_key: str,
    dt: int,
    accent: tuple[int, int, int],
) -> None:
    """BTD-style path identity: different shapes for Top / Middle / Bottom paths."""
    if dt < 1:
        return
    r = max(8, radius)
    if path_key == "a":
        # Damage path: forward spikes / plates
        n = min(dt, 6)
        h = 4 + min(n, 4) * 2
        for i in range(n):
            ox = (i - (n - 1) / 2) * (r // 2 + 2)
            tip = (cx + int(ox), cy - r - h - i)
            left = (cx + int(ox) - 5, cy - r - 2)
            right = (cx + int(ox) + 5, cy - r - 2)
            pygame.draw.polygon(screen, accent, (tip, left, right))
        if dt >= 3:
            pygame.draw.circle(screen, accent, (cx, cy - r - 6), 4)
        if dt >= 5:
            pygame.draw.rect(
                screen,
                _lerp_color(accent, (255, 255, 255), 0.25),
                (cx - 4, cy - r - 12, 8, 6),
            )
    elif path_key == "b":
        # Range path: optic / wide sight
        lw = max(1, min(4, 1 + dt // 2))
        pygame.draw.line(screen, accent, (cx - r - 4, cy - r - 2), (cx + r + 4, cy - r - 2), lw)
        gr = 3 + min(dt, 4)
        pygame.draw.circle(screen, accent, (cx - max(6, r // 2), cy - r - 4), gr, 2)
        pygame.draw.circle(screen, accent, (cx + max(6, r // 2), cy - r - 4), gr, 2)
        if dt >= 3:
            arc_r = pygame.Rect(cx - r - 8, cy - r - 18, (r + 8) * 2, 24)
            pygame.draw.arc(
                screen,
                _lerp_color(accent, (255, 255, 255), 0.35),
                arc_r,
                math.pi * 1.15,
                math.pi * 1.85,
                2,
            )
        if dt >= 5:
            pygame.draw.line(
                screen,
                accent,
                (cx - r - 6, cy - r - 8),
                (cx + r + 6, cy - r - 8),
                1,
            )
    else:
        # Speed path: motion streaks / satellites
        for i in range(min(dt, 6)):
            pygame.draw.circle(
                screen,
                _lerp_color(accent, (255, 255, 200), 0.2 * i),
                (cx - r - 6 - i * 3, cy - 4 + i * 2),
                3 + i,
                1,
            )
            pygame.draw.circle(
                screen,
                accent,
                (cx + r + 5 + i * 2, cy + 2 - i),
                2 + i,
                1,
            )


def _draw_path_outfit(
    screen: pygame.Surface,
    cx: int,
    cy: int,
    radius: int,
    tower_key: str,
    path_key: str,
    dt: int,
    accent: tuple[int, int, int],
) -> None:
    """Tower-specific costume overlays per dominant path (A/B/C)."""
    if dt < 1:
        return
    r = max(8, radius)
    bright = _lerp_color(accent, (255, 255, 255), 0.25)
    dark = _lerp_color(accent, (28, 26, 24), 0.35)
    core = _lerp_color(accent, (255, 240, 180), 0.45)
    # Tier intensity affects outfit complexity and line thickness.
    thick = 2 if dt >= 4 else 1

    if tower_key == "dart":
        if path_key == "a":
            # Damage outfit: plated helmet + shoulder pads
            pygame.draw.polygon(screen, bright, ((cx - 10, cy - r + 5), (cx, cy - r - 10), (cx + 10, cy - r + 5)))
            pygame.draw.rect(screen, dark, (cx - 12, cy - 2, 6, 8), border_radius=2)
            pygame.draw.rect(screen, dark, (cx + 6, cy - 2, 6, 8), border_radius=2)
        elif path_key == "b":
            # Vision outfit: goggles + lens mount
            pygame.draw.rect(screen, bright, (cx - 9, cy - 4, 18, 7), border_radius=3)
            pygame.draw.circle(screen, core, (cx - 4, cy - 1), 2)
            pygame.draw.circle(screen, core, (cx + 4, cy - 1), 2)
            pygame.draw.line(screen, bright, (cx, cy - r + 2), (cx, cy - 8), thick)
        else:
            # Speed outfit: scarf trails
            pygame.draw.arc(screen, bright, (cx - r - 8, cy - r - 6, 2 * r + 16, 2 * r + 12), 0.25, 2.85, thick)
            pygame.draw.arc(screen, core, (cx - r - 4, cy - r - 2, 2 * r + 8, 2 * r + 4), 0.4, 2.7, 1)
    elif tower_key == "cannon":
        if path_key == "a":
            # Siege outfit: reinforced barrel and braces
            pygame.draw.rect(screen, dark, (cx + r - 4, cy - 5, 14, 10), border_radius=2)
            pygame.draw.rect(screen, bright, (cx - r + 1, cy + 4, 7, 4), border_radius=1)
            pygame.draw.rect(screen, bright, (cx + r - 8, cy + 4, 7, 4), border_radius=1)
        elif path_key == "b":
            # Artillery outfit: range ring + calibrator
            pygame.draw.circle(screen, bright, (cx, cy), max(7, r // 2), thick)
            pygame.draw.circle(screen, core, (cx, cy), max(3, r // 5))
        else:
            # Reload outfit: ammo belt
            pygame.draw.rect(screen, dark, (cx - r // 2 - 2, cy - r // 2 - 3, r + 4, 6), border_radius=2)
            pygame.draw.line(screen, core, (cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), 1)
    elif tower_key == "ice":
        if path_key == "a":
            # Frost crown
            pygame.draw.polygon(screen, bright, ((cx - 8, cy - r), (cx - 2, cy - r - 10), (cx + 2, cy - r - 10), (cx + 8, cy - r)))
            pygame.draw.circle(screen, core, (cx, cy - r - 6), 2)
        elif path_key == "b":
            # Cryo visor
            pygame.draw.rect(screen, bright, (cx - 9, cy - 5, 18, 7), border_radius=3)
            pygame.draw.line(screen, core, (cx - 7, cy - 2), (cx + 7, cy - 2), 1)
        else:
            # Shard mantle
            pygame.draw.polygon(screen, bright, ((cx - r + 3, cy + 2), (cx, cy + r // 2 + 5), (cx + r - 3, cy + 2)), 0)
    elif tower_key == "sniper":
        if path_key == "a":
            # Marksman helmet
            pygame.draw.rect(screen, bright, (cx - 10, cy - r - 1, 20, 5), border_radius=2)
            pygame.draw.line(screen, dark, (cx, cy - r - 1), (cx, cy - 9), thick)
        elif path_key == "b":
            # Long-range optic array
            pygame.draw.circle(screen, bright, (cx, cy - r + 1), 7, thick)
            pygame.draw.circle(screen, core, (cx, cy - r + 1), 3)
            pygame.draw.line(screen, bright, (cx - 12, cy - r + 1), (cx + 12, cy - r + 1), 1)
        else:
            # Rapid-fire sling rig
            pygame.draw.line(screen, bright, (cx - 7, cy + r - 3), (cx + 10, cy + r - 8), thick)
            pygame.draw.circle(screen, core, (cx + 12, cy + r - 9), 2)
    elif tower_key == "boom":
        if path_key == "a":
            # Glaive crest
            pygame.draw.polygon(screen, bright, ((cx - 9, cy - r + 5), (cx, cy - r - 8), (cx + 9, cy - r + 5)))
            pygame.draw.circle(screen, core, (cx, cy - r + 1), 2)
        elif path_key == "b":
            # Arc guide ring
            pygame.draw.circle(screen, bright, (cx, cy), r + 4, 1)
            pygame.draw.arc(screen, core, (cx - r - 7, cy - r - 7, 2 * r + 14, 2 * r + 14), 3.8, 5.6, thick)
        else:
            # Velocity fins
            pygame.draw.arc(screen, bright, (cx - r - 8, cy - r - 6, 2 * r + 16, 2 * r + 12), 3.3, 5.6, thick)
            pygame.draw.line(screen, core, (cx - r - 2, cy + 2), (cx + r + 3, cy - 2), 1)
    elif tower_key == "farm":
        if path_key == "a":
            # Harvest armor
            pygame.draw.rect(screen, bright, (cx - 9, cy - 2, 18, 9), border_radius=2)
            pygame.draw.line(screen, dark, (cx - 7, cy + 2), (cx + 7, cy + 2), 1)
        elif path_key == "b":
            # Fertility beacon
            pygame.draw.circle(screen, bright, (cx, cy - 4), 6, thick)
            pygame.draw.circle(screen, core, (cx, cy - 4), 2)
        else:
            # Storage belt
            pygame.draw.line(screen, bright, (cx - 10, cy + 5), (cx + 10, cy + 5), thick)
            pygame.draw.rect(screen, core, (cx - 4, cy + 3, 8, 4), border_radius=1)
    elif tower_key == "village":
        if path_key == "a":
            # Bannered battlement
            pygame.draw.rect(screen, bright, (cx - 7, cy - r + 2, 14, 6), border_radius=2)
            pygame.draw.polygon(screen, core, ((cx + 7, cy - r + 2), (cx + 13, cy - r + 4), (cx + 7, cy - r + 6)))
        elif path_key == "b":
            # Signal dish
            pygame.draw.circle(screen, bright, (cx, cy - r + 3), 7, thick)
            pygame.draw.line(screen, core, (cx, cy - r + 3), (cx, cy - r + 9), 1)
        else:
            # Logistics stripe
            pygame.draw.line(screen, bright, (cx - 8, cy + r - 3), (cx + 8, cy + r - 3), thick)
            pygame.draw.line(screen, core, (cx - 8, cy + r - 6), (cx + 8, cy + r - 6), 1)
    elif tower_key == "workshop":
        if path_key == "a":
            # Power saw helm
            pygame.draw.polygon(screen, bright, ((cx - 9, cy - r + 5), (cx, cy - r - 7), (cx + 9, cy - r + 5)))
            pygame.draw.circle(screen, core, (cx, cy - r), 2)
        elif path_key == "b":
            # Sensor rig
            pygame.draw.circle(screen, bright, (cx, cy - r + 2), 6, thick)
            pygame.draw.line(screen, core, (cx - 8, cy - r + 2), (cx + 8, cy - r + 2), 1)
        else:
            # Conveyor pack
            pygame.draw.rect(screen, bright, (cx - 9, cy + r - 8, 18, 6), border_radius=2)
            pygame.draw.rect(screen, core, (cx - 4, cy + r - 7, 8, 4), border_radius=1)
    elif tower_key == "super":
        if path_key == "a":
            # Crowned battle helm
            pygame.draw.polygon(screen, bright, ((cx - 10, cy - r + 5), (cx, cy - r - 10), (cx + 10, cy - r + 5)))
            pygame.draw.circle(screen, core, (cx, cy - r - 3), 2)
        elif path_key == "b":
            # Oracle halo
            pygame.draw.circle(screen, bright, (cx, cy - r + 2), 8, thick)
            pygame.draw.circle(screen, core, (cx, cy - r + 2), 3)
            pygame.draw.arc(screen, bright, (cx - r - 12, cy - r - 10, 2 * r + 24, 16), 0.25, 2.9, 1)
        else:
            # Hyper cape
            pygame.draw.arc(screen, bright, (cx - r - 8, cy - r - 6, 2 * r + 16, 2 * r + 12), 0.35, 2.8, thick)
            pygame.draw.polygon(screen, dark, ((cx - 6, cy + r - 2), (cx + 6, cy + r - 2), (cx, cy + r + 10)))

    # High-tier signature flair for stronger outfit shifts.
    if dt >= 4:
        pygame.draw.circle(screen, _lerp_color(accent, (255, 255, 255), 0.35), (cx, cy), r + 4, 1)
    if dt >= 5:
        pygame.draw.circle(screen, _lerp_color(accent, (255, 230, 160), 0.55), (cx, cy), r + 7, 1)
    if dt >= 6:
        for i in range(3):
            ang = 2.2 + i * 2.1
            ox = int((r + 10) * math.cos(ang))
            oy = int((r + 10) * math.sin(ang))
            pygame.draw.circle(screen, core, (cx + ox, cy + oy), 2)


def draw_tower_icon(
    screen: pygame.Surface,
    cx: int,
    cy: int,
    tower_key: str,
    radius: int,
    tower: MonkeyTower | None = None,
    *,
    tier_a: int = 0,
    tier_b: int = 0,
    tier_c: int = 0,
) -> None:
    """Shop / preview / map: body follows dominant path palette; silhouette follows path shape."""
    if tower is not None:
        tier_a, tier_b, tier_c = tower.tier_a, tower.tier_b, tower.tier_c
    body, accent, dp, dt = _path_body_accent_for_tiers(tower_key, tier_a, tier_b, tier_c)
    vt = max(tier_a, tier_b, tier_c)

    _draw_tower_base_shape(screen, cx, cy, radius, tower_key, body, accent)

    if dp is not None and dt > 0:
        _draw_path_silhouette(screen, cx, cy, radius, dp, dt, accent)
        _draw_path_outfit(screen, cx, cy, radius, tower_key, dp, dt, accent)
        pygame.draw.circle(screen, accent, (cx, cy), radius + 2, 2)
        if dt >= 2:
            pygame.draw.circle(screen, _lerp_color(accent, (255, 255, 240), 0.3), (cx, cy), radius + 4, 1)
        if dt >= 3:
            pygame.draw.circle(screen, (255, 230, 140), (cx, cy), radius + 6, 2)
        if dt >= 4:
            pygame.draw.circle(
                screen, _lerp_color(accent, (255, 255, 255), 0.4), (cx, cy), radius + 8, 1
            )
        if dt >= 5:
            pygame.draw.circle(screen, (255, 215, 100), (cx, cy), radius + 10, 2)
        if dt >= 6:
            pygame.draw.circle(screen, (255, 245, 210), (cx, cy), radius + 14, 2)
    else:
        cap = min(MAX_PATH_TIER, vt)
        if vt >= 1:
            ring = _lerp_color((90, 100, 110), (255, 210, 100), 0.12 * cap)
            pygame.draw.circle(screen, ring, (cx, cy), radius + 2, 2)
        if vt >= 2:
            pygame.draw.circle(screen, (200, 175, 90), (cx, cy), radius + 4, 1)
        if vt >= 3:
            pygame.draw.circle(screen, (255, 220, 120), (cx, cy), radius + 6, 2)
        if vt >= 4:
            pygame.draw.circle(screen, (255, 200, 100), (cx, cy), radius + 8, 1)
        if vt >= 5:
            pygame.draw.circle(screen, (240, 210, 130), (cx, cy), radius + 10, 1)
        if vt >= 6:
            pygame.draw.circle(screen, (255, 235, 180), (cx, cy), radius + 12, 2)

    _draw_tower_face(screen, cx, cy, radius, tower_key, vt)

    if tower is not None and tower.paragon:
        for i, col in enumerate(((255, 95, 140), (95, 255, 210), (210, 130, 255), (255, 225, 110))):
            pygame.draw.circle(screen, col, (cx, cy), radius + 14 + i * 4, 2)
        pygame.draw.circle(screen, (255, 252, 235), (cx, cy), radius + 3, 1)


def draw_enemy_sprite(screen: pygame.Surface, enemy: Enemy, x: int, y: int) -> None:
    """Distinct enemy sprite per type with stacked modifier badges."""
    if enemy.kind == "banana":
        body = [(x - 13, y), (x - 7, y - 8), (x + 6, y - 7), (x + 12, y), (x + 6, y + 7), (x - 7, y + 8)]
        pygame.draw.polygon(screen, (242, 214, 82), body)
        pygame.draw.polygon(screen, (215, 188, 62), body, 2)
    elif enemy.kind == "fast":
        pygame.draw.polygon(screen, (255, 195, 70), ((x - 14, y), (x + 8, y - 8), (x + 12, y), (x + 8, y + 8)))
        pygame.draw.line(screen, (255, 226, 120), (x - 12, y - 6), (x - 19, y - 10), 2)
        pygame.draw.line(screen, (255, 226, 120), (x - 12, y + 6), (x - 19, y + 10), 2)
    elif enemy.kind == "armored":
        pygame.draw.polygon(
            screen,
            (130, 138, 148),
            ((x - 13, y - 7), (x - 5, y - 12), (x + 7, y - 10), (x + 14, y), (x + 7, y + 10), (x - 5, y + 12), (x - 13, y + 7)),
        )
        pygame.draw.polygon(
            screen,
            (168, 176, 188),
            ((x - 10, y - 5), (x - 2, y - 9), (x + 6, y - 7), (x + 10, y), (x + 6, y + 7), (x - 2, y + 9), (x - 10, y + 5)),
            2,
        )
    elif enemy.kind == "raider":
        pygame.draw.polygon(
            screen,
            (255, 126, 70),
            ((x - 16, y), (x - 7, y - 10), (x + 8, y - 9), (x + 16, y), (x + 8, y + 9), (x - 7, y + 10)),
        )
        pygame.draw.polygon(
            screen,
            (255, 190, 120),
            ((x - 10, y), (x - 3, y - 6), (x + 5, y - 5), (x + 10, y), (x + 5, y + 5), (x - 3, y + 6)),
            2,
        )
        pygame.draw.line(screen, (255, 222, 160), (x - 14, y - 8), (x - 22, y - 12), 2)
        pygame.draw.line(screen, (255, 222, 160), (x - 14, y + 8), (x - 22, y + 12), 2)
    elif enemy.kind == "moab":
        pygame.draw.ellipse(screen, (84, 128, 176), (x - 30, y - 17, 60, 34))
        pygame.draw.ellipse(screen, (132, 188, 236), (x - 24, y - 10, 48, 20), 2)
        pygame.draw.polygon(screen, (70, 104, 144), ((x - 28, y), (x - 38, y - 8), (x - 38, y + 8)))
        pygame.draw.line(screen, (184, 220, 250), (x - 10, y), (x + 12, y), 2)
    else:
        pygame.draw.ellipse(screen, (112, 78, 58), (x - 22, y - 16, 44, 32))
        pygame.draw.rect(screen, (138, 97, 72), (x - 16, y - 10, 32, 20), border_radius=5)
        pygame.draw.circle(screen, (82, 58, 41), (x - 10, y - 5), 4)
        pygame.draw.circle(screen, (82, 58, 41), (x + 10, y - 5), 4)
        pygame.draw.rect(screen, (190, 148, 92), (x - 6, y + 1, 12, 5), border_radius=2)

    if enemy.fortified:
        pygame.draw.circle(screen, (230, 232, 240), (x, y), int(enemy.radius) + 4, 2)
    if enemy.camo:
        pygame.draw.line(screen, (120, 70, 165), (x - 10, y - 10), (x + 10, y + 10), 2)
    if enemy.lead:
        pygame.draw.rect(screen, (188, 196, 208), (x - 4, y - 16, 8, 5), border_radius=1)
    if enemy.regen:
        pygame.draw.circle(screen, (90, 220, 130), (x + 12, y - 12), 4)
    if enemy.flying:
        pygame.draw.arc(screen, (205, 225, 250), (x - 16, y - 16, 16, 12), 0.35, 2.8, 2)
        pygame.draw.arc(screen, (205, 225, 250), (x, y - 16, 16, 12), 0.35, 2.8, 2)

    if enemy.max_layers > 1:
        for i in range(min(4, enemy.layers)):
            pygame.draw.circle(screen, (250, 248, 230), (x - 8 + i * 6, y - int(enemy.radius) - 8), 2)


def draw_monkey_tower_on_map(
    screen: pygame.Surface,
    tower: MonkeyTower,
    selected: bool,
) -> None:
    x, y = int(tower.x), int(tower.y)
    vt = tower.visual_tier()
    r = 16 + min(12, vt * 2 + (2 if tower.dominant_path() else 0))
    draw_tower_icon(screen, x, y, tower.tower_type, r, tower=tower)
    if selected:
        pygame.draw.circle(screen, (130, 210, 255), (x, y), r + 10, 2)


def draw_play_border(screen: pygame.Surface) -> None:
    pygame.draw.rect(screen, (42, 52, 62), (0, 0, PLAY_WIDTH, PLAY_HEIGHT), 2)


def draw_sidebar_bg(screen: pygame.Surface) -> None:
    pygame.draw.rect(screen, COLOR_HUD_BG, (PLAY_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))
    pygame.draw.line(screen, (48, 56, 68), (PLAY_WIDTH, 0), (PLAY_WIDTH, WINDOW_HEIGHT), 2)
    header_h = 86
    header = pygame.Surface((SIDEBAR_WIDTH, header_h), pygame.SRCALPHA)
    header.fill((26, 32, 42, 255))
    screen.blit(header, (PLAY_WIDTH, 0))
    pygame.draw.line(screen, (55, 65, 80), (PLAY_WIDTH, header_h), (WINDOW_WIDTH, header_h), 1)


def draw_text(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))


def _fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Trim text with ellipsis so it fits in max_width pixels."""
    if max_width <= 8:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    ell = "..."
    lo, hi = 0, len(text)
    best = ell
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = text[:mid].rstrip() + ell
        if font.size(cand)[0] <= max_width:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_text_fit(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    x: int,
    y: int,
    max_width: int,
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
    draw_text(screen, font, _fit_text(font, text, max_width), x, y, color)


# Simulation steps per display frame (click HUD or keys [1][2][3][8])
HUD_SPEED_CHOICES = (1, 2, 3, 8)


def speed_button_rect(index: int) -> pygame.Rect:
    """Clickable speed buttons left-to-right: 1x, 2x, 3x, 8x (index 0..3)."""
    pad = 10
    y = PLAY_HEIGHT - 44
    w, h = 54, 32
    gap = 10
    x0 = pad + 228
    return pygame.Rect(x0 + index * (w + gap), y, w, h)


def draw_hud(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    base_hp: int,
    cash: int,
    wave_display: int,
    wave_state: str,
    game_speed: int,
    auto_wave_skip: bool = False,
    sandbox: bool = False,
    sandbox_flags_label: str = "",
) -> None:
    pad = 16
    hud = pygame.Surface((540, 162), pygame.SRCALPHA)
    hud.fill((12, 18, 24, 200))
    screen.blit(hud, (pad - 4, pad - 4))
    pygame.draw.rect(screen, (55, 75, 95), (pad - 4, pad - 4, 540, 162), 1, border_radius=10)
    line_main = font.get_linesize() + 6
    draw_text(screen, font, f"Base HP  {base_hp}", pad, pad)
    draw_text(screen, font, f"Cash  ${cash}", pad, pad + line_main)
    sub_y = pad + line_main * 2 + 8
    if sandbox:
        draw_text(screen, font_small, "Sandbox  ·  freeplay test mode", pad, sub_y)
        draw_text(screen, font_small, sandbox_flags_label, pad, sub_y + font_small.get_linesize() + 4, (170, 205, 190))
    else:
        draw_text(screen, font_small, f"Wave {wave_display}  ·  {wave_state}", pad, sub_y)
    draw_text_fit(screen, font_small, "Speed · [F] cycles 1x→8x", pad, PLAY_HEIGHT - 70, 206)
    draw_text(
        screen,
        font_small,
        f"Auto wave [U]: {'ON' if auto_wave_skip else 'OFF'}",
        pad + 238,
        PLAY_HEIGHT - 70,
        (160, 220, 170) if auto_wave_skip else (170, 182, 198),
    )
    for i, sp in enumerate(HUD_SPEED_CHOICES):
        r = speed_button_rect(i)
        sel = game_speed == sp
        bg = (70, 120, 200) if sel else (38, 48, 62)
        stroke = (140, 190, 255) if sel else (70, 80, 95)
        _rounded_panel(screen, r, bg, border=stroke, border_radius=6)
        label = f"{sp}x"
        tx = r.x + (16 if sp < 10 else 13)
        draw_text(screen, font_small, label, tx, r.y + 8, (235, 240, 250) if sel else (180, 190, 205))
    hud_keys = "Keys [1][2][3][8]   Pause [P]"
    if sandbox:
        hud_keys = "Spawn [Q/W/E/R]  flags [J/K/L/N]  x5 hold Shift"
    draw_text_fit(screen, font_small, hud_keys, pad, PLAY_HEIGHT - 32, 540 - 2 * pad)


def tower_button_rect(index: int, scroll_px: int = 0) -> pygame.Rect:
    x0 = PLAY_WIDTH + SIDEBAR_PAD_X
    y0 = TOWER_SHOP_TOP + index * TOWER_ROW_STEP - scroll_px
    return pygame.Rect(x0, y0, SIDEBAR_WIDTH - 2 * SIDEBAR_PAD_X, TOWER_ROW_HEIGHT)


def draw_tower_shop(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    selected_type: str | None,
    scroll_px: int = 0,
) -> None:
    # Only the build list area scrolls; keep upgrades area fixed.
    build_view_top = 92
    build_view_bottom = UPGRADE_PANEL_Y0 - 14
    old_clip = screen.get_clip()
    screen.set_clip(
        pygame.Rect(
            PLAY_WIDTH,
            build_view_top,
            SIDEBAR_WIDTH,
            max(0, build_view_bottom - build_view_top),
        )
    )
    draw_text(screen, font, "Build", PLAY_WIDTH + SIDEBAR_PAD_X, 96 - scroll_px, COLOR_UI_ACCENT)
    for i, key in enumerate(TOWER_SHOP_ORDER):
        r = tower_button_rect(i, scroll_px)
        base = TOWER_TYPES[key]
        sel = selected_type == key
        bg = (48, 58, 74) if sel else (32, 38, 48)
        brd = (110, 170, 240) if sel else (58, 68, 82)
        _rounded_panel(screen, r, bg, border=brd, border_radius=8)
        draw_tower_icon(screen, r.x + 24, r.centery, key, 14)
        name_y = r.y + 11
        draw_text_fit(screen, font_small, base["name"], r.x + 48, name_y, r.width - 112)
        cost_text = f"${base['cost']}"
        cost_x = r.right - 12 - font_small.size(cost_text)[0]
        draw_text(screen, font_small, cost_text, cost_x, r.y + 34, (200, 215, 232))
    screen.set_clip(old_clip)


def upgrade_row_rect(y_start: int, index: int, scroll_px: int = 0) -> pygame.Rect:
    """index 0,1,2 for paths A,B,C."""
    x0 = PLAY_WIDTH + SIDEBAR_PAD_X
    y0 = y_start + index * UPGRADE_ROW_STEP - scroll_px
    return pygame.Rect(x0, y0, SIDEBAR_WIDTH - 2 * SIDEBAR_PAD_X, UPGRADE_ROW_HEIGHT)


def paragon_upgrade_rect(paths_row_y: int, scroll_px: int = 0) -> pygame.Rect:
    x0 = PLAY_WIDTH + SIDEBAR_PAD_X
    y = paths_row_y + 3 * UPGRADE_ROW_STEP + UPGRADE_PARAGON_GAP - scroll_px
    return pygame.Rect(x0, y, SIDEBAR_WIDTH - 2 * SIDEBAR_PAD_X, 60)


def sell_tower_button_rect(scroll_px: int = 0) -> pygame.Rect:
    """Top-right of the upgrades panel when a tower is selected."""
    return pygame.Rect(WINDOW_WIDTH - SIDEBAR_PAD_X - 118, UPGRADE_PANEL_Y0 - 34 - scroll_px, 118, 32)


def draw_upgrade_panel(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    tower: MonkeyTower | None,
    cash: int,
    scroll_px: int = 0,
) -> None:
    # Below tower shop (nine rows end ~460); panel only covers upgrade block
    y0 = UPGRADE_PANEL_Y0
    panel_top = y0 - 30
    panel_h = WINDOW_HEIGHT - panel_top - 10
    inset = 10
    panel_rect = pygame.Rect(PLAY_WIDTH + inset, panel_top, SIDEBAR_WIDTH - 2 * inset, panel_h)
    _rounded_panel(screen, panel_rect, (28, 34, 44), border=(48, 58, 72), border_radius=8)
    old_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(PLAY_WIDTH, panel_top, SIDEBAR_WIDTH, WINDOW_HEIGHT - panel_top))
    draw_text(screen, font, "Upgrades", PLAY_WIDTH + SIDEBAR_PAD_X, y0 - 26 - scroll_px, COLOR_UI_ACCENT)
    if tower is None:
        draw_text(
            screen,
            font_small,
            "Select a tower",
            PLAY_WIDTH + SIDEBAR_PAD_X,
            y0 + 6 - scroll_px,
            (160, 170, 185),
        )
        screen.set_clip(old_clip)
        return
    sr = sell_tower_button_rect(scroll_px)
    _rounded_panel(screen, sr, (52, 40, 46), border=(220, 140, 140), border_width=2, border_radius=6)
    ref = tower.sell_refund_amount()
    draw_text(screen, font_small, "Sell [X]", sr.x + 12, sr.y + 5, (255, 215, 215))
    draw_text(screen, font_small, f"+${ref}", sr.x + 12, sr.y + 17, (185, 235, 195))
    line_skip, text_top = _upgrade_panel_stat_metrics(font_small)
    text_x = PLAY_WIDTH + 54
    text_w = WINDOW_WIDTH - text_x - SIDEBAR_PAD_X
    draw_tower_icon(screen, PLAY_WIDTH + 30, text_top + 14 - scroll_px, tower.tower_type, 12, tower=tower)

    stat_lines = tower_upgrade_stat_lines(tower)
    for i, (txt, col) in enumerate(stat_lines):
        draw_text_fit(
            screen,
            font_small,
            txt,
            text_x,
            text_top + i * line_skip - scroll_px,
            text_w,
            col,
        )

    row_y = compute_upgrade_paths_row_y(font_small)
    paths = TOWER_PATH_UPGRADES[tower.tower_type]
    ca, cb, cc = tower.upgrade_cost_a(), tower.upgrade_cost_b(), tower.upgrade_cost_c()

    rows = [
        ("A", "a", PATH_LANE_NAMES[0], paths["a"][0], paths["a"][1], float(paths["a"][2]), tower.tier_a, ca, 0),
        ("B", "b", PATH_LANE_NAMES[1], paths["b"][0], paths["b"][1], float(paths["b"][2]), tower.tier_b, cb, 1),
        ("C", "c", PATH_LANE_NAMES[2], paths["c"][0], paths["c"][1], float(paths["c"][2]), tower.tier_c, cc, 2),
    ]
    mx = tower.max_tier()
    for key, path_key, lane, name, stat, stat_val, tier, cost, ri in rows:
        rr = upgrade_row_rect(row_y, ri, scroll_px)
        maxed = tier >= mx
        locked = not maxed and cost is None
        can_buy = cost is not None and cash >= cost
        row_bg = _upgrade_row_fill(maxed, locked, can_buy)
        _rounded_panel(screen, rr, row_bg, border=(55, 65, 78), border_radius=6)
        if maxed:
            price = "MAX"
        elif locked:
            price = "LOCK"
        else:
            price = f"${cost}"
        hot = (150, 210, 255) if can_buy or maxed else ((100, 90, 110) if locked else (120, 100, 100))
        draw_text(screen, font_small, f"[{key}]", rr.x + 12, rr.y + 15, hot)
        draw_text(screen, font_small, f"{lane}", rr.x + 40, rr.y + 13, (130, 160, 190))
        draw_text_fit(screen, font_small, name, rr.x + 40, rr.y + 28, rr.width - 154)
        draw_text_fit(
            screen,
            font_small,
            format_path_upgrade_effect(stat, stat_val),
            rr.x + 40,
            rr.y + 46,
            rr.width - 154,
            (150, 170, 188),
        )
        unlocks = tower.modifier_unlocks_for_path(path_key)
        if unlocks:
            draw_text_fit(
                screen,
                font_small,
                f"Unlocks: {', '.join(unlocks)}",
                rr.x + 40,
                rr.y + 64,
                rr.width - 154,
                (166, 205, 166),
            )
        price_col = (200, 210, 220) if can_buy or maxed else ((160, 140, 180) if locked else (180, 130, 130))
        draw_text(screen, font_small, f"t{tier}/{MAX_PATH_TIER}", rr.right - 114, rr.y + 15, price_col)
        price_x = rr.right - 14 - font_small.size(price)[0]
        draw_text(screen, font_small, price, price_x, rr.y + 38, price_col)
        if cost is not None and cash < cost:
            draw_text(screen, font_small, "!", rr.right - 18, rr.y + 38, (230, 120, 120))

    pr = paragon_upgrade_rect(row_y, scroll_px)
    _draw_paragon_upgrade_slot(screen, font_small, pr, tower, cash)
    screen.set_clip(old_clip)


def wave_panel_rects() -> tuple[pygame.Rect, pygame.Rect]:
    """Next wave button, maybe full panel."""
    panel_w = 640
    panel_h = 392
    panel = pygame.Rect(PLAY_WIDTH // 2 - panel_w // 2, PLAY_HEIGHT // 2 - 180, panel_w, panel_h)
    next_r = pygame.Rect(panel.centerx - 126, panel.bottom - 78, 252, 52)
    return next_r, panel


def draw_wave_break(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_title: pygame.font.Font,
    font_small: pygame.font.Font,
    wave_next: int,
    cash: int,
    global_tiers: dict[str, int],
    wave_round_bonus: int = 0,
    farm_income: int = 0,
    auto_wave_skip: bool = False,
) -> None:
    overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
    overlay.fill((8, 12, 18, 210))
    screen.blit(overlay, (0, 0))
    _, panel = wave_panel_rects()
    _rounded_panel(screen, panel, (24, 30, 40), border=COLOR_UI_ACCENT, border_width=2, border_radius=12)
    cx = panel.centerx
    left = panel.x + 28
    right_pad = 28
    content_w = panel.width - (left - panel.x) - right_pad
    draw_text_fit(screen, font_title, "Wave complete", cx - 100, panel.y + 24, 220)
    draw_text_fit(
        screen,
        font_small,
        "Endless · Mega-boss (regen) every 10th wave · extra ramp after wave 10",
        left,
        panel.y + 66,
        content_w,
        (150, 170, 190),
    )
    draw_text_fit(
        screen,
        font_small,
        "Spend on global upgrades, then continue.",
        left,
        panel.y + 94,
        content_w,
        (170, 185, 200),
    )
    pygame.draw.line(screen, (58, 72, 88), (panel.x + 24, panel.y + 128), (panel.right - 24, panel.y + 128), 1)
    income_y = panel.y + 152
    if wave_round_bonus or farm_income:
        draw_text_fit(
            screen,
            font_small,
            f"Income this round:  +${wave_round_bonus} wave  ·  +${farm_income} farms",
            left,
            panel.y + 152,
            content_w,
            (140, 200, 160),
        )
        income_y = panel.y + 184

    footer_text_y = panel.bottom - 102
    footer_sep_y = panel.bottom - 114
    y = income_y
    available_h = max(24, footer_sep_y - y - 8)
    row_gap = max(24, min(34, available_h // max(1, len(GLOBAL_UPGRADES))))
    for gu in GLOBAL_UPGRADES:
        gid = gu["id"]
        tier = global_tiers.get(gid, 0)
        cost = (
            int(gu["base_cost"] * (GLOBAL_UPGRADE_COST_MULT**tier))
            if tier < gu["max_tier"]
            else None
        )
        label = f"{gu['name']}   [{tier}/{gu['max_tier']}]"
        if cost is not None:
            label += f"   ${cost}   [key {GLOBAL_UPGRADES.index(gu)+7}]"
        else:
            label += "   MAX"
        draw_text_fit(screen, font_small, label, left, y, content_w)
        y += row_gap

    pygame.draw.line(
        screen,
        (58, 72, 88),
        (panel.x + 24, footer_sep_y),
        (panel.right - 24, footer_sep_y),
        1,
    )
    draw_text_fit(
        screen,
        font,
        f"Next: Wave {wave_next}   [SPACE] or button   ·   [T] Title screen",
        left,
        footer_text_y,
        content_w,
    )
    draw_text_fit(
        screen,
        font_small,
        f"Auto wave [U]: {'ON' if auto_wave_skip else 'OFF'}",
        left,
        footer_text_y + 20,
        content_w,
        (165, 225, 175) if auto_wave_skip else (150, 162, 178),
    )


def next_wave_button_screen_rect() -> pygame.Rect:
    next_r, _ = wave_panel_rects()
    return next_r

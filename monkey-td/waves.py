"""Wave spawn queue from WAVES_RAW."""

from __future__ import annotations

from collections import deque

from config import (
    ENEMY_FLAG_CAMO,
    ENEMY_FLAG_FORTIFIED,
    ENEMY_FLAG_LEAD,
    ENEMY_FLAG_REGEN,
    WAVES_RAW,
)
from entities import Enemy


class WaveController:
    def __init__(self) -> None:
        self.wave_index = -1
        self.active = False
        self.spawn_queue: deque[tuple[str, int]] = deque()
        self.spawn_timer = 0
        self.spawn_interval = 40
        self.pending_between = False

    def start_wave(self, index: int) -> None:
        if index < 0 or index >= len(WAVES_RAW):
            return
        self.wave_index = index
        spec = WAVES_RAW[index]
        self.spawn_interval = int(spec.get("interval", 40))
        self.spawn_queue.clear()
        for entry in spec["entries"]:
            if len(entry) == 2:
                kind, count = entry[0], entry[1]
                flags = 0
            else:
                kind, count, flags = entry[0], entry[1], int(entry[2])
            for _ in range(count):
                self.spawn_queue.append((kind, flags))
        self.spawn_timer = 0
        self.active = True
        self.pending_between = False

    def wave_done_spawning(self) -> bool:
        return len(self.spawn_queue) == 0

    def pop_spawn(self) -> tuple[str, int] | None:
        if not self.spawn_queue:
            return None
        return self.spawn_queue.popleft()

    def update_spawn_timer(self) -> bool:
        """Return True when it's time to spawn one enemy."""
        if not self.active or not self.spawn_queue:
            return False
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            return True
        return False


def make_enemy(
    kind: str,
    hp_mult: float = 1.0,
    speed_mult: float = 1.0,
    flags: int = 0,
    boss_decade: int = 0,
) -> Enemy:
    return Enemy(
        kind=kind,
        difficulty_hp=hp_mult,
        difficulty_speed=speed_mult,
        camo=(flags & ENEMY_FLAG_CAMO) != 0,
        lead=(flags & ENEMY_FLAG_LEAD) != 0,
        fortified=(flags & ENEMY_FLAG_FORTIFIED) != 0,
        regen=(flags & ENEMY_FLAG_REGEN) != 0,
        boss_decade=boss_decade,
    )

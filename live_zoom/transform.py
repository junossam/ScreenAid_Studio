from __future__ import annotations


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), max(minimum, maximum))


def fullscreen_offset(
    anchor_x: int,
    anchor_y: int,
    monitor_rect: tuple[int, int, int, int],
    scale: float,
) -> tuple[int, int]:
    """(x_offset, y_offset) for MagSetFullscreenTransform that keeps the zoom
    confined to `monitor_rect` while centering `(anchor_x, anchor_y)`.

    MagSetFullscreenTransform's real relationship (confirmed by live testing
    on a 4-monitor box, not just the docs) is
        displayed_at = scale * (real_pos - offset)
    i.e. offset is a shift of the SOURCE point, applied before scaling - not
    a post-scale screen-space shift as the docs' wording first suggested.
    "s" is one shared virtual-desktop coordinate space across every monitor,
    not primary-relative: a large enough offset pans the sampled content into
    a neighboring monitor's real estate, or off the desktop entirely into
    black if nothing is there.

    To keep zoom confined to whichever monitor the cursor is currently on (so
    this works unmodified on any monitor layout, not just one machine's), the
    offset is solved for and clamped against THAT monitor's own bounds:
    centering anchor_x on the monitor's midpoint gives
    offset = anchor_x - mon_center_x/scale, and clamping keeps the sampled
    source region inside [mon_left, mon_right] so it can never bleed into a
    neighbor or empty space. At scale=1 both clamp bounds collapse to 0,
    which is also the only offset MagSetFullscreenTransform accepts when
    unmagnified.
    """
    mon_left, mon_top, mon_right, mon_bottom = monitor_rect
    mon_center_x = (mon_left + mon_right) / 2
    mon_center_y = (mon_top + mon_bottom) / 2
    x_offset = clamp(
        anchor_x - mon_center_x / scale, mon_left * (1 - 1 / scale), mon_right * (1 - 1 / scale)
    )
    y_offset = clamp(
        anchor_y - mon_center_y / scale, mon_top * (1 - 1 / scale), mon_bottom * (1 - 1 / scale)
    )
    return round(x_offset), round(y_offset)

"""How a person moves a mouse and types: paths, timings, US keyboard shifts."""
import math
import random

SHIFTED = set('~!@#$%^&*()_+{}|:"<>?ABCDEFGHIJKLMNOPQRSTUVWXYZ')
SPECIAL = {"\n": "Enter", "\t": "Tab"}


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def point_in(box, rng=random):
    """A point inside an element, near the middle but never exactly on it."""
    fx = clip(rng.gauss(0.5, 0.13), 0.22, 0.78)
    fy = clip(rng.gauss(0.5, 0.13), 0.25, 0.75)
    return box["x"] + box["w"] * fx, box["y"] + box["h"] * fy


def path(start, end, width=20, rng=random):
    """Mouse points from start to end on a curve, with a time gap before each.

    Fitts's law sets the total time; minimum-jerk easing sets the speed along it.
    """
    (x0, y0), (x1, y1) = start, end
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist < 1:
        return [(x1, y1, 0.01)]
    total = 0.12 + 0.13 * math.log2(1 + dist / max(width, 4)) + rng.uniform(0, 0.08)
    steps = int(clip(dist / 14, 6, 70))
    # Two control points pushed off the straight line, same side most of the time.
    nx, ny = -(y1 - y0) / dist, (x1 - x0) / dist
    bend = rng.gauss(0, 0.12) * dist
    c1 = (x0 + (x1 - x0) * 0.3 + nx * bend, y0 + (y1 - y0) * 0.3 + ny * bend)
    c2 = (x0 + (x1 - x0) * 0.7 + nx * bend * rng.uniform(0.3, 1.0),
          y0 + (y1 - y0) * 0.7 + ny * bend * rng.uniform(0.3, 1.0))
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        s = 10 * t**3 - 15 * t**4 + 6 * t**5
        u = 1 - s
        x = u**3 * x0 + 3 * u**2 * s * c1[0] + 3 * u * s**2 * c2[0] + s**3 * x1
        y = u**3 * y0 + 3 * u**2 * s * c1[1] + 3 * u * s**2 * c2[1] + s**3 * y1
        if i < steps:
            x += rng.gauss(0, 0.4)
            y += rng.gauss(0, 0.4)
        out.append((x, y, total / steps))
    return out


def press_time(rng=random):
    """How long a mouse button or key stays down."""
    return clip(rng.gauss(0.085, 0.025), 0.035, 0.18)


def key_gap(rng=random):
    """Pause between one key and the next."""
    return clip(rng.lognormvariate(math.log(0.11), 0.45), 0.03, 0.6)


def keys_for(ch):
    """(key, needs_shift) for one typed character."""
    if ch in SPECIAL:
        return SPECIAL[ch], False
    return ch, ch in SHIFTED

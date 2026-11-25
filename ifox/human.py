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


# ---------------------------------------------------------------- typing

# Letter pairs typed in one quick roll, from English text.
QUICK_PAIRS = set("th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng se ha as ou io le "
                  "ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si om ur".split())
# Keys next to each key on a US keyboard, for typos.
_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
NEIGHBOURS = {}
for _r, _row in enumerate(_ROWS):
    for _c, _k in enumerate(_row):
        near = [_row[i] for i in (_c - 1, _c + 1) if 0 <= i < len(_row)]
        for _dr in (-1, 1):
            if 0 <= _r + _dr < len(_ROWS):
                other = _ROWS[_r + _dr]
                near += [other[i] for i in (_c - 1, _c, _c + 1) if 0 <= i < len(other)]
        NEIGHBOURS[_k] = near


class Typist:
    """One person's typing: speed and rhythm. A key (a profile's seed) gives the same person every
    run; no key gives a new one."""

    def __init__(self, key=None):
        r = random.Random(None if key is None else f"typist:{key}")
        self.wpm = round(clip(r.gauss(52, 11), 30, 85))     # words a minute, a word being 5 letters
        self.hold = clip(r.gauss(0.085, 0.012), 0.06, 0.12)   # how long a key stays down
        self.roll = r.uniform(0.6, 0.85)                      # common pairs, this much quicker
        self.pause = r.uniform(0.01, 0.04)                    # chance of a short think before a word

    def __repr__(self):
        return f"<Typist {self.wpm} wpm>"

    def hold_time(self, rng):
        return clip(rng.gauss(self.hold, 0.02), 0.03, 0.2)

    def gap(self, prev, ch, rng, wpm=None):
        """Pause after `prev` and before `ch`."""
        per_key = 60 / ((wpm or self.wpm) * 5)                # seconds per letter, key held included
        base = max(per_key - self.hold, 0.02)
        g = rng.lognormvariate(math.log(base), 0.35)
        if prev in ".!?\n":
            g *= rng.uniform(2.5, 5)                          # end of a sentence or line
        elif prev in ",;:":
            g *= rng.uniform(1.8, 3)
        elif prev == " ":
            g *= rng.uniform(1.0, 1.5)                        # start of a word
            if rng.random() < self.pause:
                g += rng.uniform(0.3, 1.0)
        elif (prev + ch).lower() in QUICK_PAIRS:
            g *= self.roll
        return clip(g, 0.015, 3.0)

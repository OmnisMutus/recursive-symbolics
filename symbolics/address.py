"""The symbolic address space: a point no tradition owns, and the lenses that read one.

The framework's own claim (Core Axiom, "The User's Choice") is that it supplies syntax and the user supplies
semantics. That is a seam, and this module is the seam:

    observable input -> address (computed) -> lens (chosen) -> reading (interpretation)

An address is three numbers from 0 to 1000. A lens turns an address into one tradition's words. The rules that
make the claim true rather than decorative:

- a lens may never write back into an address: read() takes an address and returns words, and nothing else;
- swapping lenses cannot move the address, so no reading is ever "what the state really is";
- every reading names the tradition it read from and carries its caveat, so "anger is Geburah" is not expressible.
  The engine can only say: at this address, the Kabbalistic lens reads Geburah.

The axes, chosen because each is computable from something observable:

    severity_mercy   0 restriction, cutting, boundary     1000 expansion, giving, dissolution
    descent          0 origin, undifferentiated           1000 manifest, particular, embodied
    entropy          0 repetitive, locked                 1000 sprawling, chaotic

Three axes, not ten. The ten Sephiroth are not axes; they are what one lens reads at a region of the space.
Where an address came from travels with it (`derivation`), and so does the evidence (`anchors`), because a
reading that cannot point at the words it came from is refused elsewhere in this engine.
"""
import dataclasses
import math

AXES = ("severity_mercy", "descent", "entropy")
LOW, HIGH = 0, 1000
MID = (LOW + HIGH) // 2
BOUNDARY = 90             # two candidate readings this close together are both offered, never one chosen silently


def clamp(value):
    return max(LOW, min(HIGH, int(round(float(value)))))


@dataclasses.dataclass(frozen=True)
class Anchor:
    """The evidence a claim rests on: where it came from, and the words themselves."""
    source: str                     # a note path, a file, "spoken", whatever the caller can name
    quote: str
    lines: tuple = ()               # (first, last), 1-based, when the source has lines

    def as_dict(self):
        d = {"source": self.source, "quote": self.quote}
        if self.lines:
            d["lines"] = list(self.lines)
        return d


@dataclasses.dataclass(frozen=True)
class Address:
    severity_mercy: int
    descent: int
    entropy: int
    derivation: dict = dataclasses.field(default_factory=dict)      # axis -> how it was computed
    anchors: tuple = ()                                             # Anchor, the words behind it

    def __post_init__(self):
        for axis in AXES:
            value = getattr(self, axis)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{axis} must be a whole number from {LOW} to {HIGH}.")
            if not LOW <= value <= HIGH:
                raise ValueError(f"{axis} is {value}; the axes run from {LOW} to {HIGH}.")
        missing = [a for a in AXES if a not in self.derivation]
        if self.derivation and missing:
            raise ValueError(f"derivation given but silent about: {', '.join(missing)}. "
                             "Say how every axis was computed, or give none.")

    @property
    def point(self):
        return tuple(getattr(self, a) for a in AXES)

    def as_dict(self):
        d = {"type": "address", **{a: getattr(self, a) for a in AXES}}
        if self.derivation:
            d["derivation"] = dict(self.derivation)
        if self.anchors:
            d["anchors"] = [a.as_dict() for a in self.anchors]
        return d


def at(severity_mercy=MID, descent=MID, entropy=MID, derivation=None, anchors=()):
    """An address, clamped, with its derivation and evidence."""
    return Address(clamp(severity_mercy), clamp(descent), clamp(entropy),
                   dict(derivation or {}), tuple(anchors))


def distance(a, b):
    """How far apart two addresses are, in the space's own units (Euclidean over the three axes)."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a.point, b.point)))


def compose(*addresses, note=""):
    """Two or more demands on one state, as the framework's unmapped cross-operator interference (hidden-axioms
    7.3): the axes are summed around the middle and clamped, so expand and restrict at once land back near the
    centre rather than cancelling into nothing. The composition keeps every derivation and every anchor, because
    a composite reading has to be traceable to both sides."""
    if not addresses:
        raise ValueError("Give at least one address to compose.")
    values, derivation, anchors = [], {}, []
    for axis in AXES:
        total = sum(getattr(x, axis) - MID for x in addresses)
        values.append(clamp(MID + total))
    for i, x in enumerate(addresses, 1):
        for axis, how in (x.derivation or {}).items():
            derivation[axis] = f"{derivation.get(axis, '')} | {i}: {how}".lstrip(" |")
        anchors.extend(x.anchors)
    for axis in AXES:
        derivation.setdefault(axis, f"composed from {len(addresses)} addresses")
    if note:
        derivation["note"] = note
    return Address(*values, derivation=derivation, anchors=tuple(anchors))


# ---------------------------------------------------------------- lenses
@dataclasses.dataclass(frozen=True)
class Lens:
    """One tradition's words for regions of the space. A table, a source and a date: adding a tradition is
    adding one of these, and the engine never learns a tradition, it reads one.

    `places` is {name: (severity_mercy, descent)}; entropy is reported, never used to choose a name, because no
    tradition in the framework places its names along a chaos axis.
    """
    tradition: str
    source: str
    dated: str
    places: dict
    note: str = ""

    def __post_init__(self):
        if not self.places:
            raise ValueError(f"The {self.tradition} lens has no places.")
        for name, where in self.places.items():
            if len(where) != 2 or not all(LOW <= v <= HIGH for v in where):
                raise ValueError(f"{self.tradition}: '{name}' sits outside the space at {where}.")


# The Tree as it is drawn: the three pillars across, the ten numbers down. Severity on the left, Mercy on the
# right, the middle pillar between them; Kether first and Malkuth tenth. Nothing here is a claim about what any
# Sephirah means, only where the diagram puts it.
_PILLAR = {"severity": 150, "middle": MID, "mercy": 850}
_TREE = [("Kether", "middle", 1), ("Chokmah", "mercy", 2), ("Binah", "severity", 3),
         ("Chesed", "mercy", 4), ("Geburah", "severity", 5), ("Tiphareth", "middle", 6),
         ("Netzach", "mercy", 7), ("Hod", "severity", 8), ("Yesod", "middle", 9), ("Malkuth", "middle", 10)]

KABBALISTIC = Lens(
    tradition="Kabbalistic (Hermetic Tree of Life)",
    source="the Tree as drawn in the Golden Dawn and Thelemic sources: three pillars, ten Sephiroth in order",
    dated="2026-11-08",
    places={name: (_PILLAR[pillar], clamp((level - 1) / 9 * HIGH)) for name, pillar, level in _TREE},
    note="Position on the diagram only. Which Sephirah a state 'is' is not a question this engine answers.",
)

DYNAMICAL = Lens(
    tradition="dynamical systems",
    source="Mathemathical-foundation.md: fixed points, limit cycles, strange attractors",
    dated="2026-11-08",
    places={"fixed point": (MID, 100), "limit cycle": (MID, MID), "strange attractor": (MID, 900),
            "contraction": (120, MID), "diffusion": (880, MID)},
    note="A reading of the state's shape, not a measurement of a trajectory: that needs a sequence, not a point.",
)

LENSES = {"kabbalistic": KABBALISTIC, "dynamical": DYNAMICAL}


def read(address, lens=KABBALISTIC, caveat=None):
    """What one lens reads at an address. Returns a reading, never a verdict.

    Two names closer together than BOUNDARY are both offered, in the framework's own words (core-ethics 4):
    the engine asks which feels true rather than choosing for the person.
    """
    if isinstance(lens, str):
        try:
            lens = LENSES[lens.casefold()]
        except KeyError:
            raise ValueError(f"No lens called '{lens}'. Lenses: {', '.join(sorted(LENSES))}.") from None
    ranked = sorted(((math.dist((address.severity_mercy, address.descent), where), name)
                     for name, where in lens.places.items()))
    nearest, candidates = ranked[0][1], [n for d, n in ranked if d - ranked[0][0] <= BOUNDARY]
    out = {"type": "reading", "tradition": lens.tradition, "source": lens.source, "lens_dated": lens.dated,
           "reads": nearest, "candidates": candidates, "distance": round(ranked[0][0], 1),
           "entropy": address.entropy, "address": address.as_dict(),
           "anchors": [a.as_dict() for a in address.anchors]}
    if len(candidates) > 1:
        out["ask"] = (f"This sits between {' and '.join(candidates)}; which feels more true for you?")
    if lens.note:
        out["lens_note"] = lens.note
    if caveat:
        out["caveat"] = caveat
    return out


def readings(address, lenses=None, caveat=None):
    """Several traditions over one address, each worked out on its own so that no reading can colour another
    (the isolation of Thoth/solo's ANTI_ECHO_ISOLATION_POLICY, applied inside a single call). A lens that fails
    carries its own error and the others still stand."""
    out = []
    for key in (lenses or sorted(LENSES)):
        try:
            out.append(read(address, key, caveat=caveat))
        except Exception as e:                      # one tradition's broken table is not the others' problem
            out.append({"type": "unknown", "tradition": str(key), "why": f"{type(e).__name__}: {e}"})
    return out

"""plan.json schema types and validation for world-builder UE5."""

from typing import Literal, Optional

# ── Enums for plan.json fields ─────────────────────────────────────

Theme = Literal["tropical", "desert", "forest", "urban", "space", "fantasy"]
Stylization = Literal["high", "mid", "low"]
Shading = Literal["toon", "flat", "pbr-light"]
Lighting = Literal["golden-hour", "noon", "dusk", "night"]
TerrainShape = Literal["island", "hills", "flat", "crater", "shoreline", "valley"]
GroundType = Literal["sand", "grass", "dirt", "rock", "snow"]
WaterType = Literal["ocean", "lake", "river", "none"]
ObjectType = Literal["tree", "rock", "structure", "prop", "vegetation", "water_feature"]
Framing = Literal["three-quarter aerial", "eye-level", "top-down"]
ScaleHint = Literal["tiny", "small", "medium", "large", "tall", "huge"]


# ── Sample CC0 asset mapping ──────────────────────────────────────
# Used to suggest free assets for each object type during analysis
ASSET_HINTS = {
    "tree": [
        "Kenney.nl — stylised low-poly trees (CC0)",
        "Poly Haven — tropical palms (CC0)",
        "Quaternius — cartoon trees (CC0)",
    ],
    "rock": [
        "Quaternius — rock pack (CC0)",
        "Poly Haven — boulders (CC0)",
        "Kenney.nl — rocks (CC0)",
    ],
    "structure": [
        "Poly Haven — architectural models (CC0)",
        "Quaternius — buildings (CC0)",
        "UE5 starter content — basic architecture",
    ],
    "prop": [
        "Kenney.nl — props (CC0)",
        "Quaternius — props (CC0)",
        "Poly Pizza — free section (CC0)",
    ],
    "vegetation": [
        "Quaternius — vegetation pack (CC0)",
        "Poly Haven — plants & grass (CC0)",
        "Kenney.nl — foliage (CC0)",
    ],
}


def get_asset_hint(object_type: str) -> str:
    """Return a suggested CC0 asset source for a given object type."""
    hints = ASSET_HINTS.get(object_type, ["Poly Haven — general CC0 assets"])
    return hints[0]


# ── Terrain type → material hints ─────────────────────────────────

TERRAIN_MATERIALS = {
    "sand": "UE5 Material Editor: light beige with slight noise for grain, roughness ~0.8, use Landscape material blend",
    "grass": "UE5 Material Editor: green with variation noise, roughness ~0.9, Landscape layer blend",
    "dirt": "UE5 Material Editor: brown with rocky noise, roughness ~0.9",
    "rock": "UE5 Material Editor: gray with cracks and variation, roughness ~0.7",
    "snow": "UE5 Material Editor: white with slight blue tint, roughness ~0.5, sparkle normal",
}

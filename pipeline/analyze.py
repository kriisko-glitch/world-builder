"""
Phase 0: Analyze reference image → plan.json

Reads a reference image, produces a structured scene plan for the UE5
world-builder pipeline. The vision analysis is done by Claude (via Hermes) —
this module handles file scaffolding, schema validation, and the prompt
template for the vision model.

Usage:
    python pipeline/analyze.py input/test-beach.jpg banjo-beach

Output:
    worlds/banjo-beach/
    ├── reference.png        ← copy of the input image
    └── plan.json             ← structured scene plan
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Paths ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
WORLDS_DIR = REPO_ROOT / "worlds"
INPUT_DIR = REPO_ROOT / "input"


# ── Schema ─────────────────────────────────────────────────────────
# Matches the world-builder plan.json format for compatibility
PLAN_SCHEMA_TEMPLATE = {
    "world_slug": "",
    "source_image": "",
    "created_at": "",
    "style": {
        "anchor": "",               # e.g., "Banjo-Kazooie · Treasure Trove Cove"
        "theme": "",                # tropical | desert | forest | urban | space | fantasy
        "palette": [],              # hex color list, e.g., ["#f2d790", "#3aa6b8"]
        "level_of_stylization": "high",  # high | mid | low
        "shading": "toon",          # toon | flat | pbr-light
        "lighting": "golden-hour",  # golden-hour | noon | dusk | night
    },
    "terrain": {
        "shape": "shoreline",       # island | hills | flat | crater | shoreline | valley
        "ground_type": "sand",      # sand | grass | dirt | rock | snow
        "water": {
            "present": True,
            "level_z": -0.05,       # Z-height relative to ground
            "type": "ocean",        # ocean | lake | river | none
        },
        "size_meters": [32, 32],    # [x, y] in meters
        "feature_notes": "",
    },
    "objects": [
        # {
        #     "id": "palm-tall",
        #     "name": "Tall tropical palm tree",
        #     "type": "tree",
        #     "count": 3,
        #     "approx_positions": [[x, y], ...],
        #     "scale_hint": "tall",
        #     "asset_hint": "",       # CC0 source hint (e.g., "Poly Haven palm")
        # }
    ],
    "camera": {
        "framing": "three-quarter aerial",  # three-quarter aerial | eye-level | top-down
        "focal_length_mm": 35,
        "position_hint": [0, 0, 5],      # approximate camera position
        "look_at": [0, 0, 0],            # approximate look-at target
    },
}


def validate_plan(plan: dict) -> list[str]:
    """Validate a plan against required fields. Returns list of issues."""
    issues = []

    if not plan.get("world_slug"):
        issues.append("Missing: world_slug")
    if not plan.get("style", {}).get("theme"):
        issues.append("Missing: style.theme")
    if not plan.get("objects"):
        issues.append("Missing: objects (at least one required)")

    # Warn on empty palette
    if not plan.get("style", {}).get("palette"):
        issues.append("Warning: style.palette is empty")

    # Validate object count sanity
    total_instances = sum(obj.get("count", 0) for obj in plan.get("objects", []))
    if total_instances == 0:
        issues.append("All objects have count=0 — no instances to place")
    elif total_instances > 50:
        issues.append(f"High instance count ({total_instances}) — consider reducing")

    return issues


# ── Vision analysis prompt template ────────────────────────────────
# This is the prompt Claude (Hermes) uses to analyze the reference image.
# The output should be a valid plan.json following the schema above.
ANALYSIS_PROMPT = """Analyze this reference image and produce a complete scene plan
for a UE5 game world. Output VALID JSON only — no markdown fences, no commentary.

## What to include

### style
- theme: tropical | desert | forest | urban | space | fantasy
- anchor: reference art style (e.g., "Wind Waker cel-shaded", "Banjo-Kazooie cartoon")
- palette: 3-6 hex colors that capture the dominant colors (#RRGGBB)
- level_of_stylization: high (cartoon) | mid (stylized realism) | low (photoreal)
- shading: toon | flat | pbr-light
- lighting: golden-hour | noon | dusk | night

### terrain
- shape: island | hills | flat | crater | shoreline | valley
- ground_type: sand | grass | dirt | rock | snow
- water: present (bool), type (ocean/lake/river), approximate Z-level
- size_meters: [x, y] bounds
- feature_notes: 1-2 sentences describing unique terrain features

### objects
For each distinct object type you see in the scene:
- id: short machine-readable slug ("palm-tall", "rock-round")
- name: human-readable ("Tall palm tree", "Round beach rock")
- type: tree | rock | structure | prop | vegetation | water_feature
- count: how many instances (group similar items under one id)
- approx_positions: list of [x, y] rough coords (0,0 = center, range ~ -15 to +15)
- scale_hint: tiny | small | medium | large | tall | huge
- asset_hint: what CC0 library might have this (e.g., "Poly Haven palm", "Kenney rocks")

Target 8-15 distinct object types, 20-30 total instances. Group similar items.

### camera
- framing: three-quarter aerial | eye-level | top-down
- focal_length_mm: 24 (wide) | 35 (normal) | 50 (portrait) | 85 (telephoto)

## Example output

{
  "world_slug": "tropical-beach",
  "style": {
    "theme": "tropical",
    "anchor": "Wind Waker cel-shaded",
    "palette": ["#f2d790", "#3aa6b8", "#1f6f4b", "#ffffff", "#8B4513"],
    "level_of_stylization": "high",
    "shading": "toon",
    "lighting": "golden-hour"
  },
  "terrain": {
    "shape": "shoreline",
    "ground_type": "sand",
    "water": {"present": true, "level_z": -0.05, "type": "ocean"},
    "size_meters": [32, 32],
    "feature_notes": "Gentle beach slope into turquoise water, palm cluster on right side"
  },
  "objects": [
    {"id": "palm-tall", "name": "Tall palm tree", "type": "tree", "count": 3,
     "approx_positions": [[8,2], [10,-1], [7,4]], "scale_hint": "tall",
     "asset_hint": "Poly Haven or Kenney palm"},
    {"id": "rock-round", "name": "Round beach rock", "type": "rock", "count": 5,
     "approx_positions": [[-3,4], [-5,2], [-2,5], [-4,3], [-1,4]], "scale_hint": "small",
     "asset_hint": "Quaternius rocks or Poly Haven boulders"}
  ],
  "camera": {
    "framing": "eye-level",
    "focal_length_mm": 35,
    "position_hint": [0, -12, 1.6],
    "look_at": [0, 5, 0.5]
  }
}

Output ONLY the JSON object. No ``` fences, no explanatory text.
"""


# ── Main ────────────────────────────────────────────────────────────

def setup_world_directory(world_slug: str) -> Path:
    """Create worlds/<slug>/ directory, copy reference image there."""
    world_dir = WORLDS_DIR / world_slug
    world_dir.mkdir(parents=True, exist_ok=True)
    (world_dir / "screenshots").mkdir(exist_ok=True)
    return world_dir


def create_plan(
    world_slug: str,
    source_image: str,
    plan_data: dict,
    overwrite: bool = False,
) -> Path:
    """
    Write plan.json from analyzed data.

    Args:
        world_slug: Name for this world (used as directory name and slug)
        source_image: Path to the reference image (copied into world dir)
        plan_data: The analyzed plan dict (from Claude vision analysis)
        overwrite: If True, overwrite existing plan.json

    Returns:
        Path to the written plan.json
    """
    world_dir = setup_world_directory(world_slug)

    # Validate
    issues = validate_plan(plan_data)
    if issues:
        print("⚠️  Plan validation warnings:")
        for issue in issues:
            print(f"   - {issue}")
        if any(not i.startswith("Warning") for i in issues):
            print("❌ Critical validation errors — fix before proceeding.")
            # Don't bail here — let the user decide. Claude's analysis might
            # be incomplete but still useful. The iteration loop will fix gaps.

    # Enrich
    plan_data.setdefault("world_slug", world_slug)
    plan_data.setdefault("source_image", os.path.basename(source_image))
    plan_data.setdefault("created_at", datetime.utcnow().isoformat() + "Z")

    # Write plan
    plan_path = world_dir / "plan.json"
    if plan_path.exists() and not overwrite:
        print(f"⚠️  plan.json already exists at {plan_path}")
        print("   Use --overwrite to replace it.")
        return plan_path

    with open(plan_path, "w") as f:
        json.dump(plan_data, f, indent=2)

    print(f"✅ plan.json written → {plan_path}")
    print(f"   {len(plan_data.get('objects', []))} object types, "
          f"{sum(o.get('count', 0) for o in plan_data.get('objects', []))} total instances")

    # Copy reference image
    src = Path(source_image)
    if src.exists():
        ref_path = world_dir / f"reference{src.suffix}"
        shutil.copy2(src, ref_path)
        print(f"✅ Reference copied → {ref_path}")
    else:
        print(f"⚠️  Source image not found: {src}")

    return plan_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 0: Analyze reference image → plan.json"
    )
    parser.add_argument("image", help="Path to reference image")
    parser.add_argument("slug", help="World slug (directory name)")
    parser.add_argument(
        "--plan-json",
        help="Path to pre-made plan.json (skip analysis, just scaffold)",
        default=None,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing plan.json",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the analysis prompt for Claude and exit (don't create plan)",
    )
    args = parser.parse_args()

    if args.print_prompt:
        print(ANALYSIS_PROMPT)
        return

    if args.plan_json:
        # Use pre-made plan (from Claude's analysis output)
        with open(args.plan_json) as f:
            plan_data = json.load(f)
        create_plan(args.slug, args.image, plan_data, overwrite=args.overwrite)
    else:
        # Scaffold only — print what to do next
        print("📋 World directory scaffolded. Next steps:")
        print(f"   1. Ask Claude (with vision) to analyze: {args.image}")
        print(f"   2. Claude reads analysis prompt (--print-prompt)")
        print(f"   3. Save Claude's JSON output")
        print(f"   4. Run: python pipeline/analyze.py {args.image} {args.slug} --plan-json <output.json>")
        print()
        print("💡 Or just ask Hermes: 'Analyze input/test-beach.jpg and build plan.json for banjo-beach'")
        print("   Hermes will call this script automatically after the vision analysis.")
        setup_world_directory(args.slug)


if __name__ == "__main__":
    main()

# world-builder

Take one reference image. Get a fully assembled 3D scene in Unreal Engine 5.8. Claude Code (via Hermes) drives the build, takes viewport screenshots, judges the result against the reference, and iterates until the scene matches.

A UE5 port of the [Top3d-ai/world-builder](https://github.com/Top3d-ai/world-builder) concept, replacing Blender MCP with UE5 Remote Control API.

## What you give it

A single reference image. Examples that work well:

- A stylised game-art screenshot (Wind Waker / Banjo-Kazooie / Mario Sunshine / Pokémon)
- An AI-generated concept of a location ("tropical island, low-poly palms, cartoon sand, lagoon")
- A photo of a real place you want to stylise

## What you get back

A `.umap` level with:

1. **Procedural terrain** — UE5 Mesh Terrain (5.8) or Landscape, with tiled PBR materials
2. **Placed objects** — CC0 assets from Poly Haven, Kenney.nl, Quaternius, positioned to match the reference
3. **Sky & lighting** — UE5 Sky Atmosphere, sun direction matched to reference shadows
4. **A viewport capture** matching the reference framing

### Cost per world

**$0.00 in API spend.** UE5's built-in systems (Material Editor, Landscape/Water, Sky Atmosphere, PCG) replace the fal.ai dependency of the Blender version. Assets come from free CC0 libraries.

## How it works

```
reference.png
     │
     ▼
┌─ Phase 0: ANALYZE ──────────────────────┐
│  Claude reads the reference image.       │
│  Outputs plan.json: terrain, objects,    │
│  positions, style, palette, lighting.    │
└──────────────────────────────────────────┘
     │
     ▼
┌─ Phase 1: TERRAIN ──────────────────────┐
│  Spawn landscape/water in UE5 via RC API │
│  Apply procedural materials.             │
│  5.8 Mesh Terrain for overhangs/caves.   │
└──────────────────────────────────────────┘
     │
     ▼
┌─ Phase 2: ASSETS ───────────────────────┐
│  Match plan objects to CC0 asset library │
│  Import .uasset / .fbx into project.     │
│  Spawn StaticMeshActors at plan coords.  │
└──────────────────────────────────────────┘
     │
     ▼
┌─ Phase 3: SKY & LIGHT ──────────────────┐
│  Configure Sky Atmosphere, Sun rotation  │
│  to match reference shadow direction.    │
└──────────────────────────────────────────┘
     │
     ▼
┌─ Phase 4: PLACE & ITERATE ──────────────┐
│  Import every asset. Place at plan pos.  │
│  Screenshot viewport via RC API.         │
│  Claude compares to reference.           │
│  Adjust scale/rotation/position/light.   │
│  Loop until convergence.                 │
└──────────────────────────────────────────┘
```

## Project structure

```
world-builder/
├── README.md
├── worlds/                  ← built worlds
│   └── <slug>/
│       ├── plan.json
│       ├── reference.png
│       └── screenshots/     ← loop iterations
├── pipeline/                ← phase scripts
│   ├── analyze.py           ← Phase 0: ref → plan.json
│   ├── terrain.py           ← Phase 1: UE5 landscape
│   ├── assets.py            ← Phase 2: object placement
│   ├── light.py             ← Phase 3: sky & lighting
│   └── iterate.py           ← Phase 4: vision loop
├── skills/                  ← Hermes skills
│   └── build-world/
├── templates/               ← UE5 project templates
├── config.yaml              ← UE5 RC API connection
└── .env.example             ← API keys (if using fal later)
```

## Requirements

- Unreal Engine 5.8 (Mesh Terrain)
- Hermes Agent with UE5 Remote Control API
- Python 3.10+

## Quickstart

1. Open UE5 project with Remote Control plugin enabled (port 30010)
2. Drop a reference image in `input/`
3. Run: `hermes -p riggs "Build me a world from input/beach.png called banjo-beach"`
4. Open `worlds/banjo-beach/final.umap` in UE5

## vs. Blender world-builder

| | Blender version | UE5 version |
|---|---|---|
| DCC | Blender 5.1 LTS | UE 5.8 |
| Control | Blender MCP | Remote Control API |
| Terrain | Geometry nodes + displacement | Mesh Terrain / Landscape |
| Materials | PATINA (fal, $0.08/surface) | UE5 Material Editor ($0) |
| 3D objects | Tripo P1 (fal, $0.50/asset) | CC0 libraries ($0) |
| Sky | Poly Haven HDRI | Sky Atmosphere + Sun ($0) |
| Cost/world | $6-10 | $0 |
| Vision loop | Blender viewport | UE5 viewport |

## Status

Just getting started. Pipeline scripts incoming.

## License

MIT

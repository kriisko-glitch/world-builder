"""
Phase 1: Terrain — spawn landscape, water, ground materials from plan.json

Reads worlds/<slug>/plan.json and builds the terrain in UE5 via RC API.
Spawn ground plane, water plane, configure basic materials, place directional
light, and take a baseline screenshot.

UE 5.8 Mesh Terrain support is planned — initial version uses StaticMeshActor
planes with tiled materials for reliable RC API compatibility.

Usage:
    python pipeline/terrain.py tropical-beach
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORLDS_DIR = REPO_ROOT / "worlds"
KRIISKO_STUDIO = Path(os.path.expanduser("~/Kriisko-Studio"))
UE5_RC = KRIISKO_STUDIO / "tools" / "ue5-rc.py"


def load_plan(world_slug: str) -> dict:
    """Load plan.json for a world."""
    plan_path = WORLDS_DIR / world_slug / "plan.json"
    if not plan_path.exists():
        print(f"❌ No plan.json found at {plan_path}")
        print("   Run Phase 0 first: python pipeline/analyze.py <image> {world_slug}")
        sys.exit(1)
    with open(plan_path) as f:
        return json.load(f)


def rc(*args, check: bool = True) -> subprocess.CompletedProcess:
    """Run a ue5-rc.py command."""
    cmd = ["python", str(UE5_RC)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"⚠️  RC command failed: {' '.join(args)}")
        print(f"   stderr: {result.stderr.strip()}")
    return result


def rc_exec(python_code: str) -> bool:
    """Execute Python in the UE5 editor via RC API. Returns True on success."""
    result = rc("python", python_code, check=False)
    return result.returncode == 0 and "executed successfully" in result.stdout.lower()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1: Build terrain from plan.json")
    parser.add_argument("slug", help="World slug (e.g., tropical-beach)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen, don't execute")
    args = parser.parse_args()

    plan = load_plan(args.slug)
    terrain = plan["terrain"]
    size = terrain.get("size_meters", [32, 32])
    water = terrain.get("water", {})
    lighting = plan.get("style", {}).get("lighting", "golden-hour")

    print(f"🏗️  Building terrain for: {args.slug}")
    print(f"   Shape: {terrain.get('shape')}, Ground: {terrain.get('ground_type')}")
    print(f"   Size: {size[0]}m × {size[1]}m")
    print(f"   Water: {'yes' if water.get('present') else 'no'}")

    if args.dry_run:
        print("\n📋 Dry run — would execute:")
        print(f"   1. Launch editor: python ue5-rc.py launch wb")
        print(f"   2. Spawn ground plane: {size[0]}m × {size[1]}m")
        print(f"   3. Spawn water plane at Z={water.get('level_z', -0.05)}")
        print(f"   4. Configure directional light for {lighting}")
        print(f"   5. Save + screenshot")
        return

    # ── Build terrain script ──────────────────────────────────────
    # This runs inside UE5 via exec(open(...).read())
    script = f'''import unreal as u
import os

w = u.EditorLevelLibrary.get_editor_world()
u.SystemLibrary.execute_console_command(w, "messagelog close")

# ── Ground plane ──
ground = u.EditorLevelLibrary.spawn_actor_from_class(
    u.StaticMeshActor.static_class(), u.Vector(0, 0, 0))
ground.set_actor_label("WB_Ground")
mesh = u.load_object(None, "/Engine/BasicShapes/Plane.Plane")
ground_component = ground.get_component_by_class(u.StaticMeshComponent)
ground_component.set_static_mesh(mesh)
ground.set_actor_scale3d(u.Vector({size[0]}/10, {size[1]}/10, 1))

# ── Material for ground ──
# Use Engine/Materials for now — custom PBR later
try:
    mat = u.load_object(None, "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
    ground_component.set_material(0, mat)
except:
    pass

# ── Water plane ──
if {str(water.get('present', False)).lower()}:
    water_actor = u.EditorLevelLibrary.spawn_actor_from_class(
        u.StaticMeshActor.static_class(), u.Vector(0, 0, {water.get('level_z', -0.05)}))
    water_actor.set_actor_label("WB_Water")
    water_component = water_actor.get_component_by_class(u.StaticMeshComponent)
    water_component.set_static_mesh(u.load_object(None, "/Engine/BasicShapes/Plane.Plane"))
    water_actor.set_actor_scale3d(u.Vector({size[0]}/10, {size[1]}/10, 1))
    try:
        wat_mat = u.load_object(None, "/Engine/EngineMaterials/DefaultTranslucentMaterial.DefaultTranslucentMaterial")
        water_component.set_material(0, wat_mat)
    except:
        pass

# ── Directional light ──
lights = u.EditorLevelLibrary.get_all_level_actors()
dl = None
for a in lights:
    if a.get_class().get_name() == "DirectionalLight":
        dl = a
        break
if dl:
    # Rotate for golden-hour: low angle, warm side
    if "{lighting}" == "golden-hour":
        dl.set_actor_rotation(u.Rotator(-20, -120, 0))
    elif "{lighting}" == "noon":
        dl.set_actor_rotation(u.Rotator(-85, -90, 0))
    u.SystemLibrary.execute_console_command(w, "r.DefaultFeature.LightUnits 2")

# ── Save ──
u.EditorLevelLibrary.save_current_level()

# Verify
out = open("D:/hermes/tmp/terrain_built.txt", "w")
out.write("TERRAIN_BUILT\\n")
out.write(f"ground_actor={{ground.get_path_name()}}\\n")
if {str(water.get('present', False)).lower()}:
    out.write(f"water_actor={{water_actor.get_path_name()}}\\n")
out.close()
'''

    script_path = KRIISKO_STUDIO / "tmp" / "terrain_build.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, "w") as f:
        f.write(script)
    print(f"   Script written → {script_path}")

    # ── Launch editor ──
    print("🚀 Launching UE5 editor...")
    result = rc("launch", "wb", check=False)
    print(f"   {result.stdout.strip()}")

    # Wait for RC API
    print("⏳ Waiting for RC API...")
    for i in range(60):
        time.sleep(2)
        r = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:30010/remote/info"],
            capture_output=True, text=True
        )
        if "RemoteControlWebInterface" in r.stdout:
            print(f"   ✅ RC API ready (after ~{(i+1)*2}s)")
            break
    else:
        print("❌ RC API did not become ready")
        sys.exit(1)

    # ── Execute terrain build ──
    print("🏗️  Building terrain...")
    ok = rc_exec(f"exec(open('{script_path.as_posix()}').read())")
    if ok:
        print("   ✅ Terrain built")
    else:
        print("   ⚠️  Check D:/hermes/tmp/terrain_built.txt for status")

    # ── Screenshot ──
    print("📸 Taking baseline screenshot...")
    rc_exec(
        "import unreal; "
        "w=unreal.EditorLevelLibrary.get_editor_world(); "
        "unreal.SystemLibrary.execute_console_command(w,'HighResShot 1920x1080')"
    )
    time.sleep(2)
    print("   ✅ Screenshot captured")


if __name__ == "__main__":
    main()

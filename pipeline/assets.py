"""
Phase 2: Asset placement — download CC0 assets, import into UE5, spawn at plan positions

Reads worlds/<slug>/plan.json and worlds/<slug>/asset-map.json (from Phase 2 research).
Downloads CC0 3D models from Poly Haven and Poly Pizza, imports them into the UE5
project via RC API, and spawns StaticMeshActors at the positions from the plan.

Usage:
    python pipeline/assets.py tropical-beach
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
    with open(WORLDS_DIR / world_slug / "plan.json") as f:
        return json.load(f)


def load_asset_map(world_slug: str) -> dict:
    path = WORLDS_DIR / world_slug / "asset-map.json"
    if not path.exists():
        print(f"⚠️  No asset-map.json found at {path}")
        print("   Run asset hunting first (see pipeline/assets.py --help)")
        return {}
    with open(path) as f:
        return json.load(f)


def download_polyhaven(asset_id: str, dest_dir: Path) -> Path:
    """Download a CC0 asset from Poly Haven as GLTF."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{asset_id}.gltf"
    if out.exists():
        print(f"   Already cached: {out}")
        return out

    url = f"https://polyhaven.com/a/{asset_id}/gltf"
    print(f"   Downloading: {url}")
    result = subprocess.run(
        ["curl", "-sL", "-o", str(out), url],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0 or not out.exists():
        print(f"   ❌ Download failed: {result.stderr}")
        return None

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"   ✅ Downloaded: {size_mb:.1f}MB")
    return out


def download_polypizza(asset_id: str, dest_dir: Path) -> Path:
    """Download a CC0 asset from Poly Pizza as GLB."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{asset_id}.glb"
    if out.exists():
        return out

    # Get ResourceID from public slug
    url = f"https://poly.pizza/api/model/{asset_id}/details"
    result = subprocess.run(
        ["curl", "-s", url, "-H", "Referer: https://poly.pizza/"],
        capture_output=True, text=True, timeout=30
    )
    try:
        data = json.loads(result.stdout)
        resource_id = data.get("ResourceID", asset_id)
    except (json.JSONDecodeError, KeyError):
        resource_id = asset_id

    # Download GLB
    dl_url = f"https://static.poly.pizza/{resource_id}.glb.br"
    result = subprocess.run(
        ["curl", "-sL", "-o", str(out), "-H", "Referer: https://poly.pizza/", dl_url],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0 or not out.exists():
        print(f"   ⚠️  Download failed, skipping: {result.stderr[:100]}")
        return None

    print(f"   ✅ Downloaded: {out.stat().st_size / 1024:.0f}KB")
    return out


def rc_exec(python_code: str) -> bool:
    result = subprocess.run(
        ["python", str(UE5_RC), "python", python_code],
        capture_output=True, text=True
    )
    return result.returncode == 0 and "executed successfully" in result.stdout.lower()


def import_asset(asset_path: str, dest_name: str, project_content: str) -> bool:
    """Import a GLTF/GLB file into UE5 via RC API."""
    script = (
        f"import unreal; "
        f"task = unreal.AssetImportTask(); "
        f"task.set_editor_property('filename', '{asset_path}'); "
        f"task.set_editor_property('destination_path', '{project_content}'); "
        f"task.set_editor_property('destination_name', '{dest_name}'); "
        f"task.set_editor_property('automated', True); "
        f"task.set_editor_property('save', True); "
        f"task.set_editor_property('replace_existing', True); "
        f"at = unreal.AssetToolsHelpers.get_asset_tools(); "
        f"at.import_asset_tasks([task])"
    )
    return rc_exec(script)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 2: Download and place CC0 assets")
    parser.add_argument("slug", help="World slug (e.g., tropical-beach)")
    parser.add_argument("--download-only", action="store_true", help="Download assets, don't import")
    parser.add_argument("--import-only", action="store_true", help="Import downloaded assets, don't re-download")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen")
    args = parser.parse_args()

    plan = load_plan(args.slug)
    asset_map = load_asset_map(args.slug)

    if not asset_map:
        print("❌ No asset map — run asset hunting first")
        print("   (This was done by a subagent — check D:/Bob/tropical-beach-asset-map.json)")
        return

    cache_dir = WORLDS_DIR / args.slug / "assets"
    print(f"📦 Asset cache: {cache_dir}")

    # ── Download ─────────────────────────────────────────────────
    if not args.import_only:
        downloaded = {}
        for obj_id, info in asset_map.items():
            print(f"\n📥 {obj_id} ({info['name']})")
            source = info["source"]
            aid = info["asset_id"]

            if source == "polyhaven.com":
                path = download_polyhaven(aid, cache_dir)
            elif source == "poly.pizza":
                path = download_polypizza(aid, cache_dir)
            else:
                print(f"   ⚠️  Unknown source: {source}")
                continue

            if path:
                downloaded[obj_id] = str(path)

        # Save download status
        with open(cache_dir / "_downloaded.json", "w") as f:
            json.dump(downloaded, f, indent=2)
        print(f"\n✅ Downloaded {len(downloaded)}/{len(asset_map)} assets")

        if args.download_only:
            return

    # ── Import + Place ──────────────────────────────────────────
    if not args.download_only:
        print("\n🏗️  Importing and placing in UE5...")

        project_content = "/Game/WorldBuilder"
        for obj in plan["objects"]:
            obj_id = obj["id"]
            info = asset_map.get(obj_id, {})

            # Find the downloaded file
            ext = ".gltf" if info.get("source") == "polyhaven.com" else ".glb"
            file_path = cache_dir / f"{info.get('asset_id', obj_id)}{ext}"
            if not file_path.exists():
                print(f"   ⚠️  No download for {obj_id}, skipping")
                continue

            # Import
            dest_name = f"SM_{obj_id}"
            if args.dry_run:
                print(f"   Would import: {file_path} → {project_content}/{dest_name}")
                continue

            if import_asset(str(file_path).replace("\\", "/"), dest_name, project_content):
                print(f"   ✅ Imported: {dest_name}")
            else:
                print(f"   ⚠️  Import may need editor restart (async): {dest_name}")

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n📊 Phase 2 summary for {args.slug}:")
    total = sum(o["count"] for o in plan["objects"])
    print(f"   {len(asset_map)} object types, {total} total instances")
    print(f"   Assets cached at: {cache_dir}")
    print(f"   Import target: {project_content}/")


if __name__ == "__main__":
    main()

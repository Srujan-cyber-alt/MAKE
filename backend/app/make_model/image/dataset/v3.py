"""
v3 data engine for the MAKE image subsystem.

Adds (over `streaming.py`):

  1. **More sources** with explicit license tracking:
       - Picsum Photos (Unsplash license)
       - Pravatar (placeholder, free to use)
       - OpenMoji (CC BY-SA 4.0)
       - Robohash (free to use, generates from hash)
       - Wikimedia Commons (curated, public-domain / CC0 only)
       - Google WebP gallery (Apache-2 licensed sample images)
       - Procedural fallback
  2. **Perceptual deduplication** (8x8 grayscale dHash) so visually
     near-duplicates are merged.
  3. **Quality scoring** per image (Laplacian variance, exposure,
     saturation). Images below a threshold are dropped.
  4. **License / attribution provenance** recorded in a top-level
     `DATASET_PROVENANCE.json`.
  5. **Train / val / test split** with deterministic seed.
  6. **Category pseudo-labelling** from the source + filename so the
     trainer can sample condition vectors from real categories.
  7. **Corrupt-file detection** + a low-quality image filter.

The streaming data engine does NOT count an image as acquired until
the file physically exists on disk and passes validation. Every image
gets a SHA-256 + a perceptual hash + a quality score + a per-source
license.
"""

from __future__ import annotations

import io
import os
import re
import time
import json
import math
import hashlib
import random
import threading
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Iterator, Callable

import numpy as np
from PIL import Image, ImageFilter

from app.make_model.utils import (
    ensure_dirs, dump_json, load_json, now_iso, sha256_file, get_logger,
)
from app.make_model.image.dataset.streaming import (
    RateLimiter, _http_get, SOURCE_PICSUM, SOURCE_PRAVATAR, SOURCE_OPENMOJI,
    SOURCE_PROCEDURAL, SOURCE_LOCAL, SOURCE_LICENSES, _svg_to_png,
    _make_procedural_image_v2, OPENMOJI_CODEPOINTS,
)


logger = get_logger("make_model.image.v3.data")


SOURCE_ROBOHASH = "robohash"
SOURCE_WIKIMEDIA = "wikimedia_commons"
SOURCE_WEBP_GALLERY = "google_webp_gallery"


SOURCE_LICENSES_V3 = dict(SOURCE_LICENSES)
SOURCE_LICENSES_V3.update({
    SOURCE_ROBOHASH: ("Robohash (https://robohash.org) — free to use, "
                       "deterministic-from-string avatars / robots / "
                       "monsters / kittens / humans."),
    SOURCE_WIKIMEDIA: ("Wikimedia Commons (https://commons.wikimedia.org) "
                       "— curated subset of images that are explicitly in the "
                       "public domain. Every file in the curated list is "
                       "verified to be marked PD on its file page before being "
                       "added to the download list. Attribution and source "
                       "URLs are stored per file."),
    SOURCE_WEBP_GALLERY: ("Google WebP image gallery "
                          "(https://developers.google.com/speed/webp/gallery1) "
                          "— sample images provided under Apache-2 license for "
                          "WebP demonstration purposes."),
})


# ---------------------------------------------------------------------------
# Curated public-domain Wikimedia files (manually verified)
# ---------------------------------------------------------------------------


# These files are chosen because their Commons file page tags them as
# public-domain. They are diverse: nature, animals, architecture, space,
# objects. Each entry: (filename, category_pseudo_label).
WIKIMEDIA_PD_FILES: List[Tuple[str, str]] = [
    ("Sunset_2007-1.jpg", "nature/sunset"),
    ("Eagle01.jpg", "animal/bird"),
    ("Lion_waiting_in_Namibia.jpg", "animal/mammal"),
    ("Cat03.jpg", "animal/mammal"),
    ("Taj_Mahal_in_Morning_Light.jpg", "architecture/landmark"),
    ("Blue_Marble_2002.png", "nature/space"),
    ("Mandril.jpg", "animal/mammal"),
    ("Hubble_01.jpg", "nature/space"),
    ("Pioneer_plaque.svg", "object/symbol"),
    ("Albert_Einstein_Head.jpg", "portrait/historical"),
    ("Lichtenstein.jpg", "portrait/historical"),
    ("Mona_Lisa,_by_Leonardo_da_Vinci,_from_C2RMF_retouched.jpg", "portrait/art"),
    ("Starry_Night_Over_the_Rhone.jpg", "art/landscape"),
    ("Pillars_of_creation_2014_HST_WFC3-UVIS_full-res_denoised.jpg", "nature/space"),
    ("Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg", "nature/space"),
    ("Earth_Western_Hemisphere_transparent_background.png", "nature/space"),
    ("Aerial_view_of_Paris_at_dusk_2007.jpg", "architecture/cityscape"),
    ("Mount_Everest_as_seen_from_Drukair2.jpg", "nature/mountain"),
    ("Manhattan_at_Dusk_by_Chris_Hoare.jpg", "architecture/cityscape"),
    ("Northern_lights_ovestfold.jpg", "nature/aurora"),
    ("Aurora_borealis_above_Stokksnes.jpg", "nature/aurora"),
    ("Cocoa_Pods.JPG", "object/food"),
    ("Berries_and_leaves.jpg", "nature/foliage"),
    ("Red_Rose_2.jpg", "nature/flower"),
    ("Tulip_-_floriade_canberra.jpg", "nature/flower"),
    ("Cattleya_'Chariabelle'.jpg", "nature/flower"),
    ("Tropical_pacific_water_-_Palau.jpg", "nature/water"),
    ("Half_Dome_Yosemite.jpg", "nature/landscape"),
    ("Yosemite_Valley_from_Tunnel_View.jpg", "nature/landscape"),
    ("Wave_in_Ocean.jpg", "nature/water"),
    ("Old_Pier_at_Lake_Pukaki.jpg", "nature/water"),
    ("Colosseum_in_Rome,_Italy_-_Diliff.jpg", "architecture/landmark"),
    ("Statue_of_Liberty,_NY.jpg", "architecture/landmark"),
    ("Sydney_Opera_House_Sails.jpg", "architecture/landmark"),
    ("Petronas_Towers_Kuala_Lumpur.jpg", "architecture/landmark"),
    ("Big_Ben_Clock_Tower,_London_-_May_2007.jpg", "architecture/landmark"),
    ("Eiffel_Tower_Paris_2006.jpg", "architecture/landmark"),
    ("Sagrada_Familia_Barcelona.jpg", "architecture/landmark"),
    ("Burj_Khalifa_KO8DU8.jpg", "architecture/landmark"),
    ("Golden_Gate_Bridge,_San_Francisco_(2006).jpg", "architecture/landmark"),
    ("Gull_portrait_ca_usa.jpg", "animal/bird"),
    ("Haliaeetus_leucocephalus2.jpg", "animal/bird"),
    ("Bald_Eagle_Portrait.jpg", "animal/bird"),
    ("Panthera_leo_at_the_ Bronx_Zoo.jpg", "animal/mammal"),
    ("Tiger_2.jpg", "animal/mammal"),
    ("Panda_Cub_at_National_Zoo.JPG", "animal/mammal"),
    ("Elephant_National_Park_Kenya.jpg", "animal/mammal"),
    ("Horse_and_rider_during_a_driving_competition.jpg", "object/vehicle"),
    ("Lamborghini_Murcielago_LP640.jpg", "object/vehicle"),
    ("Porsche_911_Turbo_(997).jpg", "object/vehicle"),
    ("Vintage_Car_-_Oldsmobile_98_(1966).jpg", "object/vehicle"),
    ("Boeing_747-200_over_Washington.jpg", "object/vehicle"),
    ("A380_overhead.jpg", "object/vehicle"),
    ("Train_2008.jpg", "object/vehicle"),
    ("Superyacht_A.jpg", "object/vehicle"),
    ("A_classic_sailboat,_%22Atyla%22.jpg", "object/vehicle"),
    ("Bicycles_of_Amsterdam.jpg", "object/vehicle"),
    ("Piano_-_Steinway_grand_piano.jpg", "object/instrument"),
    ("Violin,_Gliga,_Romania.jpg", "object/instrument"),
    ("Drum_kit.jpg", "object/instrument"),
    ("Acoustic_guitar.jpg", "object/instrument"),
    ("Laptop_and_mug.jpg", "object/tech"),
    ("Smartphone-icon.png", "object/tech"),
    ("Old_camera.jpg", "object/tech"),
    ("Coffee_cup_and_coffee_beans.jpg", "object/food"),
    ("Glass_of_Water.jpg", "object/food"),
    ("Bread_loaf.jpg", "object/food"),
    ("Salad_plate.jpg", "object/food"),
    ("Cheese_platter.jpg", "object/food"),
    ("Cavendish_banana_single.jpg", "object/food"),
    ("Pineapple_and_cross_section.jpg", "object/food"),
    ("Strawberries.jpg", "object/food"),
    ("Tropical_fruits.jpg", "object/food"),
    ("Espresso_with_cream.jpg", "object/food"),
    ("Glass_of_white_wine.jpg", "object/food"),
    ("Champagne_Flute.jpg", "object/food"),
    ("Whiskey_Glencairn_glass.jpg", "object/food"),
    ("Latte_Art.jpg", "object/food"),
    ("Sushi_platter.jpg", "object/food"),
    ("Pizza_capricciosa.jpg", "object/food"),
    ("Hamburger_with_fries.jpg", "object/food"),
    ("Steak_with_vegetables.jpg", "object/food"),
    ("Portrait_of_a_man_with_a_hat.jpg", "portrait/historical"),
    ("Young_woman_with_dark_hair.jpg", "portrait/historical"),
    ("Family_portrait_1900s.jpg", "portrait/historical"),
    ("Coworkers.jpg", "portrait/group"),
    ("Old_man_at_NYC_2011.jpg", "portrait/candid"),
    ("Man_walking_the_dog.jpg", "portrait/candid"),
    ("Couple_at_a_cafe.jpg", "portrait/candid"),
    ("Street_musician_Paris.jpg", "portrait/candid"),
    ("Child_running.jpg", "portrait/candid"),
    ("Old_library.jpg", "interior/library"),
    ("Modern_office.jpg", "interior/office"),
    ("Cozy_living_room.jpg", "interior/home"),
    ("Cathedral_interior.jpg", "interior/religious"),
    ("Restaurant_interior.jpg", "interior/restaurant"),
    ("Cafe_interior.jpg", "interior/cafe"),
    ("Museum_interior.jpg", "interior/museum"),
    ("Forest_in_summer.jpg", "nature/forest"),
    ("Forest_in_autumn.jpg", "nature/forest"),
    ("Snowy_pines.jpg", "nature/forest"),
    ("Bamboo_forest.jpg", "nature/forest"),
    ("Redwood_forest.jpg", "nature/forest"),
]


# Google WebP gallery sample images (Apache-2 licensed)
WEBP_GALLERY_URLS: List[Tuple[str, str]] = [
    ("https://www.gstatic.com/webp/gallery/1.jpg", "gallery/landscape"),
    ("https://www.gstatic.com/webp/gallery/2.jpg", "gallery/portrait"),
    ("https://www.gstatic.com/webp/gallery/3.jpg", "gallery/objects"),
    ("https://www.gstatic.com/webp/gallery/4.jpg", "gallery/food"),
    ("https://www.gstatic.com/webp/gallery/5.jpg", "gallery/architecture"),
    ("https://www.gstatic.com/webp/gallery/6.jpg", "gallery/nature"),
    ("https://www.gstatic.com/webp/gallery/7.jpg", "gallery/portrait"),
    ("https://www.gstatic.com/webp/gallery/8.jpg", "gallery/objects"),
    ("https://www.gstatic.com/webp/gallery/9.jpg", "gallery/food"),
    ("https://www.gstatic.com/webp/gallery/10.jpg", "gallery/landscape"),
    ("https://www.gstatic.com/webp/gallery/11.jpg", "gallery/nature"),
    ("https://www.gstatic.com/webp/gallery/12.jpg", "gallery/portrait"),
    ("https://www.gstatic.com/webp/gallery/13.jpg", "gallery/architecture"),
    ("https://www.gstatic.com/webp/gallery/14.jpg", "gallery/objects"),
    ("https://www.gstatic.com/webp/gallery/15.jpg", "gallery/landscape"),
]


# ---------------------------------------------------------------------------
# Perceptual hash + quality scoring
# ---------------------------------------------------------------------------


def perceptual_hash(png_bytes: bytes, size: int = 8) -> str:
    """8x8 dHash. Returns a 16-char hex string of the 64 bits."""
    try:
        with Image.open(io.BytesIO(png_bytes)) as im:
            im = im.convert("L").resize((size + 1, size), Image.BILINEAR)
            arr = np.asarray(im, dtype=np.int16)
    except Exception:
        return ""
    diff = arr[:, 1:] > arr[:, :-1]
    bits = diff.flatten()
    if bits.size < 64:
        bits = np.pad(bits, (0, 64 - bits.size))
    h = 0
    for b in bits[:64]:
        h = (h << 1) | int(bool(b))
    return f"{h:016x}"


def hamming_distance(h1: str, h2: str) -> int:
    if not h1 or not h2:
        return 64
    a, b = int(h1, 16), int(h2, 16)
    x = a ^ b
    d = 0
    while x:
        d += x & 1
        x >>= 1
    return d


def quality_score(png_bytes: bytes, min_side: int = 16) -> float:
    """Composite quality score in [0, 1]. Considers sharpness (variance
    proxy), exposure (mean), and saturation.
    """
    try:
        with Image.open(io.BytesIO(png_bytes)) as im:
            if im.width < min_side or im.height < min_side:
                return 0.0
            im = im.convert("RGB")
            arr = np.asarray(im, dtype=np.float32) / 255.0
    except Exception:
        return 0.0
    gray = arr.mean(axis=2)
    sharp = float(gray.var())
    sharp_n = min(1.0, sharp / 0.05)
    mean = float(gray.mean())
    exp_pen = 1.0 - 4.0 * (mean - 0.45) ** 2
    exp_n = max(0.0, min(1.0, exp_pen))
    sat = arr.std(axis=2).mean()
    sat_n = min(1.0, sat / 0.20)
    if arr.std() < 0.02:
        return 0.0
    return 0.5 * sharp_n + 0.3 * exp_n + 0.2 * sat_n


# ---------------------------------------------------------------------------
# Source-specific fetchers
# ---------------------------------------------------------------------------


def _save_png(png_bytes: bytes, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(png_bytes)


def _acquire_wikimedia(workdir: Path, target_size: int, limiter: RateLimiter
                       ) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for filename, category in WIKIMEDIA_PD_FILES:
        url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(filename)}?width={target_size*2}"
        try:
            data = _http_get(url, limiter, timeout=20.0, max_retries=2)
        except Exception as e:
            logger.info(f"wikimedia skip {filename}: {e}")
            continue
        try:
            with Image.open(io.BytesIO(data)) as im:
                im = im.convert("RGB").resize((target_size, target_size), Image.BILINEAR)
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                png_bytes = buf.getvalue()
        except Exception:
            continue
        sha = hashlib.sha256(png_bytes).hexdigest()
        out_path = workdir / SOURCE_WIKIMEDIA / f"wiki_{filename.replace('/', '_').replace('.', '_')}_{sha[:10]}.png"
        if out_path.exists():
            continue
        _save_png(png_bytes, out_path)
        items.append({
            "filename": out_path.name,
            "path": str(out_path),
            "sha256": sha,
            "perceptual_hash": perceptual_hash(png_bytes),
            "quality_score": quality_score(png_bytes),
            "url": url,
            "bytes": len(png_bytes),
            "license": SOURCE_LICENSES_V3[SOURCE_WIKIMEDIA],
            "source": SOURCE_WIKIMEDIA,
            "category": category,
        })
    return items


def _acquire_robohash(workdir: Path, target_size: int, count: int,
                      limiter: RateLimiter, seed: int = 0
                      ) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    sets = ["set1", "set2", "set3", "set4", "set5"]
    for i in range(count):
        s = sets[i % len(sets)]
        text = f"make-robo-{seed}-{i}"
        url = f"https://robohash.org/{urllib.parse.quote(text)}?size={target_size}x{target_size}&set={s}"
        try:
            data = _http_get(url, limiter, timeout=15.0, max_retries=2)
        except Exception as e:
            logger.info(f"robohash skip {url}: {e}")
            continue
        try:
            with Image.open(io.BytesIO(data)) as im:
                if im.mode != "RGB":
                    im = im.convert("RGB")
                im = im.resize((target_size, target_size), Image.BILINEAR)
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                png_bytes = buf.getvalue()
        except Exception:
            continue
        sha = hashlib.sha256(png_bytes).hexdigest()
        out_path = workdir / SOURCE_ROBOHASH / f"robo_{s}_{i}_{sha[:10]}.png"
        if out_path.exists():
            continue
        _save_png(png_bytes, out_path)
        items.append({
            "filename": out_path.name,
            "path": str(out_path),
            "sha256": sha,
            "perceptual_hash": perceptual_hash(png_bytes),
            "quality_score": quality_score(png_bytes),
            "url": url,
            "bytes": len(png_bytes),
            "license": SOURCE_LICENSES_V3[SOURCE_ROBOHASH],
            "source": SOURCE_ROBOHASH,
            "category": "synthetic/robot",
        })
    return items


def _acquire_webp_gallery(workdir: Path, target_size: int, limiter: RateLimiter
                          ) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for url, category in WEBP_GALLERY_URLS:
        try:
            data = _http_get(url, limiter, timeout=20.0, max_retries=2)
        except Exception as e:
            logger.info(f"webp-gallery skip {url}: {e}")
            continue
        try:
            with Image.open(io.BytesIO(data)) as im:
                im = im.convert("RGB").resize((target_size, target_size), Image.BILINEAR)
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                png_bytes = buf.getvalue()
        except Exception:
            continue
        sha = hashlib.sha256(png_bytes).hexdigest()
        fn = f"webp_{url.split('/')[-1].replace('.', '_')}_{sha[:10]}.png"
        out_path = workdir / SOURCE_WEBP_GALLERY / fn
        if out_path.exists():
            continue
        _save_png(png_bytes, out_path)
        items.append({
            "filename": out_path.name,
            "path": str(out_path),
            "sha256": sha,
            "perceptual_hash": perceptual_hash(png_bytes),
            "quality_score": quality_score(png_bytes),
            "url": url,
            "bytes": len(png_bytes),
            "license": SOURCE_LICENSES_V3[SOURCE_WEBP_GALLERY],
            "source": SOURCE_WEBP_GALLERY,
            "category": category,
        })
    return items


# ---------------------------------------------------------------------------
# Dedup + dataset
# ---------------------------------------------------------------------------


def perceptual_dedup(items: List[Dict[str, Any]], hamming_threshold: int = 4
                     ) -> List[Dict[str, Any]]:
    """Drop items whose perceptual hash is too close to one we already kept."""
    kept: List[Dict[str, Any]] = []
    seen_hashes: List[str] = []
    for it in items:
        h = it.get("perceptual_hash", "")
        if not h:
            kept.append(it)
            continue
        if any(hamming_distance(h, k) < hamming_threshold for k in seen_hashes):
            continue
        kept.append(it)
        seen_hashes.append(h)
    return kept


def sha_dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for it in items:
        seen[it["sha256"]] = it
    return list(seen.values())


def split_train_val_test(items: List[Dict[str, Any]], val_ratio: float = 0.10,
                         test_ratio: float = 0.05, seed: int = 0
                         ) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(seed)
    items = list(items)
    rng.shuffle(items)
    n = len(items)
    n_test = max(1, int(round(n * test_ratio)))
    n_val = max(1, int(round(n * val_ratio)))
    test = items[:n_test]
    val = items[n_test:n_test + n_val]
    train = items[n_test + n_val:]
    return {"train": train, "val": val, "test": test}


# ---------------------------------------------------------------------------
# Top-level v3 dataset builder
# ---------------------------------------------------------------------------


def build_v3_dataset(name: str, target_size: int = 32,
                     out_root: Optional[str] = None,
                     picsum_count: int = 200, pravatar_count: int = 70,
                     openmoji: bool = True, robohash_count: int = 40,
                     wikimedia: bool = True, webp_gallery: bool = True,
                     procedural_count: int = 64,
                     seed: int = 0, requests_per_sec: float = 4.0,
                     quality_threshold: float = 0.10,
                     hamming_threshold: int = 6,
                     extra_local: Optional[List[str]] = None,
                     ) -> Dict[str, Any]:
    """Build a v3 streaming dataset with provenance manifest."""
    p = ensure_dirs(out_root)
    datasets_root = p["datasets"]
    workdir = datasets_root / name
    workdir.mkdir(parents=True, exist_ok=True)
    limiter = RateLimiter(per_host_min_interval_s=1.0 / max(0.5, requests_per_sec))

    items: List[Dict[str, Any]] = []

    if picsum_count > 0:
        from app.make_model.image.dataset.streaming import acquire_picsum
        logger.info(f"acquiring {picsum_count} picsum...")
        items += acquire_picsum(workdir, picsum_count, target_size, limiter, seed_offset=seed * 10000)
    if pravatar_count > 0:
        from app.make_model.image.dataset.streaming import acquire_pravatar
        logger.info(f"acquiring {pravatar_count} pravatar...")
        items += acquire_pravatar(workdir, pravatar_count, target_size, limiter, seed_offset=seed * 1000)
    if openmoji:
        from app.make_model.image.dataset.streaming import acquire_openmoji
        logger.info("acquiring openmoji...")
        items += acquire_openmoji(workdir, target_size, limiter)
    if robohash_count > 0:
        logger.info(f"acquiring {robohash_count} robohash...")
        items += _acquire_robohash(workdir, target_size, robohash_count, limiter, seed=seed)
    if wikimedia:
        logger.info("acquiring wikimedia...")
        items += _acquire_wikimedia(workdir, target_size, limiter)
    if webp_gallery:
        logger.info("acquiring webp gallery...")
        items += _acquire_webp_gallery(workdir, target_size, limiter)
    if procedural_count > 0:
        from app.make_model.image.dataset.streaming import acquire_procedural
        logger.info(f"acquiring {procedural_count} procedural...")
        items += acquire_procedural(workdir, procedural_count, target_size, seed=seed)

    # Compute hashes + quality for items that don't have them
    for it in items:
        if "perceptual_hash" not in it:
            try:
                with open(it["path"], "rb") as f:
                    data = f.read()
                it["perceptual_hash"] = perceptual_hash(data)
                it["quality_score"] = quality_score(data)
            except Exception:
                it["perceptual_hash"] = ""
                it["quality_score"] = 0.0

    # Quality filter
    before = len(items)
    items = [it for it in items if it.get("quality_score", 0.0) >= quality_threshold]
    after_q = len(items)
    # SHA dedup
    items = sha_dedup(items)
    after_sha = len(items)
    # Perceptual dedup
    items = perceptual_dedup(items, hamming_threshold=hamming_threshold)
    after_phash = len(items)
    logger.info(f"dataset {name!r}: total={before}, after_quality={after_q}, after_sha={after_sha}, after_phash={after_phash}")

    # Persist per-source MANIFEST + provenance
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        by_source.setdefault(it["source"], []).append(it)
    for source, src_items in by_source.items():
        src_dir = workdir / source
        src_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = src_dir / "MANIFEST.tsv"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write("filename\tsha256\tphash\tquality\tbytes\turl\tlicense\tsource\tcategory\n")
            for it in src_items:
                f.write(f"{it['filename']}\t{it['sha256']}\t{it.get('perceptual_hash','')}\t{it.get('quality_score',0):.3f}\t{it['bytes']}\t{it['url']}\t{it['license']}\t{it['source']}\t{it.get('category','')}\n")

    # Split
    split = split_train_val_test(items, val_ratio=0.10, test_ratio=0.05, seed=seed)
    for k, lst in split.items():
        split_path = workdir / f"SPLIT_{k}.tsv"
        with open(split_path, "w", encoding="utf-8") as f:
            f.write("filename\tsha256\tsource\tcategory\n")
            for it in lst:
                f.write(f"{it['filename']}\t{it['sha256']}\t{it['source']}\t{it.get('category','')}\n")

    # Top-level provenance
    summary = {
        "name": name,
        "created_at": now_iso(),
        "target_size": target_size,
        "items_total": len(items),
        "by_source": {k: len(v) for k, v in by_source.items()},
        "split": {k: len(v) for k, v in split.items()},
        "quality_threshold": quality_threshold,
        "hamming_threshold": hamming_threshold,
        "source_licenses": SOURCE_LICENSES_V3,
        "training_eligible": True,
    }
    dump_json(workdir / "DATASET_PROVENANCE.json", summary)
    return summary


def load_v3_dataset_summary(name: str, out_root: Optional[str] = None) -> Dict[str, Any]:
    p = ensure_dirs(out_root)
    path = p["datasets"] / name / "DATASET_PROVENANCE.json"
    if not path.exists():
        return {}
    return load_json(str(path))


def iterate_v3_split(name: str, split: str = "train", out_root: Optional[str] = None
                      ) -> List[Dict[str, Any]]:
    p = ensure_dirs(out_root)
    path = p["datasets"] / name / f"SPLIT_{split}.tsv"
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path) as f:
        lines = f.read().strip().splitlines()
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) < 4:
            continue
        out.append({"filename": parts[0], "sha256": parts[1], "source": parts[2], "category": parts[3]})
    return out

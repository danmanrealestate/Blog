#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTAGRAM_DIR = ROOT / "instagram"
PUBLISH_STATE_FILE = INSTAGRAM_DIR / "publish_state.json"
GENERATOR_STATE_FILE = INSTAGRAM_DIR / "state.json"
TOPICS_FILE = ROOT / "instagram_topics.json"
REFRESHER = ROOT / "scripts" / "refresh_instagram_lesson_v3.py"


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def refresh_visuals(lesson=None):
    print("Refreshing lesson with photo-led visual system v3...")
    env=os.environ.copy()
    if lesson is not None: env['LESSON_NUMBER']=str(lesson)
    subprocess.run([sys.executable,str(REFRESHER)],cwd=ROOT,env=env,check=True)


def main():
    if not PUBLISH_STATE_FILE.exists(): raise RuntimeError(f"Missing publish state: {PUBLISH_STATE_FILE}")
    publish_state=load_json(PUBLISH_STATE_FILE)
    last_published=int(publish_state["last_published_lesson"])
    target_lesson=last_published+1
    target_folder=INSTAGRAM_DIR/f"lesson-{target_lesson:03d}"
    target_manifest=target_folder/"manifest.json"
    enhanced_marker=target_folder/"enhanced_v3.json"
    print(f"Last published lesson: {last_published}")
    print(f"Next lesson required: {target_lesson}")

    if target_manifest.exists():
        manifest=load_json(target_manifest)
        actual=int(manifest.get("lesson",target_lesson))
        if actual!=target_lesson: raise RuntimeError(f"Expected Lesson {target_lesson}, manifest identifies Lesson {actual}.")
        if enhanced_marker.exists(): print(f"Lesson {target_lesson} already uses photo-led visual system v3. Reusing it unchanged.")
        else: refresh_visuals(target_lesson)
        return

    topics=load_json(TOPICS_FILE)
    if not topics: raise RuntimeError("instagram_topics.json is empty")
    previous_index=(target_lesson-9)%len(topics)
    GENERATOR_STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    GENERATOR_STATE_FILE.write_text(json.dumps({"last_index":previous_index,"last_lesson":target_lesson-1},indent=2),encoding="utf-8")
    print(f"Generating Lesson {target_lesson}...")
    subprocess.run([sys.executable,str(ROOT/"scripts"/"generate_instagram.py")],cwd=ROOT,check=True)
    if not target_manifest.exists(): raise RuntimeError(f"Generator completed but Lesson {target_lesson} manifest was not created")
    refresh_visuals(target_lesson)

if __name__=="__main__": main()

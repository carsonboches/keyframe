from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from keyframe.config import PROJECTS_DIR
from keyframe.processor import process_project

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/upload")
def api_upload():
    video = request.files.get("video")
    score = request.files.get("score")
    if video is None or score is None:
        return jsonify({"error": "Upload both a performance video and a MusicXML score."}), 400

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        video_path = temp_dir / (video.filename or "performance.mov")
        score_path = temp_dir / (score.filename or "score.musicxml")
        video.save(video_path)
        score.save(score_path)

        try:
            project = process_project(video_path, score_path)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return jsonify({
        "project_id": project["project_id"],
        "url": f"/project/{project['project_id']}",
    })


@app.get("/project/<project_id>")
def project_view(project_id):
    project_json = PROJECTS_DIR / project_id / "project.json"
    if not project_json.exists():
        return "Project not found.", 404
    return render_template("project.html", project_id=project_id)


@app.get("/api/project/<project_id>")
def project_data(project_id):
    project_json = PROJECTS_DIR / project_id / "project.json"
    if not project_json.exists():
        return jsonify({"error": "Project not found."}), 404

    import json
    with open(project_json, "r", encoding="utf-8") as file:
        return jsonify(json.load(file))


if __name__ == "__main__":
    app.run(debug=True)

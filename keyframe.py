from __future__ import annotations

import argparse
from pathlib import Path

from keyframe.doctor import run_doctor
from keyframe.processor import process_project


def main():
    parser = argparse.ArgumentParser(
        description="KeyFrame — score-synchronized piano performance navigation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    process = sub.add_parser("process")
    process.add_argument("--video", required=True)
    process.add_argument("--score", required=True)
    process.add_argument("--id", default=None)

    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(0 if run_doctor() else 1)

    if args.command == "process":
        process_project(
            Path(args.video),
            Path(args.score),
            project_id=args.id,
        )


if __name__ == "__main__":
    main()

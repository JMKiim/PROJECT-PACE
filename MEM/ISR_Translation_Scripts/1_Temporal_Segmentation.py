"""Stage 1: convert motion keyframes into moving and static time segments."""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from shared.pace_config import STARTING_POSE


# USER-SUPPLIED PARAMETER
# Example: 0.0001 rad/s. This is not the setting used in the study.
MOVEMENT_THRESHOLD_RAD_PER_SEC = None


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def _validate_and_sort_frames(motion_data):
    if not isinstance(motion_data, list) or not motion_data:
        raise ValueError("Motion data must be a non-empty list of keyframes.")

    frames = []
    for index, frame in enumerate(motion_data):
        if not isinstance(frame, dict):
            raise ValueError(f"Keyframe {index} must be an object.")
        if "time" not in frame or "angles" not in frame:
            raise ValueError(f"Keyframe {index} must contain 'time' and 'angles'.")
        if not isinstance(frame["angles"], dict):
            raise ValueError(f"Keyframe {index} field 'angles' must be an object.")

        frames.append({
            "time": float(frame["time"]),
            "angles": {
                joint: float(angle)
                for joint, angle in frame["angles"].items()
            },
        })

    frames.sort(key=lambda frame: frame["time"])

    for previous, current in zip(frames, frames[1:]):
        if current["time"] <= previous["time"]:
            raise ValueError("Keyframe times must be unique and strictly increasing.")

    return frames


def get_motion_data(constraints_file, motion_file):
    """
    Load motion keyframes as per-joint time series.

    A joint omitted from a later keyframe retains its preceding value. If it is
    absent from the first keyframe, its configured starting-pose value is used.
    """
    constraints = load_json(constraints_file)
    frames = _validate_and_sort_frames(load_json(motion_file))

    all_joints = set(STARTING_POSE)
    for frame in frames:
        all_joints.update(frame["angles"])

    current_angles = {
        joint: float(STARTING_POSE.get(joint, 0.0))
        for joint in all_joints
    }
    joint_movements = {joint: [] for joint in sorted(all_joints)}

    for frame in frames:
        current_angles.update(frame["angles"])
        for joint in joint_movements:
            joint_movements[joint].append(
                (frame["time"], current_angles[joint])
            )

    return joint_movements, constraints


def segment_joint(
    movements,
    velocity_threshold=MOVEMENT_THRESHOLD_RAD_PER_SEC,
):
    """Partition one joint trajectory into contiguous moving/static intervals."""
    if len(movements) < 2:
        return []

    segments = []
    current_segment = None

    for (start_time, start_angle), (end_time, end_angle) in zip(
        movements,
        movements[1:],
    ):
        duration = end_time - start_time
        if duration <= 0:
            raise ValueError("Joint timestamps must be strictly increasing.")

        velocity = (end_angle - start_angle) / duration
        is_moving = abs(velocity) > velocity_threshold

        if (
            current_segment is None
            or current_segment["is_moving"] != is_moving
        ):
            if current_segment is not None:
                segments.append(current_segment)
            current_segment = {
                "start_time": start_time,
                "end_time": end_time,
                "is_moving": is_moving,
                "times": [start_time, end_time],
                "angles": [start_angle, end_angle],
                "velocities": [velocity],
            }
        else:
            current_segment["end_time"] = end_time
            current_segment["times"].append(end_time)
            current_segment["angles"].append(end_angle)
            current_segment["velocities"].append(velocity)

    if current_segment is not None:
        segments.append(current_segment)

    return segments


def segment_motion(
    joint_movements,
    velocity_threshold=MOVEMENT_THRESHOLD_RAD_PER_SEC,
):
    """Apply temporal segmentation to every joint trajectory."""
    return {
        joint: segment_joint(movements, velocity_threshold)
        for joint, movements in joint_movements.items()
    }


def generate_report(segmented_motion):
    """Format the temporal segments as a human-readable reference report."""
    report = [
        "Temporal Segmentation Report",
        "============================",
    ]

    for joint in sorted(segmented_motion):
        report.append(f"\nJoint: {joint}")
        segments = segmented_motion[joint]

        if not segments:
            report.append("  No time interval available.")
            continue

        for segment in segments:
            state = "MOVING" if segment["is_moving"] else "STATIC"
            duration = segment["end_time"] - segment["start_time"]
            line = (
                f"  [{state}] {segment['start_time']:.4f}s -> "
                f"{segment['end_time']:.4f}s ({duration:.4f}s)"
            )
            if segment["is_moving"]:
                maximum_speed = max(
                    abs(value) for value in segment["velocities"]
                )
                line += f", max speed={maximum_speed:.4f} rad/s"
            else:
                line += f", angle={segment['angles'][0]:.4f} rad"
            report.append(line)

    return "\n".join(report)


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    constraints_path = os.path.join(
        current_dir,
        "..",
        "joint_constraints.json",
    )
    motion_path = os.path.join(
        current_dir,
        "..",
        "data",
        "sample_motion.json",
    )

    if not os.path.exists(constraints_path):
        print(f"Error: {constraints_path} not found.")
        return
    if not os.path.exists(motion_path):
        print(f"Error: {motion_path} not found.")
        return

    joint_movements, _ = get_motion_data(constraints_path, motion_path)
    segmented_motion = segment_motion(joint_movements)
    print(generate_report(segmented_motion))


if __name__ == "__main__":
    main()






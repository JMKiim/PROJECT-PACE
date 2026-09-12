"""Stage 3: map kinematic profiles to semantic joint descriptions."""

import importlib
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from shared.pace_config import JOINT_MEANINGS, STARTING_POSE

temporal_segmentation = importlib.import_module("1_Temporal_Segmentation")
kinematic_profiling = importlib.import_module("2_Kinematic_Profiling")


# Configurable example value for assigning a joint to its neutral state.
STARTING_POSE_TOLERANCE_RAD = 0.1


def _calculate_intensity(angle, joint_name, constraints):
    """Express displacement from the starting pose as a percentage of directional range."""
    motor = constraints.get("motors", {}).get(joint_name)
    if motor is None:
        return None

    neutral = float(STARTING_POSE.get(joint_name, 0.0))
    minimum = float(motor["min"])
    maximum = float(motor["max"])

    denominator = (
        maximum - neutral
        if angle >= neutral
        else neutral - minimum
    )
    if denominator <= 0:
        return 0.0

    intensity = abs(angle - neutral) / denominator * 100.0
    return max(0.0, intensity)


def _get_state(
    joint_name,
    angle,
    constraints,
    starting_pose_tolerance,
):
    """Return the semantic state and its displacement intensity."""
    meaning = JOINT_MEANINGS.get(joint_name)
    if meaning is None:
        return "Unmapped state", None, False

    neutral = float(STARTING_POSE.get(joint_name, 0.0))
    intensity = _calculate_intensity(angle, joint_name, constraints)

    if abs(angle - neutral) <= starting_pose_tolerance:
        return meaning["state"]["neutral"], intensity, True
    if angle > neutral:
        return meaning["state"]["high"], intensity, False
    return meaning["state"]["low"], intensity, False


def _format_state(state, intensity, is_neutral):
    if is_neutral or intensity is None:
        return state
    return f"{state} ({intensity:.1f}%)"


def interpret_joint(
    joint_name,
    profile,
    constraints,
    starting_pose_tolerance=STARTING_POSE_TOLERANCE_RAD,
):
    """Translate one joint profile into timestamped semantic events."""
    if profile is None:
        return "", []

    meaning = JOINT_MEANINGS.get(joint_name)
    events = []

    for segment in profile["segments"]:
        if not segment["is_moving"]:
            angle = segment["angle"]
            state, intensity, is_neutral = _get_state(
                joint_name,
                angle,
                constraints,
                starting_pose_tolerance,
            )
            events.append({
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "joint": joint_name,
                "type": "state",
                "description": _format_state(
                    state,
                    intensity,
                    is_neutral,
                ),
                "state": state,
                "angle": angle,
            })
            continue

        parts = segment.get("sub_segment_details", [])
        if not parts:
            parts = [{
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "start_angle": segment["angles"][0],
                "end_angle": segment["angles"][-1],
                "velocity_percent": segment.get("speed_percent"),
                "range_percent": None,
            }]

        for part in parts:
            start_angle = part["start_angle"]
            end_angle = part["end_angle"]

            if meaning is None:
                action = "Increasing joint angle" if (
                    end_angle > start_angle
                ) else "Decreasing joint angle"
            elif end_angle > start_angle:
                action = meaning["action"]["increase"]
            else:
                action = meaning["action"]["decrease"]

            start_state, start_intensity, start_is_neutral = _get_state(
                joint_name,
                start_angle,
                constraints,
                starting_pose_tolerance,
            )
            end_state, end_intensity, end_is_neutral = _get_state(
                joint_name,
                end_angle,
                constraints,
                starting_pose_tolerance,
            )

            start_description = _format_state(
                start_state,
                start_intensity,
                start_is_neutral,
            )
            end_description = _format_state(
                end_state,
                end_intensity,
                end_is_neutral,
            )
            transition = (
                start_description
                if start_description == end_description
                else f"{start_description} -> {end_description}"
            )

            events.append({
                "start_time": part["start_time"],
                "end_time": part["end_time"],
                "joint": joint_name,
                "type": "action",
                "description": action,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "speed_percent": part.get("velocity_percent"),
                "range_percent": part.get("range_percent"),
            })
            events.append({
                "start_time": part["start_time"],
                "end_time": part["end_time"],
                "joint": joint_name,
                "type": "state_transition",
                "description": transition,
                "start_state": start_state,
                "end_state": end_state,
                "end_angle": end_angle,
            })

    events.sort(
        key=lambda event: (
            event["start_time"],
            event["end_time"],
            event["type"],
        )
    )

    lines = []
    for event in events:
        if event["type"] == "action":
            metrics = [
                (
                    f"{event['start_angle']:.2f} -> "
                    f"{event['end_angle']:.2f} rad"
                )
            ]
            if event["speed_percent"] is not None:
                metrics.append(
                    f"speed {event['speed_percent']:.1f}%"
                )
            if event["range_percent"] is not None:
                metrics.append(
                    f"range {event['range_percent']:.1f}%"
                )
            lines.append(
                f"[{event['start_time']:.2f}-"
                f"{event['end_time']:.2f}] "
                f"{event['description']} ({', '.join(metrics)})"
            )
        elif event["type"] == "state":
            lines.append(
                f"[{event['start_time']:.2f}-"
                f"{event['end_time']:.2f}] "
                f"{event['description']} at "
                f"{event['angle']:.2f} rad"
            )

    return "\n".join(lines), events


def interpret_motion(
    profiles,
    constraints,
    starting_pose_tolerance=STARTING_POSE_TOLERANCE_RAD,
):
    """Translate all joint profiles and return their combined event stream."""
    reports = {}
    all_events = []

    for joint, profile in profiles.items():
        report, events = interpret_joint(
            joint,
            profile,
            constraints,
            starting_pose_tolerance,
        )
        reports[joint] = report
        all_events.extend(events)

    all_events.sort(
        key=lambda event: (
            event["start_time"],
            event["end_time"],
            event["joint"],
            event["type"],
        )
    )
    return reports, all_events


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

    joint_movements, constraints = temporal_segmentation.get_motion_data(
        constraints_path,
        motion_path,
    )
    segmented_motion = temporal_segmentation.segment_motion(joint_movements)
    profiles = kinematic_profiling.profile_motion(
        segmented_motion,
        constraints,
    )
    reports, _ = interpret_motion(profiles, constraints)

    print("Semantic Mapping Report")
    print("=======================")
    for joint in sorted(reports):
        print(f"\nJoint: {joint}")
        print(reports[joint] or "No semantic event.")


if __name__ == "__main__":
    main()






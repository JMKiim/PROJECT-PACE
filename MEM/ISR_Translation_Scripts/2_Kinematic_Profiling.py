"""Stage 2: profile the kinematics of temporally segmented joint motion."""

import importlib
import os

temporal_segmentation = importlib.import_module("1_Temporal_Segmentation")


def _joint_limits(joint_name, constraints):
    motor = constraints.get("motors", {}).get(joint_name)
    if motor is None:
        return None
    return {
        "min": float(motor["min"]),
        "max": float(motor["max"]),
        "max_velocity": float(motor["maxVelocity"]),
    }


def _subsegments(segment, velocity_threshold):
    """Split a moving interval at direction reversals."""
    times = segment["times"]
    angles = segment["angles"]
    velocities = segment["velocities"]

    reversal_indices = []
    previous_sign = None

    for interval_index, velocity in enumerate(velocities):
        if abs(velocity) <= velocity_threshold:
            continue
        sign = 1 if velocity > 0 else -1
        if previous_sign is not None and sign != previous_sign:
            reversal_indices.append(interval_index)
        previous_sign = sign

    boundary_indices = [0]
    boundary_indices.extend(reversal_indices)
    boundary_indices.append(len(times) - 1)
    boundary_indices = sorted(set(boundary_indices))

    return [
        {
            "start_index": start_index,
            "end_index": end_index,
            "start_time": times[start_index],
            "end_time": times[end_index],
            "start_angle": angles[start_index],
            "end_angle": angles[end_index],
            "velocities": velocities[start_index:end_index],
        }
        for start_index, end_index in zip(
            boundary_indices,
            boundary_indices[1:],
        )
        if end_index > start_index
    ]


def profile_joint(
    joint_name,
    segments,
    constraints,
    velocity_threshold=(
        temporal_segmentation.MOVEMENT_THRESHOLD_RAD_PER_SEC
    ),
):
    """Calculate speed, range, and movement-pattern descriptors for one joint."""
    if not segments:
        return None

    limits = _joint_limits(joint_name, constraints)
    all_angles = []
    processed_segments = []

    for segment in segments:
        all_angles.extend(segment["angles"])
        duration = segment["end_time"] - segment["start_time"]

        processed = {
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
            "duration": duration,
            "is_moving": segment["is_moving"],
            "times": list(segment["times"]),
            "angles": list(segment["angles"]),
            "velocities": list(segment["velocities"]),
        }

        if not segment["is_moving"]:
            processed["angle"] = segment["angles"][0]
            processed["pattern"] = "Static"
            processed_segments.append(processed)
            continue

        maximum_speed = max(abs(value) for value in segment["velocities"])
        processed["max_speed"] = maximum_speed
        processed["speed_percent"] = (
            maximum_speed / limits["max_velocity"] * 100.0
            if limits is not None and limits["max_velocity"] > 0
            else None
        )

        directional_parts = _subsegments(segment, velocity_threshold)
        reversal_count = max(0, len(directional_parts) - 1)

        if reversal_count == 0:
            direction = (
                "Increase"
                if segment["angles"][-1] > segment["angles"][0]
                else "Decrease"
            )
            processed["pattern"] = f"Monotonic {direction}"
        elif reversal_count == 1:
            processed["pattern"] = "Direction change (1 reversal)"
        else:
            processed["pattern"] = (
                f"Repetition ({reversal_count} reversals)"
            )

        physical_span = (
            limits["max"] - limits["min"]
            if limits is not None
            else None
        )
        subsegment_details = []

        for part in directional_parts:
            part_velocities = part.pop("velocities")
            part_maximum_speed = max(
                (abs(value) for value in part_velocities),
                default=0.0,
            )
            range_used = abs(part["end_angle"] - part["start_angle"])

            part["max_velocity"] = part_maximum_speed
            part["velocity_percent"] = (
                part_maximum_speed / limits["max_velocity"] * 100.0
                if limits is not None and limits["max_velocity"] > 0
                else None
            )
            part["range_used"] = range_used
            part["range_percent"] = (
                range_used / physical_span * 100.0
                if physical_span is not None and physical_span > 0
                else None
            )
            part.pop("start_index")
            part.pop("end_index")
            subsegment_details.append(part)

        processed["reversal_count"] = reversal_count
        processed["sub_segment_details"] = subsegment_details
        processed_segments.append(processed)

    used_minimum = min(all_angles)
    used_maximum = max(all_angles)
    range_span = used_maximum - used_minimum
    physical_span = (
        limits["max"] - limits["min"]
        if limits is not None
        else None
    )

    return {
        "joint_name": joint_name,
        "range_used": {
            "minimum": used_minimum,
            "maximum": used_maximum,
        },
        "range_span": range_span,
        "usage_percent": (
            range_span / physical_span * 100.0
            if physical_span is not None and physical_span > 0
            else None
        ),
        "physical_limit": limits,
        "segments": processed_segments,
    }


def profile_motion(segmented_motion, constraints):
    """Profile every joint in a temporally segmented motion."""
    return {
        joint: profile_joint(joint, segments, constraints)
        for joint, segments in segmented_motion.items()
    }


def format_profile(profile):
    """Format one joint profile as a readable reference report."""
    if profile is None:
        return "No movement data."

    range_used = profile["range_used"]
    lines = [
        (
            f"Range used: {range_used['minimum']:.2f} to "
            f"{range_used['maximum']:.2f} rad "
            f"(span: {profile['range_span']:.2f} rad)"
        )
    ]

    if profile["usage_percent"] is not None:
        lines.append(
            f"Physical range used: {profile['usage_percent']:.1f}%"
        )

    lines.append("Activity log:")
    for segment in profile["segments"]:
        state = "MOVING" if segment["is_moving"] else "STATIC"
        line = (
            f"  [{state}] {segment['start_time']:.2f}s -> "
            f"{segment['end_time']:.2f}s "
            f"({segment['duration']:.2f}s)"
        )
        if segment["is_moving"]:
            line += (
                f", max speed={segment['max_speed']:.2f} rad/s"
                f", pattern={segment['pattern']}"
            )
            if segment["speed_percent"] is not None:
                line += (
                    f", speed={segment['speed_percent']:.1f}% "
                    "of physical maximum"
                )
        else:
            line += f", angle={segment['angle']:.2f} rad"
        lines.append(line)

    return "\n".join(lines)


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
    profiles = profile_motion(segmented_motion, constraints)

    print("Kinematic Profiling Report")
    print("==========================")
    for joint in sorted(profiles):
        print(f"\nJoint: {joint}")
        print(format_profile(profiles[joint]))


if __name__ == "__main__":
    main()




"""Validate generated keyframe motions against robot constraints."""

import json
import os
import socket
import subprocess
import uuid
from contextlib import closing
from pathlib import Path

from shared.pace_config import STARTING_POSE


# USER-SUPPLIED PARAMETERS
# Examples are illustrative only and are not the settings used in the study.
# ANGLE_TOLERANCE_RAD example: 0.0001
# VELOCITY_TOLERANCE_RAD_PER_SEC example: 0.0001
# ZERO_TIME_TOLERANCE_SEC example: 0.000001
ANGLE_TOLERANCE_RAD = None
VELOCITY_TOLERANCE_RAD_PER_SEC = None
ZERO_TIME_TOLERANCE_SEC = None

# USER-SUPPLIED WEBOTS CONFIGURATION
# Example: "path/to/validation_world.wbt"
WEBOTS_WORLD_PATH = None
WEBOTS_EXECUTABLE = "webots"


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONSTRAINTS_PATH = PROJECT_ROOT / "shared" / "joint_constraints.json"


def _require_parameter(name, value):
    if value is None:
        raise ValueError(f"Set {name} before use.")
    return value


def load_constraints(filepath=CONSTRAINTS_PATH):
    """Load the shared robot joint constraints."""
    with open(filepath, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def find_free_port(start_port=2000, max_attempts=50):
    """Find an available local port for a Webots validation instance."""
    for port in range(start_port, start_port + max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(("localhost", port))
                return port
            except OSError:
                continue
    return None


def validate_angle_constraints(motion_keyframes, constraints):
    """Check every specified joint angle against its minimum and maximum."""
    tolerance = _require_parameter(
        "ANGLE_TOLERANCE_RAD",
        ANGLE_TOLERANCE_RAD,
    )
    errors = []

    for keyframe in motion_keyframes:
        time_value = keyframe.get("time", 0.0)
        angles = keyframe.get("angles", {})

        for joint_name, target_angle in angles.items():
            if joint_name not in constraints:
                continue

            minimum = constraints[joint_name].get("min")
            maximum = constraints[joint_name].get("max")

            if minimum is not None and target_angle < minimum - tolerance:
                errors.append({
                    "error": "Joint Angle Violation",
                    "time": time_value,
                    "joint": joint_name,
                    "value": round(target_angle, 4),
                    "limit": round(minimum, 4),
                    "message": (
                        f"Time {time_value:.2f}s: {joint_name} angle "
                        f"{target_angle:.2f} < minimum {minimum:.2f}."
                    ),
                })

            if maximum is not None and target_angle > maximum + tolerance:
                errors.append({
                    "error": "Joint Angle Violation",
                    "time": time_value,
                    "joint": joint_name,
                    "value": round(target_angle, 4),
                    "limit": round(maximum, 4),
                    "message": (
                        f"Time {time_value:.2f}s: {joint_name} angle "
                        f"{target_angle:.2f} > maximum {maximum:.2f}."
                    ),
                })

    return errors


def validate_velocity_constraints(
    motion_keyframes,
    constraints,
    starting_pose=STARTING_POSE,
):
    """
    Check inter-keyframe angular velocities against physical limits.

    Each keyframe is expected to contain the complete joint configuration.
    """
    velocity_tolerance = _require_parameter(
        "VELOCITY_TOLERANCE_RAD_PER_SEC",
        VELOCITY_TOLERANCE_RAD_PER_SEC,
    )
    time_tolerance = _require_parameter(
        "ZERO_TIME_TOLERANCE_SEC",
        ZERO_TIME_TOLERANCE_SEC,
    )
    errors = []

    first_keyframe = motion_keyframes[0]
    if abs(first_keyframe.get("time", 0.0)) < time_tolerance:
        previous_pose = first_keyframe.get("angles", {})
        previous_time = 0.0
        start_index = 1
    else:
        previous_pose = starting_pose
        previous_time = 0.0
        start_index = 0

    for index in range(start_index, len(motion_keyframes)):
        keyframe = motion_keyframes[index]
        current_pose = keyframe.get("angles", {})
        current_time = keyframe.get("time", 0.0)
        duration = current_time - previous_time

        if duration <= time_tolerance:
            changed = any(
                abs(
                    angle
                    - previous_pose.get(
                        joint,
                        starting_pose.get(joint, 0.0),
                    )
                )
                > time_tolerance
                for joint, angle in current_pose.items()
            )
            if changed:
                errors.append({
                    "error": "Instantaneous Movement",
                    "time": current_time,
                    "message": (
                        f"Time {current_time:.2f}s: pose changed "
                        "without a positive time interval."
                    ),
                })

            previous_pose = current_pose
            previous_time = current_time
            continue

        for joint_name, target_angle in current_pose.items():
            if joint_name not in constraints:
                continue

            start_angle = previous_pose.get(
                joint_name,
                starting_pose.get(joint_name, 0.0),
            )
            maximum_velocity = constraints[joint_name].get("maxVelocity")

            if maximum_velocity is None or maximum_velocity <= 0:
                continue

            required_velocity = abs(target_angle - start_angle) / duration
            if required_velocity > maximum_velocity + velocity_tolerance:
                errors.append({
                    "error": "Joint Velocity Violation",
                    "time_end": current_time,
                    "joint": joint_name,
                    "required_velocity": round(required_velocity, 2),
                    "max_velocity": round(maximum_velocity, 2),
                    "message": (
                        f"Time {previous_time:.2f}s -> "
                        f"{current_time:.2f}s: {joint_name} velocity "
                        f"{required_velocity:.2f} > maximum "
                        f"{maximum_velocity:.2f}."
                    ),
                })

        previous_pose = current_pose
        previous_time = current_time

    return errors


def _validate_agent_fall(motion_keyframes):
    """
    Run a user-supplied Webots validation world and read its fall report.

    The world/controller should read VAL_INPUT_FILE and write VAL_OUTPUT_FILE.
    """
    world_path = os.environ.get("WEBOTS_WORLD_PATH") or WEBOTS_WORLD_PATH
    if not world_path:
        return [{
            "error": "Fall Validation Configuration Error",
            "message": "Set WEBOTS_WORLD_PATH before enabling fall validation.",
        }]

    port = find_free_port()
    if port is None:
        return [{
            "error": "Fall Validation Port Error",
            "message": "Could not find an available Webots port.",
        }]

    unique_id = uuid.uuid4().hex[:8]
    input_path = PROJECT_ROOT / f"motion_validation_{unique_id}.json"
    report_path = PROJECT_ROOT / f"fall_report_{unique_id}.json"

    try:
        with open(input_path, "w", encoding="utf-8") as file:
            json.dump(motion_keyframes, file, indent=2)

        environment = os.environ.copy()
        environment["AGENT_VALIDATION_MODE"] = "BATCH"
        environment["PYTHONUNBUFFERED"] = "1"
        environment["AGENT_PROJECT_ROOT"] = str(PROJECT_ROOT)
        environment["VAL_INPUT_FILE"] = str(input_path)
        environment["VAL_OUTPUT_FILE"] = str(report_path)

        command = [
            WEBOTS_EXECUTABLE,
            "--stdout",
            "--stderr",
            "--mode=realtime",
            f"--port={port}",
            "--batch",
            str(world_path),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        output, _ = process.communicate()

        if not report_path.exists():
            return [{
                "error": "Fall Validation Execution Error",
                "message": "The Webots controller did not produce a report.",
                "webots_log": output,
            }]

        with open(report_path, "r", encoding="utf-8") as file:
            report = json.load(file)

        if report.get("status") == "FAILED":
            return [{
                "error": "Agent Fall Violation",
                "message": report.get(
                    "reason",
                    "Unknown agent fall failure.",
                ),
                "webots_log": output,
            }]

        return []

    except Exception as error:
        return [{
            "error": "Webots Execution Error",
            "message": str(error),
        }]
    finally:
        for path in (input_path, report_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def validate_motion(
    motion_keyframes,
    constraints_data=None,
    starting_pose=STARTING_POSE,
    check_angles=True,
    check_velocity=True,
    check_agent_fall=True,
):
    """
    Validate a complete keyframe motion.

    The caller may disable individual checks when configuring the validator.
    """
    if not isinstance(motion_keyframes, list) or not motion_keyframes:
        return False, ["Motion keyframes are empty or invalid."]

    if constraints_data is None:
        constraints_data = load_constraints()

    constraints = constraints_data.get("motors", {})
    errors = []

    if check_angles:
        errors.extend(
            validate_angle_constraints(motion_keyframes, constraints)
        )

    if check_velocity:
        errors.extend(
            validate_velocity_constraints(
                motion_keyframes,
                constraints,
                starting_pose,
            )
        )

    if check_agent_fall and not errors:
        errors.extend(_validate_agent_fall(motion_keyframes))

    return not errors, errors

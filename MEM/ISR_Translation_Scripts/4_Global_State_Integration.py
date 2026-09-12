"""Stage 4: integrate semantic joint events with global robot state."""

import collections


JOINT_GROUPS = {
    "LEFT LEG": [
        "LHipYawPitch",
        "LHipRoll",
        "LHipPitch",
        "LKneePitch",
        "LAnklePitch",
        "LAnkleRoll",
    ],
    "RIGHT LEG": [
        "RHipYawPitch",
        "RHipRoll",
        "RHipPitch",
        "RKneePitch",
        "RAnklePitch",
        "RAnkleRoll",
    ],
    "LEFT ARM": [
        "LShoulderPitch",
        "LShoulderRoll",
        "LElbowYaw",
        "LElbowRoll",
        "LWristYaw",
    ],
    "RIGHT ARM": [
        "RShoulderPitch",
        "RShoulderRoll",
        "RElbowYaw",
        "RElbowRoll",
        "RWristYaw",
    ],
    "LEFT HAND": [
        "LPhalanx1",
        "LPhalanx2",
        "LPhalanx3",
        "LPhalanx4",
        "LPhalanx5",
        "LPhalanx6",
        "LPhalanx7",
        "LPhalanx8",
    ],
    "RIGHT HAND": [
        "RPhalanx1",
        "RPhalanx2",
        "RPhalanx3",
        "RPhalanx4",
        "RPhalanx5",
        "RPhalanx6",
        "RPhalanx7",
        "RPhalanx8",
    ],
    "HEAD": ["HeadYaw", "HeadPitch"],
}


# USER-SUPPLIED PARAMETERS
# Examples: 0.001 s and 0.5 s. These are not the settings used in the study.
MINIMUM_INTERVAL_SEC = None
SENSOR_TIME_TOLERANCE_SEC = None


# The study representation used these three global-state signals.
GLOBAL_STATE_FIELDS = (
    {
        "key": "com_z",
        "label": "Center-of-mass height",
        "unit": " cm",
        "scale": 100.0,
    },
    {
        "key": "imu_pitch",
        "label": "Upper-body tilt",
        "unit": " rad",
        "scale": 1.0,
    },
    {
        "key": "head_pitch",
        "label": "Gaze direction",
        "unit": " rad",
        "scale": 1.0,
    },
)


def aggregate_and_sort(all_events):
    """Return semantic events in chronological order."""
    return sorted(
        all_events,
        key=lambda event: (
            event["start_time"],
            event["end_time"],
            event["joint"],
            event["type"],
        ),
    )


def _time_intervals(
    all_events,
    minimum_interval=MINIMUM_INTERVAL_SEC,
):
    timestamps = {
        float(timestamp)
        for event in all_events
        for timestamp in (event["start_time"], event["end_time"])
    }
    sorted_times = sorted(timestamps)

    return [
        (start, end)
        for start, end in zip(sorted_times, sorted_times[1:])
        if end > start + minimum_interval
    ]


def _closest_sensor_sample(sensor_data, target_time, tolerance):
    if not sensor_data:
        return None

    closest = min(
        sensor_data,
        key=lambda sample: abs(float(sample["time"]) - target_time),
    )
    if abs(float(closest["time"]) - target_time) > tolerance:
        return None
    return closest


def _format_global_state(
    sensor_data,
    start_time,
    end_time,
    tolerance,
):
    start_sample = _closest_sensor_sample(
        sensor_data,
        start_time,
        tolerance,
    )
    end_sample = _closest_sensor_sample(
        sensor_data,
        end_time,
        tolerance,
    )
    if start_sample is None or end_sample is None:
        return []

    lines = ["  GLOBAL STATE:"]
    for field in GLOBAL_STATE_FIELDS:
        key = field["key"]
        if key not in start_sample or key not in end_sample:
            continue

        start_value = float(start_sample[key]) * field["scale"]
        end_value = float(end_sample[key]) * field["scale"]
        difference = end_value - start_value
        lines.append(
            f"    - {field['label']}: "
            f"{start_value:.2f} -> {end_value:.2f} "
            f"(Delta: {difference:+.2f}){field['unit']}"
        )

    return lines if len(lines) > 1 else []


def generate_time_based_report(
    all_events,
    sensor_data=None,
    sensor_time_tolerance=SENSOR_TIME_TOLERANCE_SEC,
):
    """
    Combine joint-level semantic events with center-of-mass height,
    upper-body tilt, and gaze direction over shared time intervals.
    """
    sorted_events = aggregate_and_sort(all_events)
    intervals = _time_intervals(sorted_events)

    current_states = collections.defaultdict(lambda: "Neutral")
    report = [
        "Global State Integration Report",
        "===============================",
    ]

    for start_time, end_time in intervals:
        midpoint = (start_time + end_time) / 2.0
        active_actions = {}
        active_states = {}

        for event in sorted_events:
            event_start = float(event["start_time"])
            event_end = float(event["end_time"])
            event_type = event["type"]
            joint = event["joint"]

            if event_end <= midpoint:
                if event_type == "state":
                    current_states[joint] = event["description"]
                elif event_type == "state_transition":
                    current_states[joint] = event.get(
                        "end_state",
                        event["description"],
                    )

            if event_start <= midpoint <= event_end:
                if event_type == "action":
                    active_actions[joint] = event
                elif event_type in ("state", "state_transition"):
                    active_states[joint] = event

        report.append(f"\n[{start_time:.2f}s - {end_time:.2f}s]")
        report.extend(
            _format_global_state(
                sensor_data,
                start_time,
                end_time,
                sensor_time_tolerance,
            )
        )

        for group_name, joints in JOINT_GROUPS.items():
            group_lines = []

            for joint in joints:
                action = "-"
                state = current_states[joint]

                if joint in active_actions:
                    event = active_actions[joint]
                    metrics = [
                        (
                            f"{event['start_angle']:.2f} -> "
                            f"{event['end_angle']:.2f} rad"
                        )
                    ]
                    if event.get("speed_percent") is not None:
                        metrics.append(
                            f"speed {event['speed_percent']:.1f}%"
                        )
                    if event.get("range_percent") is not None:
                        metrics.append(
                            f"range {event['range_percent']:.1f}%"
                        )
                    action = (
                        f"{event['description']} "
                        f"({', '.join(metrics)})"
                    )

                if joint in active_states:
                    event = active_states[joint]
                    if event["type"] == "state":
                        state = event["description"]
                    else:
                        state = event["description"]

                group_lines.extend([
                    f"    - {joint}:",
                    f"      Action: {action}",
                    f"      State: {state}",
                ])

            report.append(f"  {group_name}:")
            report.extend(group_lines)

    return "\n".join(report)



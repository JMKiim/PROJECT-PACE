# Shared Constants and Dictionaries for the PACE Framework

NEUTRAL_POSE = {
    "HeadYaw": 0.0, "HeadPitch": 0.0,
    "LShoulderPitch": 1.5708, "RShoulderPitch": 1.5708,
    "LShoulderRoll": 0.0,  "RShoulderRoll": 0.0,
    "LElbowYaw": -1.5708,     "RElbowYaw": 1.5708,
    "LElbowRoll": 0.0,     "RElbowRoll": 0.0,
    "LWristYaw": 0.0,      "RWristYaw": 0.0,
    "LHipYawPitch": 0.0,   "RHipYawPitch": 0.0,
    "LHipRoll": 0.0,       "RHipRoll": 0.0,
    "LHipPitch": 0.0,      "RHipPitch": 0.0,
    "LKneePitch": 0.0,     "RKneePitch": 0.0,
    "LAnklePitch": 0.0,    "RAnklePitch": 0.0,
    "LAnkleRoll": 0.0,     "RAnkleRoll": 0.0,
}

JOINT_MEANINGS = {
    "HeadYaw": {
        "action": { "increase": "Rotating head left", "decrease": "Rotating head right" },
        "state": { "high": "Head Rotated Left", "low": "Head Rotated Right", "neutral": "Head Neutral Rotation (Relative to Torso)" }
    },
    "HeadPitch": {
        "action": { "increase": "Flexing head", "decrease": "Extending head" },
        "state": { "high": "Head Flexed (Chin to Chest)", "low": "Head Extended (Tilted Back)", "neutral": "Head Aligned with Torso" }
    },
    "RShoulderPitch": {
        "action": { "increase": "Extending shoulder", "decrease": "Flexing shoulder" },
        "state": { "high": "Arm Extended", "low": "Arm Flexed", "neutral": "Arm Aligned with Torso" }
    },
    "RShoulderRoll": {
        "action": { "increase": "Adducting arm", "decrease": "Abducting arm" },
        "state": { "high": "Arm Adducted (In)", "low": "Arm Abducted (Out)", "neutral": "Arm Parallel to Midline" }
    },
    "RElbowYaw": {
        "action": { "increase": "Supinating forearm", "decrease": "Pronating forearm" },
        "state": { "high": "Forearm Supinated", "low": "Forearm Pronated", "neutral": "Forearm Neutral Rotation (Relative to Upper Arm)" }
    },
    "RElbowRoll": {
        "action": { "increase": "Flexing elbow", "decrease": "Extending elbow" },
        "state": { "high": "Elbow Bent", "low": "Elbow Extended", "neutral": "Elbow Straight" }
    },
    "RWristYaw": {        
        "action": { "increase": "Rotating wrist outward", "decrease": "Rotating wrist inward" },
        "state": { "high": "Wrist Outward", "low": "Wrist Inward", "neutral": "Wrist Neutral Rotation (Relative to Forearm)" }
    },
    "LShoulderPitch": {
        "action": { "increase": "Extending shoulder", "decrease": "Flexing shoulder" },
        "state": { "high": "Arm Extended", "low": "Arm Flexed", "neutral": "Arm Aligned with Torso" }
    },
    "LShoulderRoll": {
        "action": { "increase": "Abducting arm", "decrease": "Adducting arm" },
        "state": { "high": "Arm Abducted (Out)", "low": "Arm Adducted (In)", "neutral": "Arm Parallel to Midline" }
    },
    "LElbowYaw": {
        "action": { "increase": "Pronating forearm", "decrease": "Supinating forearm" },
        "state": { "high": "Forearm Pronated", "low": "Forearm Supinated", "neutral": "Forearm Neutral Rotation (Relative to Upper Arm)" }
    },
    "LElbowRoll": {
        "action": { "increase": "Extending elbow", "decrease": "Flexing elbow" },
        "state": { "high": "Elbow Extended", "low": "Elbow Bent", "neutral": "Elbow Straight" }
    },
    "LWristYaw": {
        "action": { "increase": "Rotating wrist inward", "decrease": "Rotating wrist outward" },
        "state": { "high": "Wrist Inward", "low": "Wrist Outward", "neutral": "Wrist Neutral Rotation (Relative to Forearm)" }
    },
    "RHipYawPitch": {
        "action": { "increase": "Rotating thigh inward", "decrease": "Rotating thigh outward" },
        "state": { "high": "Thigh Rotated In", "low": "Thigh Rotated Out", "neutral": "Thigh Neutral Rotation (Relative to Pelvis)" }
    },
    "RHipPitch": {
        "action": { "increase": "Extending thigh", "decrease": "Flexing thigh" },
        "state": { "high": "Thigh Extended", "low": "Thigh Flexed", "neutral": "Thigh Aligned with Torso" }
    },
    "RHipRoll": {
        "action": { "increase": "Adducting thigh", "decrease": "Abducting thigh" },
        "state": { "high": "Thigh Adducted (In)", "low": "Thigh Abducted (Out)", "neutral": "Thigh Parallel to Midline" }
    },
    "RKneePitch": {
        "action": { "increase": "Flexing knee", "decrease": "Extending knee" },
        "state": { "high": "Knee Bent", "low": "Knee Extended", "neutral": "Knee Fully Extended" }
    },
    "RAnklePitch": {
        "action": { "increase": "Plantarflexing Ankle", "decrease": "Dorsiflexing Ankle" },
        "state": { "high": "Ankle Plantarflexed", "low": "Ankle Dorsiflexed", "neutral": "Foot Perpendicular to Lower Leg" }
    },
    "RAnkleRoll": {
        "action": { "increase": "Inverting ankle", "decrease": "Everting ankle" },
        "state": { "high": "Ankle Inverted (Sole In)", "low": "Ankle Everted (Sole Out)", "neutral": "Foot Aligned with Lower Leg" }
    },
    "LHipYawPitch": {
        "action": { "increase": "Rotating thigh inward", "decrease": "Rotating thigh outward" },
        "state": { "high": "Thigh Rotated In", "low": "Thigh Rotated Out", "neutral": "Thigh Neutral Rotation (Relative to Pelvis)" }
    },
    "LHipPitch": {
        "action": { "increase": "Extending thigh", "decrease": "Flexing thigh" },
        "state": { "high": "Thigh Extended", "low": "Thigh Flexed", "neutral": "Thigh Aligned with Torso" }
    },
    "LHipRoll": {
        "action": { "increase": "Abducting thigh", "decrease": "Adducting thigh" },
        "state": { "high": "Thigh Abducted (Out)", "low": "Thigh Adducted (In)", "neutral": "Thigh Parallel to Midline" }
    },
    "LKneePitch": {
        "action": { "increase": "Flexing knee", "decrease": "Extending knee" },
        "state": { "high": "Knee Bent", "low": "Knee Extended", "neutral": "Knee Fully Extended" }
    },
    "LAnklePitch": {
        "action": { "increase": "Plantarflexing Ankle", "decrease": "Dorsiflexing Ankle" },
        "state": { "high": "Ankle Plantarflexed", "low": "Ankle Dorsiflexed", "neutral": "Foot Perpendicular to Lower Leg" }
    },
    "LAnkleRoll": {
        "action": { "increase": "Everting ankle", "decrease": "Inverting ankle" },
        "state": { "high": "Ankle Everted (Sole Out)", "low": "Ankle Inverted (Sole In)", "neutral": "Foot Aligned with Lower Leg" }
    },
}

NEUTRAL_POSE_DESC = "An at-attention posture relative to the upper body's normal plane: the head faces forward, arms hang vertically downward, and elbows point backward. The normal vector from the palms is directed toward the torso or thighs. Hands are not opened."
JOINT_MEANINGS_DESC = "States are determined based on each joint angle of the NEUTRAL_POSE. Actions refer to objective movements resulting from changes in joint angle values, regardless of the pose."

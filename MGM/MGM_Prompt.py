"""Construct prompts for affective full-body motion generation and refinement."""

import json

from shared.pace_config import STARTING_POSE


def _target_ranges(target_affect):
    """Return the refinement acceptance ranges for one target affect."""
    normalized = target_affect.lower()

    if "neutral" in normalized:
        return "4-6", "4-6"

    if "positive" in normalized:
        valence_range = "7-9"
    elif "negative" in normalized:
        valence_range = "1-3"
    else:
        raise ValueError(
            "Target affect must specify positive, negative, or neutral valence."
        )

    if "high" in normalized:
        arousal_range = "7-9"
    elif "low" in normalized:
        arousal_range = "1-3"
    else:
        raise ValueError(
            "A non-neutral target affect must specify high or low arousal."
        )

    return valence_range, arousal_range


def _success_criteria(target_affect):
    valence_range, arousal_range = _target_ranges(target_affect)
    return f"""
All three evaluator ensemble members must independently satisfy both criteria:
- Valence rating: {valence_range}
- Arousal rating: {arousal_range}
Ratings use the 9-point Self-Assessment Manikin (SAM) scales.
""".strip()


def construct_generator_prompt(
    target_affect,
    feedback=None,
    constraints_text="",
    previous_motion_json=None,
):
    """
    Assemble an initial-generation or refinement prompt.

    Provide both feedback and previous_motion_json for a refinement iteration,
    or omit both for initial zero-shot generation.
    """
    if (feedback is None) != (previous_motion_json is None):
        raise ValueError(
            "Provide both feedback and previous_motion_json for refinement."
        )

    prompt = f"""
You generate executable affective full-body motions for a NAO robot.

### Target Affect Category
{target_affect}

### Starting Pose
{json.dumps(STARTING_POSE)}

### Joint Constraints
Joint angles are expressed in radians, and maximum angular velocities are expressed in radians per second.

{constraints_text}

### Motion Generation Rules
1. Choose the number of keyframes needed to communicate the target affect.
2. Choose strictly increasing keyframe times while respecting the relationship between angular displacement, time interval, and angular velocity.
3. Set the first keyframe time to 0.0 and its angles to the Starting Pose.
4. Keep all joint angles and angular velocities within the supplied limits. Motions that violate these limits are rejected by kinematic validation.
5. Maintain physical stability. Motions that fall during physics-based validation are rejected.
6. Use the same joint keys in every keyframe.
""".strip()

    if feedback is not None:
        criteria = _success_criteria(target_affect)
        prompt += f"""

### Refinement Input
The previous motion passed kinematic validation but did not meet the target-affect success criterion.

Previous motion:
{previous_motion_json}

Target-blind evaluator output:
{feedback}

The evaluator output may contain motion interpretations, valence and arousal ratings, rationales, and suggested improvements.

### Refinement Success Criterion
{criteria}

### Refinement Instructions
1. Compare the previous motion and evaluator output with the Target Affect.
2. Select the feedback that is relevant to reaching the target.
3. Translate the selected feedback into concrete changes to joint angles and keyframe timing.
4. Preserve kinematic validity and physical stability in the revised motion.
""".rstrip()

    prompt += """

### Output Format
The example below is abbreviated and illustrates format only, not a motion.

Output ONLY the JSON code.
### Output Example (JSON Only)
[
  {
    "time": 0.0,
    "angles": {
      "HeadYaw": 0.0,
      "LShoulderPitch": 1.5708,
      ... all remaining Starting Pose joints
    }
  },
  {
    "time": <strictly increasing time in seconds>,
    "angles": {
      "HeadYaw": <angle in radians>,
      "LShoulderPitch": <angle in radians>,
      ... the same complete set of joint keys
    }
  }
]

The first keyframe must reproduce the complete Starting Pose exactly.
Replace all bracketed fields with numeric values, include every joint in every keyframe, and do not output the ellipses or explanatory text.
"""

    return prompt.strip()

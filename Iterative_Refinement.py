"""Iterative refinement between MGM and MEM."""

import copy
import json
from collections.abc import Mapping, Sequence


EXPECTED_EVALUATOR_COUNT = 3

_TARGET_REGIONS = {
    "PH": {"valence": "positive", "arousal": "high"},
    "PL": {"valence": "positive", "arousal": "low"},
    "NN": {"valence": "neutral", "arousal": "neutral"},
    "NL": {"valence": "negative", "arousal": "low"},
    "NH": {"valence": "negative", "arousal": "high"},
}

_SCORE_FIELDS = ("valence_score", "arousal_score")
_TEXT_FIELDS = (
    "valence_reason",
    "arousal_reason",
)


def _validate_target_code(target_code):
    if not isinstance(target_code, str) or target_code not in _TARGET_REGIONS:
        allowed = ", ".join(_TARGET_REGIONS)
        raise ValueError(f"target_code must be one of: {allowed}.")
    return target_code


def _validate_evaluator_output(output, index):
    if not isinstance(output, Mapping):
        raise ValueError(f"Evaluator output {index} must be an object.")

    for field in _SCORE_FIELDS:
        if field not in output:
            raise ValueError(
                f"Evaluator output {index} is missing '{field}'."
            )
        score = output[field]
        if type(score) is not int or not 1 <= score <= 9:
            raise ValueError(
                f"Evaluator output {index} field '{field}' must be "
                "an integer from 1 to 9."
            )

    for field in _TEXT_FIELDS:
        if field not in output:
            raise ValueError(
                f"Evaluator output {index} is missing '{field}'."
            )
        text = output[field]
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Evaluator output {index} field '{field}' must be "
                "a non-empty string."
            )

    return {
        "valence_score": output["valence_score"],
        "valence_reason": output["valence_reason"],
        "arousal_score": output["arousal_score"],
        "arousal_reason": output["arousal_reason"],
    }


def _valence_region(score):
    if score < 4:
        return "negative"
    if score <= 6:
        return "neutral"
    return "positive"


def _arousal_region(score):
    if score < 4:
        return "low"
    if score <= 6:
        return "neutral"
    return "high"


def assess_evaluator_outputs(target_code, evaluator_outputs):
    """
    Aggregate three MEM outputs and assess their mean scores.

    The arithmetic means are classified without rounding. Both Valence and
    Arousal must fall in the target regions for ``meets_target`` to be true.
    """
    target_code = _validate_target_code(target_code)

    if (
        not isinstance(evaluator_outputs, Sequence)
        or isinstance(evaluator_outputs, (str, bytes, bytearray))
    ):
        raise ValueError("evaluator_outputs must be a sequence.")

    if len(evaluator_outputs) != EXPECTED_EVALUATOR_COUNT:
        raise ValueError(
            "evaluator_outputs must contain exactly "
            f"{EXPECTED_EVALUATOR_COUNT} results."
        )

    validated_outputs = [
        _validate_evaluator_output(output, index)
        for index, output in enumerate(evaluator_outputs, start=1)
    ]

    mean_valence = sum(
        output["valence_score"] for output in validated_outputs
    ) / EXPECTED_EVALUATOR_COUNT
    mean_arousal = sum(
        output["arousal_score"] for output in validated_outputs
    ) / EXPECTED_EVALUATOR_COUNT

    target_regions = _TARGET_REGIONS[target_code]
    meets_target = (
        _valence_region(mean_valence) == target_regions["valence"]
        and _arousal_region(mean_arousal) == target_regions["arousal"]
    )

    return {
        "target_code": target_code,
        "mean_scores": {
            "valence": mean_valence,
            "arousal": mean_arousal,
        },
        "meets_target": meets_target,
        "evaluator_outputs": validated_outputs,
    }


def build_refinement_inputs(current_motion, assessment):
    """
    Serialize an assessment for ``construct_generator_prompt``.

    This function only packages data. The caller decides whether another
    refinement iteration should be performed.
    """
    if not isinstance(assessment, Mapping):
        raise ValueError("assessment must be an object.")

    required_fields = (
        "mean_scores",
        "evaluator_outputs",
    )
    for field in required_fields:
        if field not in assessment:
            raise ValueError(f"assessment is missing '{field}'.")

    feedback_payload = {
        "mean_scores": copy.deepcopy(assessment["mean_scores"]),
        "evaluator_outputs": copy.deepcopy(
            assessment["evaluator_outputs"]
        ),
    }

    try:
        return {
            "feedback": json.dumps(
                feedback_payload,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ),
            "previous_motion_json": json.dumps(
                copy.deepcopy(current_motion),
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ),
        }
    except (TypeError, ValueError) as error:
        raise ValueError(
            "current_motion and assessment must be JSON-serializable."
        ) from error

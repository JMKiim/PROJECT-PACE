import json
from pace_config import NEUTRAL_POSE

def construct_generator_prompt(quadrant, feedback=None, constraints_str="", prev_motion_str=None):
    # Define Success Criteria Instructions
    is_positive = "Positive" in quadrant
    is_high = "High" in quadrant
    is_neutral = "Neutral" in quadrant and not ("Positive" in quadrant or "Negative" in quadrant)
    
    if is_neutral:
        val_target = "4.0 <= Valence Score <= 6.0"
        aro_target = "4.0 <= Arousal Score <= 6.0"
        # Neutral Criteria
        criteria_instruction = f"""
        *Based on SAM(Self-Assessment Manikin) 9-point Scale evaluated by 3 independent agents*
        **Primary Criteria (Zone Acceptance)**: 
           - **Arousal Mean**: Must be within [{aro_target}].
           - **Valence Mean**: Must be within [{val_target}].
        """
    else:
        val_target = "Valence Score > 6 (Positive)" if is_positive else "Valence Score < 4 (Negative)"
        aro_target = "Arousal Score > 6 (High)" if is_high else "Arousal Score < 4 (Low)"
        # Standard Criteria: Focus on Clarity and Significance
        criteria_instruction = f"""
        *Based on SAM(Self-Assessment Manikin) 9-point Scale evaluated by 3 independent agents*
        - **Direction**: The MEAN score must match the target quadrant ({val_target}, {aro_target}).
        **Crucial Warning**: High variance or ambiguity will cause FAILURE.
        """
    action_plan_instruction = """ 
    1. Baseline Integration: Apply the 'Motion Generation Rules', especially 'Joint Constraints' as the universal framework to maintain procedural consistency.
    2. Strategic Selection: Analyze the Evaluator's Feedback through the lens of your 'Motion Goal' above. Select the strategies that bridge the gap to meet the 'Success Criteria'.
    3. Comprehensive Reflection: Fully incorporate the core principles of the selected strategy. Avoid partial or minimal adjustments; insufficient reflection of the feedback will result in failing to meet the Success Criteria, and causes retries
    4. Kinematic Synthesis: Convert the selected strategy into specific joint parameters (Angle & Time), focusing on achieving motion goal.
    """

    prompt = f"""
        You are a NAO robot motion generation agent operating under **standard safety protocols**.

        ### Motion Goal (Affective Quadrant)
        [Format: "(Valence) (Arousal) (Abbr)"] 
        {quadrant}

        ### BASE POSE (stand at attention): 
        {json.dumps(NEUTRAL_POSE)}

        ### Joint Constraints (expressed in radians):
        {constraints_str}

        ### Motion Generation Rules
        1. **Structure Design**: You have full discretion to determine the **total number of keyframes** required to express the motion dynamics naturally. Do not limit yourself to a fixed number.
        2. **Time Strategy**: Determining specific time values is your discretion. However, **consider** the physical principle: **Velocity = (Change in Angle) / (Time Interval)**. 
            Purely from a physical standpoint, **excessively short time intervals** drastically increase angular velocity, which may violate intrinsic limits or render the motion **physically unexecutable**.
        3. **Initialization**: The first keyframe's time value MUST be **'0.0'** and its pose MUST be set to **'BASE POSE'** to ensure a standardized initialization.
        4. **Hardware Constraints**: Compliance with the **provided 'Joint Constraints' (Angles)** is mandatory. Furthermore, be aware that violations of **intrinsic dynamic limits (Velocity)**—checked by the system's physical logic—result in **immediate rejection**.
        5. **Physical Stability**: Note that maintaining **physical stability** is a prerequisite. Unstable motions (e.g., falls) are detected by the **Physics Engine** and automatically filtered out as **critical system failures**.
        
        """

    if prev_motion_str and feedback:
        prompt += f"""
        ### REPAIR TASK (Gap Analysis & Refinement)
        The following motion was generated in the **PREVIOUS** workflow cycle. 
        It was **physically valid** (passed safety checks) but **semantically misaligned** with the target goal.

        [1. Previous Failed Motion JSON]:
        {prev_motion_str}

        [2. Feedback Definition]
        interpretation_of_motion: How the previous motion was perceived by the observer.
        (valence/arousal)_score: The SAM evaluation score from 1 to 9.
        (valence/arousal)_reason: Rationale for the SAM evaluation score and improvement strategies.

        [3. Evaluator Feedback (Status & Reason)]:
        {feedback}

        [4. Success Criteria]:
        **{criteria_instruction}**

        [5. INSTRUCTION: Perform Gap Analysis & Execution]:
        **The Evaluator was BLIND to your goal.** It provided objective observations and multiple strategy options based on the score.
        
        **Action Plan (Execute Step-by-Step)**:
        {action_plan_instruction}
        
        """
    prompt += """
        Output ONLY the JSON code.
        ### Output Example (JSON Only)
        [
        {
            "time": 0.0,
            "angles": {
            "HeadYaw": 0.0,
            "LShoulderPitch": 1.5708,
            ... (Matches BASE POSE exactly)
            }
        },
        {
            "time": 1.2,
            "angles": {
            "HeadYaw": 0.0,
            "LShoulderPitch": 1.5,
            ... (other modified joints)
            }
        },
        ]
        """
    return prompt
import json

from pace_config import NEUTRAL_POSE, NEUTRAL_POSE_DESC

# ==============================================================================
# 1. Agent 1: Pose Interpreter
# ==============================================================================
def get_pose_interpreter_prompt():
    return f"""
You are Agent 1: 'Pose Interpreter'
Analyze the provided Kinematic Change Log of the NAO agent and objectively infer the 'actual physical/anatomical pose' of the agent for each timestamp in chronological order. 
'Identifying the intended motion' (Action Labeling) is NOT your role. Describe ONLY the 'geometric shape of the pose' the agent is currently maintaining.

NEUTRAL_POSE = {json.dumps(NEUTRAL_POSE, indent=4)}
NEUTRAL_POSE's DEFINITION: {NEUTRAL_POSE_DESC}

Log and Data Field Definitions:
The Kinematic Change Log provided contains only the changes in joint angles and PHYSICAL_DATA between each timestamped pose.
Any joint angles or physical data not specified in a given segment mean that they maintain the same values as the previous timestamp.
For t=0.00s, since no previous timestamp(pose) exists, the log contains the results compared against the NEUTRAL_POSE.

Before analysis, familiarize yourself with the precise meanings of the terms used in the log:

Action (Motion Execution):
An active movement performed during the interval from timestamp t to t+1.
If no Action is noted for a specific segment, it means there was no significant active motion during that interval.
Keep in mind that Action represents an objective and anatomical 'change' and does not represent a 'state.'
- Ex: A 30-degree Flexing of the Elbow does not mean the elbow is in a 30-degree flexed state, but that the degree of elbow flexion has changed by 30 degrees compared to the previous pose.

Percentage (%):
Speed (%): The actual operating speed relative to the joint's maximum hardware speed.
Range (%): The ratio of movement relative to the joint's Range of Motion (ROM).
Hand  (%): In the case of the hand, only the degree of openness is briefly represented as a percentage.

⚠️ Core Pose Inference Rules ⚠️
1. **Maintain Orthogonal Independence**:
   Analyze Pitch (Sagittal plane) and Roll (Coronal plane) joints independently. It is easier to apply Pitch first, followed by Roll.
   - Ex: When ShoulderPitch is 90 degrees (lifting the arm) and ShoulderRoll is 90 degrees (spreading the arm), applying these sequentially results in "lifting the arm forward (Pitch) 90 degrees and spreading it to the side (Roll) 90 degrees" which translates to the 'arms spread out sideways (T-pose)' position.

2. **Verify Physical Data**:
   Always check the PHYSICS DATA indicators after inference. These represent the actual data from simulation and hold Override priority over individual joint angles when determining the pose.
   - Torso Pitch: The absolute tilt of the upper body relative to the ground (World). A larger (+) value indicates the front of the torso is tilting forward toward the ground.
   - Gaze Pitch: The absolute tilt of the head relative to the ground (World). A larger (+) value indicates looking down, while a larger (-) value indicates looking up.
   - CoM Z: Height of the Center of Mass (Unit: cm). NAO's height is approximately 57.4 cm. (CoM ≈ 27.6 cm in a standing pose)
   - HeadPitch vs. Gaze Pitch Distinction: 
     HeadPitch: The tilt of the head relative to the torso (Local coordinate).
     Gaze Pitch: The tilt of the head relative to the ground/World (Global coordinate). (Since NAO’s gaze is fixed to its head)
     (Gaze Pitch ≈ Torso Pitch + Head Pitch)
   In the NEUTRAL_POSE, Torso Pitch and Gaze Pitch are 0.00 rad, and CoM Z is 27.6 cm.

⚠️ Pose Inference Procedures ⚠️
To ensure accurate whole-body pose inference, you must strictly follow the step-by-step procedure (Chain-of-Thought) below, similar to assembling a figure.

Step 0. Check Delta Values in Log (Assembly Planning) 
Before inference, check and record the **changes in joint angles and physical data (Delta)** provided in the Kinematic Change Log.
Each segment in the log is compared to the previous timestamp, with the exception of 0.00s, which is the starting pose and is compared to the NEUTRAL_POSE.
All angle changes are already recorded, so you can directly use the Delta Deg value.

Step 1. Local Pose Assembly by Body Part via Forward Kinematics (Hold the figure in your hand and assemble it based on the upper body)
Assemble the pose from the 'Torso (Root)' to the 'End-effector' by strictly following the Forward Kinematics (FK) chain.
In particular, strictly separate and describe the Upper Arm and Forearm.
Note: Except for PHYSICS_DATA, all joint angles are relative to the 'Parent Link,' not the ground (World).

Step 2. Applying Global Tilt (Placing the assembled figure on the ground)
Take the 'Torso-based agent shape' completed in Step 1 and describe it as it is positioned relative to the ground (World).
At this stage, apply the Torso Pitch value to tilt the agent's overall pose.
- Ex: Even if the arms were raised 90 degrees forward in Step 1, if the Torso Pitch is tilted 90 degrees forward (fully leaned over), the arms will actually be pointing vertically toward the ground.

Step 3. Physical Data Cross-Verification (Verifying the integrity of the finished figure and its placement)
Cross-verify the final whole-body pose derived in Step 2 using the Physics Data.
- Gaze Pitch (World): Does the final head tilt in the inferred pose, after applying the Torso Pitch, match this value?
- CoM Z: Is the height consistent with the inferred pose (standing/sitting)? (Ex: If the agent is sitting, the height must be lower.)

⚠️ Caution ⚠️
1. Thorough Change Detection: 
  If even a single joint changes, it is highly likely to affect the overall pose. 
  Carefully review all change information—including the HAND—in Step 0.

2. Rigorous Directional Analysis: 
  When describing the direction of body parts (e.g., up/down, front/back), you must first determine the orientation relative to the local normal vector, and then apply the Torso Pitch for an extremely meticulous and precise calculation.
  - Ex: If the agent raises its arm 50 degrees forward from the Neutral Pose while simultaneously tilting its upper body (Torso Pitch) 50 degrees forward, the upper arm first points 40 degrees downward relative to the upper body's normal plane. 
    Once the Torso Pitch is applied, the upper arm ultimately points vertically toward the ground. 
    Note that the same Shoulder Pitch can result in different physical orientations depending on the Torso Pitch.

3. Avoid Abstract Expressions: 
  Do not use abstract or metaphorical terms such as "V-shape" or "Horse-riding stance." 
  Describe the pose objectively, using the numerical data of the changes as your evidence.

Output Format: 
You must output in JSON format, including the following two sections.
#### Section 1: transitions
First, record the changes (Actions) occurring between each timestamp (t to t+1), including Physics Data, exactly as they appear in the original input log.
- Joint Changes: Must include Joint Name, Delta(Δdeg), Speed(%), and Range(%). (Including HAND)
- Physics Changes: Record changes in Torso Pitch, Gaze Pitch, and CoM Z.
#### Section 2: snapshot_poses
Describe the static pose the agent is maintaining at every timestamp (record each point individually, e.g., Time 0.0s, 0.4s, etc.).
Refer to the output example below for description and label writing instructions.
You should include details of terminal body parts, such as palm normal vectors, in the label.

### (Highest Priority) CRITICAL INSTRUCTIONS
# In Step 0, all 'inference' is strictly prohibited. Simply record the provided deltas. If a value is not recorded, it means it maintains the same value as the previous pose or the NEUTRAL_POSE.
# In Steps 2 and 3, NEVER infer PHYSICAL DATA values. If there is a change, it will be recorded; otherwise, it remains identical to the previous pose (or NEUTRAL_POSE for 0.0s). 
# If it is not in the immediate previous pose, check further back until the value is found.
# Prioritize learning all contents of Step 1 (Inference style/procedure/method/format, etc.) included in the output example and follow them thoroughly without omission.
# Pay particular attention to the connection between Steps 1, 2, and 3, the comparison with the previous pose using the 'Upper Body Normal Plane,' Actions, and Delta Deg, and the determination of directions.
# To determine the Up/Down direction of a body part, simply compare the required delta to reach the horizontal reference plane from the previous pose with the actual joint angle delta. 
  Be careful not to confuse the process of change with the final state (e.g., the act of "lifting upward" does not mean the part is currently "above" the reference).
 - Ex: For determining the up/down orientation of the upper arm: 
   If the arm is currently below the torso's normal plane and requires 70° of Flexing to become parallel to it, a 50° Flexing action means the arm moved "upward," but since 50 < 70, the final state of the upper arm is still located below the torso's normal plane.
Note: The upper arm of the attention position(or NEUTRAL_POSE) is directed vertically downward with respect to the upper body's normal plane.

### Output Example (JSON Only) ###
```json
{{
  "transitions": [
    {{
      "interval": "0.0s - 1.0s",
      "joint_changes": [
        "LShoulderPitch Flexing (1.50->0.30) (Speed: 25%, Range: 76%)",
        ...
      ],
      "physics_changes": [
        "CoM Z: 27.63 -> 28.19 (Delta: +0.56) cm",
        ...
      ]
    }},
    ...
  ],
  "snapshot_poses": [
    {{
      "time_point": 0.0,
      "description": "
        Step 0. [Check Delta] 
        Compared to the NEUTRAL_POSE, the changes are as follows: 
        ShoulderPitch -0.07 rad (Flexing Shoulder), ShoulderRoll ±0.1 rad (Abducting arm), ElbowYaw ±1.57 rad (Pronating elbow), and WristYaw ±1.57 rad (Supinating wrist). All other joints maintain their Neutral state.

        Step 1. [Local Pose Assembly (Delta-based Inference)]
        1. Head: Since there is no change from the NEUTRAL_POSE (0.0), it remains facing forward, horizontal to the upper body's normal plane.
        2. Upper Arm: Relative to the NEUTRAL_POSE (arms hanging down), ShoulderPitch decreased slightly by ~4.0° and ShoulderRoll changed by ~5.7°. Compared to the vertical-down position of the NEUTRAL_POSE, the upper arm is lifted by about 4°, meaning it still points almost vertically downward relative to the upper body's normal plane, with the arms spread very slightly (~5.7°, Almost Neutral).
        3. Forearm: Starting from the NEUTRAL_POSE (arms hanging downward with elbows pointing backward) and incorporating the slight upper arm abduction (5.7°) described above: 
           the ElbowYaw was pronated by approximately 90° (internal rotation). Consequently, the elbows are now oriented toward the sides relative to the upper body’s normal plane. Since there is no change in ElbowRoll, the arms remain fully extended (straight).
        4. Palm: Starting from the NEUTRAL_POSE (arms hanging downward, elbows pointing backward, and the palm's normal vector facing the torso) and proceeding through the subtle upper arm abduction (5.7°) and forearm internal rotation (~90°): 
           the palm's normal vector would initially be directed toward the rear of the upper body's normal plane. However, as the WristYaw is supinated (external rotation) by approximately 90°, the palm's normal vector ultimately returns to facing the torso.
           Hand's openness are not changed.
        5. Leg: No changes for both legs compared to the NEUTRAL_POSE; maintained in a straight, upright standing posture.

        Step 2. [Global Transformation] 
        Since there is no change in Torso Pitch, the pose assembled in Step 1 is placed on the ground as is. 
        The final result is a standing-at-attention pose facing forward, with only minute deviations from the NEUTRAL_POSE.

        Step 3. [Verification]
        Because CoM Z and Gaze Pitch are nearly identical to the Neutral values, the 'forward-facing at-attention pose' derived in Step 2 is cross-verified as correct.
      ",
      "label": "A standing-at-attention pose facing forward, with the elbows oriented toward the sides and the palms' normal vectors facing the torso. Hands are not opened."
    }},
    {{
      "time_point": 1.0,
      "description": "
        Step 0. [Check Delta]
        Compared to the previous timestamp (t=0.0), the changes are as follows:
        The bilateral ShoulderPitch changed by -1.20 rad (Flexing shoulder), ShoulderRoll by ±1.50 rad (Abducting arm), and ElbowRoll by ±1.50 rad (Flexing elbow). Bilateral HipPitch also changed by -0.5 rad (Flexing thigh).

        Step 1. [Local Pose Assembly (Delta-based Inference)]
        1. Head: No change relative to the previous timestamp (t=0.0); maintains a forward-facing orientation relative to the upper body’s normal plane.
        2. Upper Arm: Compared to the previous pose where the arms were hanging straight down, both ShoulderPitch joints flexed by approximately 70.0° to lift the arms, and ShoulderRoll abducted by approximately 86.6° to spread them sideways. From the previous pose where the upper arm was oriented vertically downward relative to the upper body's normal plane, a 90-degree change is required for the upper arm to become parallel to the plane. Since it was only lifted by 70 degrees, falling short of the required 90 degrees, the upper arm remains oriented in a downward direction relative to the upper body's normal plane. Furthermore, as the angle of abduction is nearly 90 degrees, the arms are spread wide to the sides relative to the upper body's normal plane.
        3. Forearm: Starting from the previous pose with the arms straight down and elbows pointing sideways, applying the upper arm lifting (70°) and spreading (86.6°) mentioned in the [Upper Arm] section causes the elbows to point backward relative to the upper body's normal plane. Since there is no separate change in ElbowYaw, the direction the elbows are pointing is maintained. In this state, as ElbowRoll flexes by approximately 86.6° to bend, the forearms extend forward, nearly parallel to the upper body's normal plane. (If they had flexed further, the forearms would have gathered in front of the chest).
        4. Palm: Starting from the previous pose (arms down, elbows sideways, palms facing torso) and applying the transformation chain (Shoulder 70°/86.6°, Elbow 86.6°): the hands are positioned in front of the torso, wider than shoulder-width. Crucially, as the blades of the hands are tilted rather than perpendicular to the ground, the normal vectors of the palms do not perfectly face each other in parallel; instead, they converge at an angle in the space in front of the torso. Since WristYaw is unchanged, this tilted orientation is maintained. Hand's openness are not changed.
        5. Leg: Compared to the previous pose (0.0s), the HipPitch of both legs flexed by approximately 28.6°, and the remaining joints are identical to the previous pose. Therefore, while the legs are extended (straight), the angle between the upper body and the lower body is bent by 28.6°.

        Step 2. [Global Transformation]
        The Torso Pitch tilted forward by approximately 28.6°, which is the same degree as the HipPitch. The result of tilting the pose assembled in Step 1 according to the Torso Pitch and then placing it on the ground is as follows:
        1. The legs are fully extended and vertical to the ground. In this state, the upper body is tilted forward by 28.6°, and the upper body normal plane tilts accordingly.
        2. As the upper body normal plane tilts 28.6° forward, the head—which was facing forward relative to the upper body normal plane—ultimately ends up looking slightly downward toward the ground.
        3. As the upper body normal plane tilts 28.6° forward, the upper arms—which were oriented diagonally downward toward the outer sides relative to the upper body normal plane—ultimately point in a diagonal backward/outward/downward direction.
        4. As the upper body normal plane tilts 28.6° forward, the forearms—which were facing forward and nearly parallel to the plane—ultimately point in a diagonal downward-forward direction.

        Step 3. [Verification]
        1. The Gaze Pitch tilted forward by approximately 28.6°, which is consistent with the Step 2 result of 'the head looking downward toward the ground.'
        2. CoM Z increased slightly. This implies that the impact of lifting both arms was greater than the impact of tilting the upper body forward.
      ",
      "label": "A pose where the torso is leaned forward with the head looking slightly toward the ground; the upper arms are oriented diagonally backward/outward/downward, and the elbows are flexed so that the forearms point forward/diagonal-downward with the palms' normal vectors angled toward each other in front of the torso. Hands are not opened."
    }},
    ...
  ]
}}
```
"""

# ==============================================================================
# 2. Agent 2: Dynamics Analyzer
# ==============================================================================
def get_dynamics_analyzer_prompt():
    return f"""
You are Agent 2: 'Dynamics Analyzer'

NEUTRAL_POSE's DEFINITION: {NEUTRAL_POSE_DESC}

Log and Data Field Definitions:
You will receive a log about 'Chronological List of Poses and Changes' authored by Agent 1 (Pose Interpreter). 
The contents of the list provided by Agent 1 are as follows:
1. transitions: 
  This section contains only the deltas (amount of change) and detailed information for joint angles and physical data that changed during the intervals between timestamps (poses). 
  For the 0.0s pose, as there is no previous pose, the results compared against the NEUTRAL_POSE are specified.
  Since only changed items are recorded, any data not specified remains unchanged compared to the previous pose (or the NEUTRAL_POSE in the case of 0.0s).
2. snapshot_poses: 
  This section provides an inferred label for the pose at each timestamp along with its underlying reasoning (description).

[Reference Data Definitions]
- **Speed (%)**: The actual operating speed relative to the joint's maximum hardware speed.
- **Range (%)**: The ratio of movement relative to the joint's Range of Motion (ROM).
- **Hand (%)**: The degree of hand opening/closing (0%: Closed/Fist, 100%: Open/Extended).
- **Torso Pitch**: The tilt of the upper body relative to the ground (World). A larger (+) value indicates the front of the torso is tilting forward toward the ground.
- **Gaze Pitch**: The absolute tilt of the head relative to the ground (World). A larger (+) value indicates looking down, while a larger (-) value indicates looking up.
- **CoM Z**: Height of the Center of Mass (Unit: cm). NAO's height is approximately 57.4 cm. (CoM ≈ 27.6 cm in a standing pose)

⚠️ Core Rules for Motion Inference ⚠️
1. **Continuous Interpolation**:
  Interpret the log data with the understanding that it represents a continuous flow of smoothly interpolated movements, rather than a sequence of fragmented or discrete motions.
2. Data Recording - **[Prohibition of Subjective Judgment]**:
   - Use the Speed/Range data provided in Agent 1's log as your evidence.
   - Do not use subjective adjectives such as "fast/slow" or "large/small"; instead, describe the data strictly using the numerical values provided in the log.
3. Eliminating ambiguous expressions:
  Avoid ambiguous expressions with unknown levels of posture (e.g., squats, horseback riding positions) and provide objective explanations based on numerical data.

Output Format:
You must output in JSON format, including the following two sections:
### Section 1. key_phases
Analyze the data provided by Agent 1 and describe the motions by grouping them into segments.
Note: Exclude the [NEUTRAL_POSE - 0.0s] interval, as it is a simple comparison between the reference and the starting pose rather than an actual movement.
- **joint_changes**: Record Agent 1's data (value changes, Speed%, Range%) exactly as provided, without any omission.
- **physics_hanges**: Record the detailed change data for Torso Pitch, Gaze Pitch, and CoM Z.
- **analysis**: Analyze the flow of changes, focusing on the objective "movement itself" rather than the "intent" of the motion. While numerical data is included in this specific field, you must preserve all descriptive details specified in Agent 1's label and description without omission.
### Section 2. overall_motion
Synthesize all the segmented analyses above in chronological order to describe what the entire sequence of motion represents.
Provide an objective description of the entire motion by combining the "Analysis" results from the segmented analysis. Do not infer or interpret the underlying intent.

It is not your role to determine what information is important. 
Include details of terminal body parts, such as normal vectors of palm, in the analysis or overall_motion.

### Output Example (JSON Only) ###
```json
{{
  "key_phases": [
    {{
      "interval": "0.0s - 0.8s",
      "joint_changes": "
        "HeadPitch: Flexing head (0.00 -> 0.40 (Delta: +0.40 rad (+23 deg)), Speed: 7.0%, Range: 33.7%)",
        "LShoulderPitch: Flexing shoulder (1.50 -> 0.40 (Delta: -1.10 rad (-63 deg)), Speed: 15.1%, Range: 26.4%)",
        ...
      ",
      "physics_changes":
        "CoM Z: 27.63 -> 28.08 (Delta: +0.45) cm",
        "Gaze Pitch: -0.00 -> 0.35 (Delta: +0.35 (+20 deg)) rad
      ",
      "analysis": "Starting from an at-attention pose where the elbows are oriented sideways and the palm normal vectors face the torso, the knees and hip joints are slightly flexed. Simultaneously, both upper arms are lifted by 63°—remaining below the horizontal plane—while the elbows (forearms) are flexed by 20° to position both hands together in front of the upper body. Consequently, the palm normal vectors face each other while tilting very slightly toward the torso (specifically toward the solar plexus). Hand's are opening (0% to 50%)."
    }},
    ...
  ],
  "overall_motion": "..."
}}
```
"""

# ==============================================================================
# 3. Agent 3: Affective Evaluator
# ==============================================================================
def get_affective_evaluator_prompt(is_neutral_task=False):
    if is_neutral_task:
        reasoning_strategy = """
  1. Midpoint Analysis: Analyze the score relative to the Neutral Zone (Score 4~6) 
  2. Strategy for Change:
  - [If Score < 4]: Provide 'Upward Calibration Strategy'. Instruct specifically how to increase the score to reach the (4 <= Score <= 6).
  - [If Score > 6]: Provide 'Downward Damping Strategy'. Instruct specifically how to decrease the score to drop into the (4 <= Score <= 6).
  - [If 4 <= Score <= 6]: Provide 'Stabilization Strategy'. Instruct how to maintain this score."""
        
        closing_instruction = """
The results serve as a rigorous prescriptive guide for motion generator.
Act as a proactive evaluator, provide specific numerical instructions.
Detailed instructions (e.g., intensity, range, repetitions, etc.) are allowed."""
    else:
        reasoning_strategy = """
  1. Midpoint Analysis: Explain why the score is positioned on its side relative to the SAM midpoint (Score 5). If it is exactly 5, explain why it is neutral. 
  2. Strategy for Change:
  - [If Score != 5]: Provide 'Category Inversion Strategy' (how to flip to the opposite side of 5) and 'Extremization Strategy' (how to reach the pole of the current category, 1 or 9).
  - [If Score = 5]: Provide 'Directional Divergence Strategy' (Changes required to move the perception into BOTH the 'High' (>5) and 'Low' (<5) categories, and 'Remove the **Ambiguity**')."""
        
        closing_instruction = """
The results serve as a rigorous prescriptive guide to remove all ambiguity for motion generator.
Act as a proactive evaluator, provide specific numerical instructions to ensure the next iteration reaches a definitive and unambiguous affective zone.
Detailed instructions (e.g., intensity, range, repetitions, etc.) are allowed."""
    return f"""
You are Agent 3: 'Affective Evaluator'
Based on the 'Action' log of the NAO agent identified in the previous stage (Agent 2), an affective evaluation should be conducted.
Check the criteria, perspectives, and procedures specified below carefully.

[Reference Data Definitions]
- **Speed (%)**: The actual operating speed relative to the joint's maximum hardware speed.
- **Range (%)**: The ratio of movement relative to the joint's Range of Motion (ROM).
- **Hand (%)**: The degree of hand opening/closing (0%: Closed/Fist, 100%: Open/Extended).
- **Torso Pitch**: The tilt of the upper body relative to the ground (World). A larger (+) value indicates the front of the torso is tilting forward toward the ground.
- **Gaze Pitch**: The absolute tilt of the head relative to the ground (World). A larger (+) value indicates looking down, while a larger (-) value indicates looking up.
- **CoM Z**: Height of the Center of Mass (Unit: cm). NAO's height is approximately 57.4 cm. (CoM ≈ 27.6 cm in a standing pose)

⚠️ SAM Definition and Evaluation Criteria ⚠️
SAM(Self-Assessment Manikin Scale) 9-point Scale :
**Arousal** (1–9): (1–4: Low Arousal, 5: Moderate, 6–9: High Arousal).
**Valence** (1–9): (1–4: Unpleasant/Negative, 5: Neutral, 6–9: Pleasant/Positive).

⚠️ Common SAM Evaluation Criteria ⚠️
1. Granularity & Anchor: 
  Use the 1-9 scale with 5 as the neutral baseline.
  Score in detail according to the evaluation results and **react sensitively to the possibility of neutral recognition**.
  Avoid exaggerated evaluations(especially extreme scores: 1, 9) unless evidence is definitive.
2. SAM Grading: 
  1) 5 (Neutral): Strictly mundane or truly ambiguous.
  2) 4 or 6 (Subtle Direction): Buffers for motions with a detectable lean but remaining ambiguity.
    Assign these to motions that possess 'disqualifying factors' that hinder a definitive classification.
  3) 1-3 & 7-9 (Definitive): Reserved for motions with clear and consistent evidence.
    Motions containing significant disqualifying factors must be excluded from these zones, regardless of their peak intensity.
    Apply differentiated grading based on evidence intensity; avoid extreme scores (e.g., 1, 9) unless kinetic evidence is definitive.

⚠️ Evaluation from a Human Observer's Perspective ⚠️
1. Perceptual Uncertainty: 
  Human judgment is non-binary and context-dependent. 
  what emotion it expresses, and how ambiguous it is, can vary from person to person.
2. Velocity Evaluation
  Human observers are generally unaware of a agent's hardware constraints
  Therefore, the criteria for evaluating that 'the motion is fast' MUST be strict, based on human social norms.
  A motion is 'definitively fast' only if it conveys clear visual urgency beyond functional necessity.
  Note that instantaneous peak speed does not necessarily represent the overall speed of the motion.
3. Head Cues: 
  Even if the head is not moved directly, it is likely to be recognized as a head movement according to the movement of the torso.
  If it is too slow, it is likely that it **will not be recognized as a head cue** by human observers or its meaning will be distorted.
4. **Special Considerations for Low Arousal**
  Even in the same motion, if the speed is too slow, the meaning can be distorted.
  If the amount of movement is too small, the lack of clues can obscure the motion or cause the evaluation to go beyond expectations.
5. **Special Considerations for High Arousal**
  Valence confusion is common in high-arousal motion. Motion can be perceived differently by human observers. 
  So check the details and ambiguity of the motion and reflect it in the SAM score.
6. Motion Type
  Even the same behavior can be recognized as different motion types from person to person.
  Perceived speed may vary depending on the motion type.
  Depending on the person, the standard of high-arousal motion type can be dramatic and exaggerated
  Therefore, it's ok to apply strict and conservative standards to definitive high-arousal evaluations. 

⚠️ Evaluation Procedures ⚠️
You should follow this procedure thoroughly.
Step 0. Check the motion(posture) written in the log received from Agent 2.
Step 1. Determine the possible motion types list (e.g., stretching, walking, dancing, swinging, etc.). 
Step 2. [MOST IMPORTANT] Thoroughly learn the SAM criteria and human observer perspectives set out above.
Step 3. Use all the information learned in step 2 to conduct SAM evaluation and provide decisive, prescriptive feedback.

Output Format:
The analysis results must be output in strict adherence to the JSON format provided below.
- "interpretation_of_motion": Refer to the Agent 2's motion log, infer the possible motion types list.
- "(valence/arousal)_score": Provide a score from 1 to 9 based on the evaluation criteria.
- "(valence/arousal)_reason": Provide a comprehensive rationale that must include all of the following components:
{reasoning_strategy}

{closing_instruction}

### Output Example (JSON Only) ###
{{
  "interpretation_of_motion": "...",
  "arousal_score": 1,
  "arousal_reason": "Must consider ALL rules from 'Evaluation from a Human Observer's Perspective'",
  "valence_score": 2,
  "valence_reason": "Must consider ALL rules from 'Evaluation from a Human Observer's Perspective'",
}}
"""
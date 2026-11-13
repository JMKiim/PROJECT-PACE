<div align="center">
  <h1>PACE</h1>
  <p><strong>Core Components for Affective Robot Motion</strong></p>
</div>

<p align="center">
  <a href="#framework">Framework</a> ·
  <a href="#overview">Overview</a> ·
  <a href="#reference-setup">Reference Setup</a> ·
  <a href="#motion-examples">Motion Examples</a> ·
  <a href="#repository-structure">Repository Structure</a> ·
  <a href="#configuration-before-use">Configuration</a>
</p>

## Framework

<p align="center">
  <a href="./figure/Framework.svg">
    <img src="./figure/readme/framework.png" alt="PACE framework architecture" width="100%">
  </a>
</p>

<p align="center">
  <sub><strong>Framework overview.</strong> The Motion Generation Module (MGM) supports motion generation and kinematic validation. The Motion Evaluation Module (MEM) converts each kinematically valid motion into an intermediate semantic representation (ISR) and supports affective evaluation and refinement. Click the figure to open the original SVG.</sub>
</p>

## Overview

This repository provides the reference components used in the framework: prompt templates for MGM and MEM, kinematic-validation logic, shared robot configuration, four-stage ISR conversion, and utilities for three-evaluator score aggregation and MGM refinement input.

| Component | Included functionality | Key files |
| --- | --- | --- |
| **Motion Generation Module (MGM)** | Dynamic prompt assembly for initial motion generation and feedback-guided revision | `MGM/MGM_Prompt.py` |
| **Kinematic Validation** | Joint-angle, angular-velocity, and optional physics-based fall checks | `MGM/Kinematic_Validation.py`, `shared/joint_constraints.json` |
| **Intermediate Semantic Representation (ISR)** | Temporal segmentation, kinematic profiling, semantic mapping, and global state integration | `MEM/ISR_Translation_Scripts/` |
| **Motion Evaluation Module (MEM)** | Prompt construction for pose interpretation, dynamics analysis, and affective evaluation | `MEM/MEM_Prompt.py` |
| **Iterative Refinement** | Three-evaluator score aggregation, success-criterion assessment, and refinement-input preparation | `Iterative_Refinement.py` |

## Reference Setup

The reference implementation was configured with:

| Component | Reference configuration |
| --- | --- |
| **Language model API** | Google Gemini 2.5 Pro API |
| **Physics simulator** | Webots R2025a |
| **Robot platform** | NAO V6 humanoid robot |

## Motion Examples

### Virtual NAO model

<p align="center">
  <a href="./figure/S1_Stimuli.svg">
    <img src="./figure/readme/virtual-stimuli.png" alt="Five affective motion stimuli shown with a virtual robot" width="100%">
  </a>
</p>

<p align="center">
  <sub>Representative motions rendered on the virtual NAO model.</sub>
</p>

### Physical NAO execution

<p align="center">
  <a href="./figure/S2_Stimuli.svg">
    <img src="./figure/readme/physical-stimuli.png" alt="Five affective motion stimuli shown with a physical robot" width="100%">
  </a>
</p>

<p align="center">
  <sub>Representative frames of corresponding motions executed by the physical NAO.</sub>
</p>

<p align="center">
  <sub><strong>Target affect categories:</strong> PH = Positive-valence and High-arousal; PL = Positive-valence and Low-arousal; NN = Neutral-valence and Neutral-arousal; NL = Negative-valence and Low-arousal; NH = Negative-valence and High-arousal. Click either figure to open the original SVG.</sub>
</p>

## Repository Structure

```text
.
├── Iterative_Refinement.py
├── MGM/
│   ├── MGM_Prompt.py
│   └── Kinematic_Validation.py
├── MEM/
│   ├── MEM_Prompt.py
│   └── ISR_Translation_Scripts/
│       ├── 1_Temporal_Segmentation.py
│       ├── 2_Kinematic_Profiling.py
│       ├── 3_Semantic_Mapping.py
│       └── 4_Global_State_Integration.py
├── shared/
│   ├── pace_config.py
│   └── joint_constraints.json
└── figure/
    ├── Framework.svg
    ├── S1_Stimuli.svg
    ├── S2_Stimuli.svg
    └── readme/
```

The ISR conversion stages are:

1. **Temporal segmentation** — distinguishes stationary intervals from movement.
2. **Kinematic profiling** — determines whether each joint angle increases or decreases and quantifies speed and range relative to the robot's constraints.
3. **Semantic mapping** — converts each profiled change into a predefined, joint-specific natural-language expression.
4. **Global-state integration** — adds simulator-derived whole-body changes in center-of-mass height, upper-body tilt, and gaze direction.

## Configuration Before Use

Configure the following robot- and task-specific values before running validation or ISR translation:

- `shared/pace_config.py`: robot height, standing center-of-mass height, starting pose, and joint semantics.
- `MGM/Kinematic_Validation.py`: joint-angle, angular-velocity, and zero-time tolerances.
- `MEM/ISR_Translation_Scripts/1_Temporal_Segmentation.py`: movement threshold.
- `MEM/ISR_Translation_Scripts/4_Global_State_Integration.py`: minimum interval and sensor-time tolerance.
- Optional fall checking additionally requires a local Webots installation, world, and controller.

## Minimal Example

Run the following from the repository root to assemble an initial MGM prompt for the PH target affect category:

```python
from pathlib import Path

from MGM.MGM_Prompt import construct_generator_prompt


constraints_text = Path("shared/joint_constraints.json").read_text(encoding="utf-8")

prompt = construct_generator_prompt(
    target_affect="Positive-valence and High-arousal (PH)",
    constraints_text=constraints_text,
)
```

The core Python modules use only the Python standard library.

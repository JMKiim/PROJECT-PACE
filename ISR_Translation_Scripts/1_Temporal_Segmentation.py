import json
import os

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from pace_config import NEUTRAL_POSE

def get_motion_data(constraints_file, motion_file):
    constraints = load_json(constraints_file)
    motion_data = load_json(motion_file)
    
    joint_movements = {}
    
    motion_data.sort(key=lambda x: x['time'])
    
    all_joints = set(NEUTRAL_POSE.keys())
    for frame in motion_data:
        all_joints.update(frame['angles'].keys())
        
    for joint in all_joints:
        joint_movements[joint] = []
    for frame in motion_data:
        t = frame['time']
        frame_angles = frame['angles']
        
        for joint in all_joints:
            if joint in frame_angles:
                val = frame_angles[joint]
            else:
                val = NEUTRAL_POSE.get(joint, 0.0)
            
            joint_movements[joint].append((t, val))
                
    return joint_movements, constraints

def generate_report(joint_movements, constraints):
    report = []
    report.append("Temporal Segmentation Report")
    report.append("==========================")
    
    for joint in sorted(joint_movements.keys()):
        movements = joint_movements[joint]
        if not movements:
            continue
            
        report.append(f"\nJoint: {joint}")
        
        joint_constraints = constraints['motors'].get(joint)
        if not joint_constraints:
            report.append(f"  Warning: No constraints found for {joint}")
            min_angle = -float('inf')
            max_angle = float('inf')
            max_vel = float('inf')
        else:
            min_angle = joint_constraints['min']
            max_angle = joint_constraints['max']
            max_vel = joint_constraints['maxVelocity']
            report.append(f"  Constraints: Min={min_angle}, Max={max_angle}, MaxVel={max_vel}")

        report.append("  Movements:")
        
        for i, (t, angle) in enumerate(movements):
            status = []
            
            if angle < min_angle or angle > max_angle:
                status.append(f"[VIOLATION: Angle out of bounds ({min_angle} ~ {max_angle})]")
            
            vel_str = ""
            if i > 0:
                prev_t, prev_angle = movements[i-1]
                dt = t - prev_t
                if dt > 0:
                    velocity = (angle - prev_angle) / dt
                    vel_str = f", Velocity={velocity:.4f} rad/s"
                    if abs(velocity) > max_vel:
                        status.append(f"[VIOLATION: Velocity exceeds max {max_vel}]")
                else:
                    vel_str = ", Velocity=N/A (dt=0)"
            
            status_str = " " + " ".join(status) if status else ""
            report.append(f"    Time {t:.4f}s: Angle {angle:.4f} rad{vel_str}{status_str}")

    return "\n".join(report)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    constraints_path = os.path.join(current_dir, '..', 'joint_constraints.json')
    motion_path = os.path.join(current_dir, '..', 'data', 'sample_motion.json')
    
    if not os.path.exists(constraints_path):
        print(f"Error: {constraints_path} not found.")
    elif not os.path.exists(motion_path):
        print(f"Error: {motion_path} not found.")
    else:
        joint_movements, constraints = get_motion_data(constraints_path, motion_path)
        report_text = generate_report(joint_movements, constraints)
        print(report_text)

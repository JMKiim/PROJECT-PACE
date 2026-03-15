import math
import os
import json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pace_config import NEUTRAL_POSE, JOINT_MEANINGS

# --- Configuration ---
# Thresholds for generating the optimized report
MIN_TIME_INTERVAL_SEC = 0.001       # Minimum time diff to register an interval
SIGNIFICANT_ANGLE_DELTA_RAD = 0.02  # Minimum angle change (rad) to report
SIGNIFICANT_HAND_DELTA_PCT = 5.0    # Minimum hand % change to report
# ---------------------

JOINT_GROUPS = {
    "LEFT LEG": ["LHipYawPitch", "LHipRoll", "LHipPitch", "LKneePitch", "LAnklePitch", "LAnkleRoll"],
    "RIGHT LEG": ["RHipYawPitch", "RHipRoll", "RHipPitch", "RKneePitch", "RAnklePitch", "RAnkleRoll"],
    "LEFT ARM": ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw"],
    "RIGHT ARM": ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw"],
    "HEAD": ["HeadYaw", "HeadPitch"]
}

HAND_GROUPS = {
    "LEFT HAND": {
        "Finger 1": ["LPhalanx1", "LPhalanx2", "LPhalanx3"],
        "Finger 2": ["LPhalanx4", "LPhalanx5", "LPhalanx6"],
        "Finger 3": ["LPhalanx7", "LPhalanx8"]
    },
    "RIGHT HAND": {
        "Finger 1": ["RPhalanx1", "RPhalanx2", "RPhalanx3"],
        "Finger 2": ["RPhalanx4", "RPhalanx5", "RPhalanx6"],
        "Finger 3": ["RPhalanx7", "RPhalanx8"]
    }
}

def load_constraints():
    # Attempt to load constraints from standard location
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        constraints_path = os.path.join(current_dir, '..', 'joint_constraints.json')
        if os.path.exists(constraints_path):
            with open(constraints_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return None

CONSTRAINTS = load_constraints()

def calculate_intensity(angle, joint_name):
    """Calculates intensity % based on neutral and limits locally."""
    if not CONSTRAINTS or joint_name not in CONSTRAINTS['motors']:
        return 0.0
    
    neutral = NEUTRAL_POSE.get(joint_name, 0.0)
    limits = CONSTRAINTS['motors'][joint_name]
    min_lim = limits['min']
    max_lim = limits['max']
    
    if angle >= neutral:
        denom = max_lim - neutral
        if denom == 0: return 0.0
        return (angle - neutral) / denom * 100.0
    else:
        denom = neutral - min_lim
        if denom == 0: return 0.0
        return (neutral - angle) / denom * 100.0

def get_state_desc(joint_name, angle):
    """Returns (state_description, intensity_percent)."""
    meaning = JOINT_MEANINGS.get(joint_name)
    if not meaning:
        return "Unknown", 0.0
        
    neutral_val = NEUTRAL_POSE.get(joint_name, 0.0)
    tolerance = meaning.get("tolerance", 0.1)
    
    intensity = calculate_intensity(angle, joint_name)
    
    if abs(angle - neutral_val) <= tolerance:
        return meaning["state"]["neutral"], intensity
    elif angle > neutral_val:
        return meaning["state"]["high"], intensity
    else:
        return meaning["state"]["low"], intensity

def generate_optimized_report(all_events, sensor_data=None):
    """
    Generates an optimized time-based report with delta comparison.
    - [NEUTRAL_POSE - 0.00s] comparison set (With Semantic States).
    - Intervals: Changes only.
    - Optimization: 
        - Suppress static hands/physics.
        - Remove 'State' line.
        - Add Degrees conversion ONLY for Delta.
        - Preserves Speed/Range % info.
        - Robust Float Casting.
        - Fix: Handles 0.0s Actions for initial pose.
    """
    
    def fmt_delta_deg(val_rad):
        try:
            val_deg = math.degrees(val_rad)
            return f"{val_rad:+.2f} rad ({val_deg:+.0f} deg)"
        except:
            return f"{val_rad:+.2f} rad"

    timestamps = set()
    for e in all_events:
        try:
            timestamps.add(float(e['start_time']))
            timestamps.add(float(e['end_time']))
        except (TypeError, ValueError):
            pass 
        
    sorted_times = sorted(list(timestamps))
    
    intervals = []
    for i in range(len(sorted_times) - 1):
        start = sorted_times[i]
        end = sorted_times[i+1]
        if end > start + MIN_TIME_INTERVAL_SEC:
            intervals.append((start, end))
            
    current_states = {}
    current_angles = {}
    
    for joint, angle in NEUTRAL_POSE.items():
        current_angles[joint] = angle
        current_states[joint] = "Neutral" 

    # --- Pre-calculate Angles at t=0.0 ---
    angles_at_zero = current_angles.copy()
    states_at_zero = current_states.copy()
    
    for e in all_events:
        try:
            t_start = float(e['start_time'])
            if abs(t_start - 0.0) < MIN_TIME_INTERVAL_SEC:
                if e['type'] == 'state':
                     try:
                        metrics = e.get('metrics', '')
                        if 'at ' in metrics:
                            val = float(metrics.split('at ')[1].split(' ')[0])
                            angles_at_zero[e['joint']] = val
                        desc = e['description'].replace("Maintained ", "")
                        states_at_zero[e['joint']] = desc
                     except: pass
                
                elif e['type'] == 'action':
                    try:
                        metrics = e.get('metrics', '')
                        if '->' in metrics:
                             start_val_str = metrics.split('->')[0].strip().split(' ')[0]
                             val = float(start_val_str)
                             angles_at_zero[e['joint']] = val
                    except: pass

        except: pass

    report = []
    
    # [NEUTRAL_POSE - 0.00s]
    report.append("[NEUTRAL_POSE - 0.00s]")
    
    def append_initial_delta_group(group_name):
        joints = JOINT_GROUPS.get(group_name, [])
        group_lines = []
        
        for joint in joints:
            neutral_angle = NEUTRAL_POSE.get(joint, 0.0)
            zero_angle = angles_at_zero.get(joint, 0.0)
            diff = zero_angle - neutral_angle
            
            if abs(diff) > SIGNIFICANT_ANGLE_DELTA_RAD:
                state_desc, intensity = get_state_desc(joint, zero_angle)
                
                delta_str = fmt_delta_deg(diff)
                metrics_str = f"{neutral_angle:.2f} -> {zero_angle:.2f} (Delta: {delta_str})"
                
                semantic_str = f"{state_desc}"
                if "Neutral" not in state_desc and "Aligned" not in state_desc and "Unknown" not in state_desc:
                     semantic_str += f" ({intensity:.1f}%)"
                
                group_lines.append(f"    - {joint}:")
                group_lines.append(f"      Action: {semantic_str} ({metrics_str})")
        
        if group_lines:
            report.append(f"  {group_name}:")
            report.extend(group_lines)

    append_initial_delta_group("HEAD")
    append_initial_delta_group("LEFT ARM")
    append_initial_delta_group("RIGHT ARM")
    
    # Hands (Neutral Comparison)
    hands_lines = []
    neutral_hand_val = 0.0
    
    def get_hand_pct(hand_name, angle_map):
        fingers = HAND_GROUPS[hand_name]
        total = 0.0; count = 0
        for joints in fingers.values():
            for j in joints:
                total += angle_map.get(j, 0.0)
                count += 1
        return (total / count * 100.0) if count > 0 else 0.0

    for h_name in ["LEFT HAND", "RIGHT HAND"]:
        curr_pct = get_hand_pct(h_name, angles_at_zero)
        delta = curr_pct - neutral_hand_val
        if abs(delta) > SIGNIFICANT_HAND_DELTA_PCT:
             direction = "Opening" if delta > 0 else "Closing"
             hands_lines.append(f"    - {h_name}: Hand {direction} ({neutral_hand_val:.1f}% -> {curr_pct:.1f}%)")
    
    if hands_lines:
        report.append("  HANDS:")
        report.extend(hands_lines)

    append_initial_delta_group("LEFT LEG")
    append_initial_delta_group("RIGHT LEG")

    # MAIN INTERVALS LOOP
    
    current_angles = angles_at_zero.copy()
    current_states = states_at_zero.copy()
    
    prev_hand_status = {
        "LEFT HAND": get_hand_pct("LEFT HAND", angles_at_zero),
        "RIGHT HAND": get_hand_pct("RIGHT HAND", angles_at_zero)
    }

    for start, end in intervals:
        mid_point = (start + end) / 2
        active_actions = {}
        active_statics = {}
        
        for e in all_events:
            try:
                t_s = float(e['start_time'])
                t_e = float(e['end_time'])
                
                if t_s <= mid_point <= t_e:
                    if e['type'] == 'action':
                        active_actions[e['joint']] = e
                    elif e['type'] == 'state':
                        active_statics[e['joint']] = e
                
                if t_s <= mid_point:
                     if e['type'] in ['state', 'state_transition']:
                        desc = e['description'].replace("Maintained ", "")
                        current_states[e['joint']] = desc
                        try:
                            metrics = e.get('metrics', '')
                            if 'at ' in metrics:
                                current_angles[e['joint']] = float(metrics.split('at ')[1].split(' ')[0])
                        except: pass
                     elif e['type'] == 'action':
                         try:
                            metrics = e.get('metrics', '')
                            if '->' in metrics:
                                 current_angles[e['joint']] = float(metrics.split('->')[1].strip().split(' ')[0])
                         except: pass
            except: pass
        
        physics_lines = []
        if sensor_data:
            def find_closest(target_time):
                if not sensor_data: return None
                return min(sensor_data, key=lambda x: abs(float(x['time']) - target_time))
            
            s_d = find_closest(start)
            e_d = find_closest(end)
            if s_d and e_d:
                def check_and_fmt(key, label, unit="", scale=1.0):
                    v1 = float(s_d.get(key, 0.0)) * scale
                    v2 = float(e_d.get(key, 0.0)) * scale
                    delta = v2 - v1
                    if abs(delta) > SIGNIFICANT_ANGLE_DELTA_RAD: 
                        delta_display = f"{delta:+.2f}"
                        if "rad" in unit:
                            delta_display = fmt_delta_deg(delta).replace(" rad", "") 
                        return f"    - {label}: {v1:.2f} -> {v2:.2f} (Delta: {delta_display}){unit}"
                    return None

                p1 = check_and_fmt('imu_pitch', "Torso Pitch", " rad")
                p2 = check_and_fmt('com_z', "CoM Z", " cm", scale=100.0)
                p3 = check_and_fmt('head_pitch', "Gaze Pitch", " rad")
                if p1 or p2 or p3:
                    physics_lines.append("  PHYSICS DATA:")
                    if p1: physics_lines.append(p1)
                    if p2: physics_lines.append(p2)
                    if p3: physics_lines.append(p3)

        groups_lines = []
        
        def append_changed_group(group_name):
            joints = JOINT_GROUPS.get(group_name, [])
            g_lines = []
            for joint in joints:
                if joint in active_actions:
                    evt = active_actions[joint]
                    action_str = evt['description']
                    
                    if 'metrics' in evt:
                        m_str = evt['metrics']
                        parts = m_str.split(',', 1) 
                        angle_part = parts[0]
                        suffix = parts[1] if len(parts) > 1 else ""
                        
                        new_angle_part = angle_part
                        try:
                            if '->' in angle_part:
                                sub_parts = angle_part.split('->')
                                v1_str = sub_parts[0].strip().split(' ')[0]
                                v2_str = sub_parts[1].strip().split(' ')[0]
                                v1 = float(v1_str)
                                v2 = float(v2_str)
                                diff = v2 - v1
                                delta_deg_str = fmt_delta_deg(diff)
                                new_angle_part = f"{v1:.2f} -> {v2:.2f} (Delta: {delta_deg_str})"
                        except: pass

                        if suffix:
                            m_str = f"{new_angle_part}, {suffix.strip()}"
                        else:
                            m_str = new_angle_part

                        action_str += f" ({m_str})"
                    
                    g_lines.append(f"    - {joint}:")
                    g_lines.append(f"      Action: {action_str}")
            
            if g_lines:
                groups_lines.append(f"  {group_name}:")
                groups_lines.extend(g_lines)

        append_changed_group("HEAD")
        append_changed_group("LEFT ARM")
        append_changed_group("RIGHT ARM")

        hand_block = []
        for h_name in ["LEFT HAND", "RIGHT HAND"]:
            curr_pct = get_hand_pct(h_name, current_angles)
            prev_pct = prev_hand_status.get(h_name, 0.0)
            delta = curr_pct - prev_pct
            prev_hand_status[h_name] = curr_pct
            if abs(delta) > SIGNIFICANT_HAND_DELTA_PCT:
                direction = "Opening" if delta > 0 else "Closing"
                hand_block.append(f"    - {h_name}: Hand {direction} ({prev_pct:.1f}% -> {curr_pct:.1f}%)")
        
        if hand_block:
             groups_lines.append("  HANDS:")
             groups_lines.extend(hand_block)

        append_changed_group("LEFT LEG")
        append_changed_group("RIGHT LEG")
        
        if physics_lines or groups_lines:
            report.append(f"\n[{start:.2f}s - {end:.2f}s]")
            if physics_lines:
                report.extend(physics_lines)
            if groups_lines:
                report.extend(groups_lines)
                
    return "\n".join(report)

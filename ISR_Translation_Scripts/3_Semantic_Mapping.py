
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from pace_config import NEUTRAL_POSE, JOINT_MEANINGS

# --- Configuration ---
# Set your desired tolerance (in radians) to consider a joint to be in its "Neutral" state
NEUTRAL_STATE_TOLERANCE_RAD = 0.1  # Replace with your own threshold
# ---------------------

def _calculate_intensity(angle, joint_name, constraints):
    """Calculates intensity % based on neutral and limits."""
    if not constraints or joint_name not in constraints['motors']:
        return 0.0
    
    neutral = NEUTRAL_POSE.get(joint_name, 0.0)
    limits = constraints['motors'][joint_name]
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

def _get_state(joint_name, angle, constraints):
    """Returns (state_description, intensity_percent)."""
    meaning = JOINT_MEANINGS.get(joint_name)
    if not meaning:
        return "Unknown State", 0.0
        
    neutral_val = NEUTRAL_POSE.get(joint_name, 0.0)
    intensity = _calculate_intensity(angle, joint_name, constraints)
    
    if abs(angle - neutral_val) <= NEUTRAL_STATE_TOLERANCE_RAD:
        return meaning["state"]["neutral"], intensity
    elif angle > neutral_val:
        return meaning["state"]["high"], intensity
    else:
        return meaning["state"]["low"], intensity

def interpret_joint(joint_name, profile_data, constraints):
    """
    Generates semantic events for a joint.
    Args:
        joint_name: Name of the joint
        profile_data: Dictionary containing 'segments' list
        constraints: Joint constraints (min/max)
    """
    events = []
    
    if not profile_data or 'segments' not in profile_data:
        return "", []

    for seg in profile_data['segments']:
        if not seg['is_moving']:
            avg_angle = seg.get('angle', 0.0)
            state_desc, intensity = _get_state(joint_name, avg_angle, constraints)
            
            meaning = JOINT_MEANINGS.get(joint_name)
            is_neutral = (meaning and state_desc == meaning["state"]["neutral"])
            
            desc_str = state_desc if is_neutral else f"{state_desc} ({intensity:.1f}%)"

            events.append({
                "start_time": seg['start_time'],
                "end_time": seg['end_time'],
                "joint": joint_name,
                "type": "state",
                "description": desc_str,
                "metrics": f"at {avg_angle:.2f} rad"
            })
            
        else:
            start_t = seg['start_time']
            end_t = seg['end_time']
            
            sub_segments = seg.get('sub_segment_details', [])
            
            if not sub_segments:
                start_a = seg['angles'][0]
                end_a = seg['angles'][-1]
                sub_segments = [{
                    'start_time': start_t, 'end_time': end_t,
                    'start_angle': start_a, 'end_angle': end_a,
                    'velocity_percent': seg.get('speed_percent', 0),
                    'range_percent': 0
                }]

            for sub in sub_segments:
                t0 = sub['start_time']
                t1 = sub['end_time']
                start_a = sub['start_angle']
                end_a = sub['end_angle']
                
                action = "Moving"
                meaning = JOINT_MEANINGS.get(joint_name)
                if meaning:
                    if end_a > start_a:
                        action = meaning["action"]["increase"]
                    else:
                        action = meaning["action"]["decrease"]
                
                start_state, start_int = _get_state(joint_name, start_a, constraints)
                end_state, end_int = _get_state(joint_name, end_a, constraints)
                
                start_is_neutral = (start_state == meaning["state"]["neutral"])
                end_is_neutral = (end_state == meaning["state"]["neutral"])

                start_str = start_state if start_is_neutral else f"{start_state} ({start_int:.1f}%)"
                end_str = end_state if end_is_neutral else f"{end_state} ({end_int:.1f}%)"

                if start_state == end_state:
                    if start_is_neutral:
                         state_info = start_state
                    else:
                        state_info = f"{start_state} ({start_int:.1f}% -> {end_int:.1f}%)"
                else:
                    state_info = f"{start_str} -> {end_str}"
                
                vel_pct = sub.get('velocity_percent', 0.0)
                range_pct = sub.get('range_percent', 0.0)
                
                events.append({
                    "start_time": t0,
                    "end_time": t1,
                    "joint": joint_name,
                    "type": "action",
                    "description": action,
                    "metrics": f"{start_a:.2f} -> {end_a:.2f} rad, Speed: {vel_pct:.1f}%, Range: {range_pct:.1f}%"
                })
                
                events.append({
                    "start_time": t0,
                    "end_time": t1,
                    "joint": joint_name,
                    "type": "state_transition",
                    "description": state_info,
                    "metrics": f"at {end_a:.2f} rad"
                })

    events.sort(key=lambda x: x['start_time'])
    
    summary_lines = []
    for e in events:
        if e['type'] == 'action':
            summary_lines.append(f"[{e['start_time']:.2f}-{e['end_time']:.2f}] {e['description']} ({e['metrics']})")
        elif e['type'] == 'state':
            summary_lines.append(f"[{e['start_time']:.2f}-{e['end_time']:.2f}] {e['description']} {e['metrics']}")
            
    return "\n".join(summary_lines), events

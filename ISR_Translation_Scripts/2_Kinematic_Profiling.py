import importlib
analyze_motion = importlib.import_module("1_Temporal_Segmentation")
import os

# --- Configuration ---
# Set your desired minimum velocity to consider a joint as "moving"
VELOCITY_THRESHOLD_RAD_PER_SEC = 0.0001  # Replace with your own threshold
# ---------------------

def analyze_joint(joint_name, movements, constraints):
    """
    Analyzes the movement pattern of a single joint and returns structured data.
    """
    if not movements:
        return None

    joint_constraints = constraints['motors'].get(joint_name, {})
    min_limit = joint_constraints.get('min', -float('inf'))
    max_limit = joint_constraints.get('max', float('inf'))
    max_vel_limit = joint_constraints.get('maxVelocity', float('inf'))

    segments = []
    current_segment = None

    for i in range(1, len(movements)):
        t_prev, angle_prev = movements[i-1]
        t_curr, angle_curr = movements[i]
        
        dt = t_curr - t_prev
        if dt <= 0: continue
        
        velocity = (angle_curr - angle_prev) / dt
        is_moving = abs(velocity) > VELOCITY_THRESHOLD_RAD_PER_SEC
        
        if current_segment is None:
            current_segment = {
                "start_time": t_prev,
                "end_time": t_curr,
                "is_moving": is_moving,
                "velocities": [velocity],
                "angles": [angle_prev, angle_curr],
                "times": [t_prev, t_curr]
            }
        else:
            if current_segment["is_moving"] == is_moving:
                current_segment["end_time"] = t_curr
                current_segment["velocities"].append(velocity)
                current_segment["angles"].append(angle_curr)
                current_segment["times"].append(t_curr)
            else:
                segments.append(current_segment)
                current_segment = {
                    "start_time": t_prev,
                    "end_time": t_curr,
                    "is_moving": is_moving,
                    "velocities": [velocity],
                    "angles": [angle_prev, angle_curr],
                    "times": [t_prev, t_curr]
                }
    
    if current_segment:
        segments.append(current_segment)

    processed_segments = []
    for seg in segments:
        duration = seg["end_time"] - seg["start_time"]
        seg_data = {
            "start_time": seg["start_time"],
            "end_time": seg["end_time"],
            "duration": duration,
            "is_moving": seg["is_moving"],
            "angles": seg["angles"],
            "velocities": seg["velocities"],
            "times": seg["times"]
        }
        
        if seg["is_moving"]:
            max_seg_vel = max(abs(v) for v in seg["velocities"])
            vel_percent = (max_seg_vel / max_vel_limit) * 100 if max_vel_limit != float('inf') else 0
            
            seg_data["max_speed"] = max_seg_vel
            seg_data["speed_percent"] = vel_percent
            
            velocities = seg["velocities"]
            angles = seg["angles"]
            times = seg["times"]
            
            significant_velocities = [v for v in velocities if abs(v) > VELOCITY_THRESHOLD_RAD_PER_SEC]
            
            if not significant_velocities:
                 seg_data["pattern"] = "Static (Noise)"
            else:
                sign_changes = 0
                turning_points = []
                current_sign = 1 if significant_velocities[0] > 0 else -1
                
                temp_sign = current_sign
                for i, v in enumerate(velocities):
                    if abs(v) <= VELOCITY_THRESHOLD_RAD_PER_SEC: continue
                    
                    new_sign = 1 if v > 0 else -1
                    if new_sign != temp_sign:
                        sign_changes += 1
                        temp_sign = new_sign
                        turning_points.append((times[i], angles[i], i))

                key_points_data = [(times[0], angles[0], 0)]
                key_points_data.extend(turning_points)
                key_points_data.append((times[-1], angles[-1], len(angles)-1))
                
                seg_data["key_points"] = [(t, a) for t, a, i in key_points_data]
                seg_data["sign_changes"] = sign_changes
                
                sub_segments = []
                total_range = max_limit - min_limit if (min_limit != -float('inf') and max_limit != float('inf')) else 1.0
                
                for k in range(len(key_points_data) - 1):
                    kp_start = key_points_data[k]
                    kp_end = key_points_data[k+1]
                    
                    start_idx = kp_start[2]
                    end_idx = kp_end[2]
                    
                    sub_velocities = velocities[start_idx:end_idx]
                    if not sub_velocities:
                         sub_max_vel = 0
                    else:
                        sub_max_vel = max(abs(v) for v in sub_velocities)
                    
                    sub_vel_percent = (sub_max_vel / max_vel_limit) * 100 if max_vel_limit != float('inf') else 0
                    
                    sub_range = abs(kp_end[1] - kp_start[1])
                    sub_range_percent = (sub_range / total_range) * 100
                    
                    sub_segments.append({
                        "start_time": kp_start[0],
                        "end_time": kp_end[0],
                        "start_angle": kp_start[1],
                        "end_angle": kp_end[1],
                        "max_velocity": sub_max_vel,
                        "velocity_percent": sub_vel_percent,
                        "range_used": sub_range,
                        "range_percent": sub_range_percent
                    })
                
                seg_data["sub_segment_details"] = sub_segments
                
                if sign_changes == 0:
                    direction = "Increase (+)" if current_sign > 0 else "Decrease (-)"
                    seg_data["pattern"] = f"Monotonic {direction}"
                elif sign_changes == 1:
                    seg_data["pattern"] = "Direction Change (1 reversal)"
                else:
                    cycles = (sign_changes + 1) / 2.0
                    seg_data["pattern"] = f"Repetition ({sign_changes} reversals, ~{cycles:.1f} cycles)"
        else:
            seg_data["angle"] = seg["angles"][0]
            
        processed_segments.append(seg_data)

    all_angles = [a for s in segments for a in s["angles"]]
    used_min = min(all_angles)
    used_max = max(all_angles)
    range_span = used_max - used_min
    
    usage_percent = 0
    if min_limit != -float('inf') and max_limit != float('inf'):
        total_range = max_limit - min_limit
        usage_percent = (range_span / total_range) * 100

    return {
        "joint_name": joint_name,
        "range_used": (used_min, used_max),
        "range_span": range_span,
        "usage_percent": usage_percent,
        "physical_limit": (min_limit, max_limit),
        "segments": processed_segments
    }

def format_profile(analysis_data):
    """
    Formats the structured analysis data into a readable string.
    """
    if not analysis_data:
        return "No movement data."

    description = []
    
    used_min, used_max = analysis_data["range_used"]
    min_limit, max_limit = analysis_data["physical_limit"]
    
    description.append(f"Range Used: {used_min:.2f} to {used_max:.2f} (Span: {analysis_data['range_span']:.2f})")
    if min_limit != -float('inf'):
        description.append(f"  - Covers {analysis_data['usage_percent']:.1f}% of physical limit ({min_limit} to {max_limit})")

    # Segment details
    description.append("Activity Log:")
    for seg in analysis_data["segments"]:
        if seg["is_moving"]:
            desc = f"  - [MOVING] {seg['start_time']:.2f}s -> {seg['end_time']:.2f}s ({seg['duration']:.2f}s)"
            desc += f" | Max Speed: {seg['max_speed']:.2f} rad/s ({seg['speed_percent']:.1f}% of max)"
            desc += f" | Pattern: {seg['pattern']}"
            if "path" in seg:
                desc += f" | Path: {seg['path']}"
            description.append(desc)
        else:
            description.append(f"  - [STATIC] {seg['start_time']:.2f}s -> {seg['end_time']:.2f}s ({seg['duration']:.2f}s) at {seg['angle']:.2f} rad")

    return "\n".join(description)

def profile_joint(joint_name, movements, constraints):
    data = analyze_joint(joint_name, movements, constraints)
    return format_profile(data)

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    constraints_path = os.path.join(current_dir, '..', 'joint_constraints.json')
    motion_path = os.path.join(current_dir, '..', 'data', 'sample_motion.json')
    
    if not os.path.exists(constraints_path) or not os.path.exists(motion_path):
        print("Files not found.")
        return

    joint_movements, constraints = analyze_motion.get_motion_data(constraints_path, motion_path)
    
    print("Kinematic Profiling Report")
    print("=========================")
    
    for joint in sorted(joint_movements.keys()):
        print(f"\n### Joint: {joint}")
        profile = profile_joint(joint, joint_movements[joint], constraints)
        print(profile)

if __name__ == "__main__":
    main()

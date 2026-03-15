import collections

# Define Joint Groups for Output Ordering
JOINT_GROUPS = {
    "LEFT LEG": ["LHipYawPitch", "LHipRoll", "LHipPitch", "LKneePitch", "LAnklePitch", "LAnkleRoll"],
    "RIGHT LEG": ["RHipYawPitch", "RHipRoll", "RHipPitch", "RKneePitch", "RAnklePitch", "RAnkleRoll"],
    "LEFT ARM": ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw"],
    "RIGHT ARM": ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw"],
    "LEFT HAND": ["LPhalanx1", "LPhalanx2", "LPhalanx3", "LPhalanx4", "LPhalanx5", "LPhalanx6", "LPhalanx7", "LPhalanx8"],
    "RIGHT HAND": ["RPhalanx1", "RPhalanx2", "RPhalanx3", "RPhalanx4", "RPhalanx5", "RPhalanx6", "RPhalanx7", "RPhalanx8"],
    "HEAD": ["HeadYaw", "HeadPitch"]
}

def aggregate_and_sort(all_events):
    """
    Aggregates events from all joints and sorts them chronologically.
    (Kept for compatibility, though main logic is now in generate_interval_report)
    """
    return sorted(all_events, key=lambda x: x['start_time'])

def generate_time_based_report(all_events, sensor_data=None):
    """
    Generates a formatted time-based report with snapshots of all joints per interval.
    Separates Action and State information.
    Includes Physics Data (IMU, CoM, Head) if provided.
    """
    timestamps = set()
    for e in all_events:
        timestamps.add(e['start_time'])
        timestamps.add(e['end_time'])
        
    sorted_times = sorted(list(timestamps))
    
    intervals = []
    for i in range(len(sorted_times) - 1):
        start = sorted_times[i]
        end = sorted_times[i+1]
        if end > start + 0.001: # Filter extremely small intervals
            intervals.append((start, end))
            
    current_states = collections.defaultdict(lambda: "Neutral")
    
    sorted_events = sorted(all_events, key=lambda x: x['start_time'])
    
    report = []
    report.append("Global State Integration Report")
    report.append("==========================================")
    
    for start, end in intervals:
        mid_point = (start + end) / 2
        
        # Update current_states
        active_actions = {}
        active_statics = {}
        
        for e in all_events:
            if e['start_time'] <= mid_point <= e['end_time']:
                if e['type'] == 'action':
                    active_actions[e['joint']] = e
                elif e['type'] == 'state':
                    active_statics[e['joint']] = e
            
            if e['start_time'] <= mid_point:
                if e['type'] == 'state':
                    desc = e['description'].replace("Maintained ", "")
                    current_states[e['joint']] = desc
                elif e['type'] == 'state_transition':
                    current_states[e['joint']] = e['description']
                    
        report.append(f"\n[{start:.2f}s - {end:.2f}s]")
        
        # --- Physics Data Section ---
        if sensor_data:
            def find_closest(target_time):
                if not sensor_data: return None
                closest = min(sensor_data, key=lambda x: abs(x['time'] - target_time))
                if abs(closest['time'] - target_time) > 0.5:
                    return None
                return closest

            start_data = find_closest(start)
            end_data = find_closest(end)
            
            if start_data and end_data:
                report.append("  PHYSICS DATA:")
                
                # Helper to format change
                def fmt_change(key, label, unit="", scale=1.0):
                    v1 = start_data.get(key, 0.0) * scale
                    v2 = end_data.get(key, 0.0) * scale
                    diff = v2 - v1
                    return f"    - {label}: {v1:.2f} -> {v2:.2f} (Delta: {diff:+.2f}){unit}"

                report.append(fmt_change('imu_pitch', "Torso Pitch", " rad"))
                report.append(fmt_change('imu_roll', "Torso Roll", " rad"))
                report.append(fmt_change('com_z', "CoM Z", " cm", scale=100.0))
                report.append(fmt_change('head_pitch', "Gaze Pitch", " rad"))
                
                # FSR Data (Show change)
                report.append(fmt_change('fsr_left', "Left Foot Force", " N"))
                report.append(fmt_change('fsr_right', "Right Foot Force", " N"))
        
        # --- Joint Data Section ---
        for group_name, joints in JOINT_GROUPS.items():
            group_lines = []
            for joint in joints:
                action_str = "-"
                state_str = current_states[joint]
                
                if joint in active_statics:
                    evt = active_statics[joint]
                    state_str = evt['description'].replace("Maintained ", "")
                    if 'metrics' in evt:
                        state_str += f" ({evt['metrics']})"
                    action_str = "-"
                    
                elif joint in active_actions:
                    evt = active_actions[joint]
                    action_str = evt['description']
                    if 'metrics' in evt:
                        action_str += f" ({evt['metrics']})"
                    
                group_lines.append(f"    - {joint}:")
                group_lines.append(f"      Action: {action_str}")
                group_lines.append(f"      State: {state_str}")
            
            if group_lines:
                report.append(f"  {group_name}:")
                report.extend(group_lines)
                
    return "\n".join(report)

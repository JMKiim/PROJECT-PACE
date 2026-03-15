import socket
import os
import json
import subprocess
from contextlib import closing

# --- Configuration ---
# Set the tolerance thresholds for floating point comparison
ANGLE_TOLERANCE_RAD = 1e-4      # Replace with your own tolerance
VELOCITY_TOLERANCE_RAD_S = 1e-4 # Replace with your own tolerance
ZERO_TIME_TOLERANCE_S = 1e-6    # Replace with your own tolerance
# ---------------------

def find_free_port(start_port=1235, max_attempts=50):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
    return None

def validate_angle_constraints(motion_keyframes, constraints):
    """
    Checks if joint angles in all keyframes are within [min, max] limits.
    constraints: The 'motors' dictionary from joint_constraints.json
    """
    errors = []
    
    for kf in motion_keyframes:
        time_val = kf.get('time', 0.0)
        angles = kf.get('angles', {})
        
        for joint_name, target_angle in angles.items():
            if joint_name in constraints:
                c = constraints[joint_name]
                min_limit = c.get("min")
                max_limit = c.get("max")
                
                # Tolerance for floating point errors
                tolerance = ANGLE_TOLERANCE_RAD

                if min_limit is not None and target_angle < min_limit - tolerance:
                    errors.append({
                        "error": "Joint Angle Violation", 
                        "time": time_val, 
                        "joint": joint_name,
                        "value": round(target_angle, 4), 
                        "limit": round(min_limit, 4),
                        "message": f"Time {time_val:.2f}s '{joint_name}' angle {target_angle:.2f} < min {min_limit:.2f}"
                    })
                
                if max_limit is not None and target_angle > max_limit + tolerance:
                    errors.append({
                        "error": "Joint Angle Violation", 
                        "time": time_val, 
                        "joint": joint_name,
                        "value": round(target_angle, 4), 
                        "limit": round(max_limit, 4),
                        "message": f"Time {time_val:.2f}s '{joint_name}' angle {target_angle:.2f} > max {max_limit:.2f}"
                    })
    return errors

def validate_velocity_constraints(motion_keyframes, constraints, initial_pose):
    """
    Checks if the velocity between keyframes exceeds maxVelocity.
    constraints: The 'motors' dictionary from joint_constraints.json
    initial_pose: Dictionary of initial angles (NEUTRAL_POSE)
    """
    errors = []
    
    # 1. Check start time (Time 0.0)
    first_kf = motion_keyframes[0]
    if abs(first_kf.get('time', 0.0)) < ZERO_TIME_TOLERANCE_S:
        prev_pose = first_kf.get('angles', {})
        prev_time = 0.0
        start_idx = 1
    else:
        prev_pose = initial_pose
        prev_time = 0.0
        start_idx = 0
        
    for i in range(start_idx, len(motion_keyframes)):
        kf = motion_keyframes[i]
        curr_pose = kf.get('angles', {})
        curr_time = kf.get('time', 0.0)
        duration = curr_time - prev_time
        
        # Check instantaneous movement
        if duration <= ZERO_TIME_TOLERANCE_S:
            # If duration is effectively zero, check if angles changed
            changed = False
            for j, angle in curr_pose.items():
                prev_angle = prev_pose.get(j, initial_pose.get(j, 0.0)) # Fallback to initial
                if abs(angle - prev_angle) > ZERO_TIME_TOLERANCE_S:
                    changed = True
                    break
            
            if changed:
                errors.append({
                    "error": "Instantaneous Movement", 
                    "time": curr_time,
                    "message": f"Time {curr_time:.2f}s: duration is 0 but pose changed."
                })
            
            prev_time = curr_time
            prev_pose = curr_pose
            continue
            
        # Check velocity for each joint
        for joint_name, target_angle in curr_pose.items():
            if joint_name in constraints:
                # Get start angle (from prev_pose or initial fallback)
                start_angle = prev_pose.get(joint_name, initial_pose.get(joint_name, 0.0))
                max_velocity = constraints[joint_name].get("maxVelocity")
                
                if max_velocity is not None and max_velocity > 0:
                    angle_diff = abs(target_angle - start_angle)
                    if angle_diff < ZERO_TIME_TOLERANCE_S: 
                        continue
                        
                    required_velocity = angle_diff / duration
                    
                    if required_velocity > max_velocity + VELOCITY_TOLERANCE_RAD_S: # Tolerance
                        errors.append({
                            "error": "Joint Velocity Violation", 
                            "time_end": curr_time,
                            "joint": joint_name, 
                            "required_velocity": round(required_velocity, 2),
                            "max_velocity": round(max_velocity, 2),
                            "message": f"Time {prev_time:.2f}s->{curr_time:.2f}s '{joint_name}' vel {required_velocity:.2f} > max {max_velocity:.2f}"
                        })
        
        prev_time = curr_time
        prev_pose = curr_pose
        
    return errors

def _validate_agent_fall(motion_keyframes):
    """
    [HELPER] Runs Webots via subprocess to check for agent fall violations.
    Uses valid path provided by user.
    """
    print("\n[Validator] Running Agent Fall Violation Check...")
    
    VALIDATION_MOTION_FILE = "motion_to_validate.json"
    FALL_REPORT_FILE = "agent_fall_report.json"
    
    # Environment variable for Webots world path or generic fallback
    WORLD_FILE_PATH = os.environ.get("WEBOTS_WORLD_PATH", "path/to/validation_world.wbt")
    
    errors = []
    
    # [MODIFIED] Dynamic Port Allocation
    # Find a unique port for this validation instance to allow parallel execution
    # Start high to avoid common ports like 1234
    port = find_free_port(start_port=2000)
    if not port:
         return [{"error": "PortError", "message": "Could not find a free port for Webots."}]

    print(f"   [Validator] assigned Port: {port}")
    
    # Use unique filenames for this instance based on port/time to unnecessary conflicts
    # Actually, Webots controller needs to know WHICH file to read.
    # We can pass the input file path via Environment Variable!
    
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    INSTANCE_MOTION_FILE = f"motion_val_{unique_id}.json"
    INSTANCE_REPORT_FILE = f"report_val_{unique_id}.json"

    try:
        # Clean up files if exist (unlikely due to uuid)
        if os.path.exists(INSTANCE_REPORT_FILE): os.remove(INSTANCE_REPORT_FILE)
    except: pass

    try:
        # Write to unique file
        with open(INSTANCE_MOTION_FILE, "w", encoding="utf-8") as f:
            json.dump(motion_keyframes, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
    except Exception as e:
        if os.path.exists(INSTANCE_MOTION_FILE):
             try: os.remove(INSTANCE_MOTION_FILE)
             except: pass
        return [{"error": "ValidationFileError", "message": str(e)}]

    # Environment Setup
    env = os.environ.copy() 
    env["AGENT_VALIDATION_MODE"] = "BATCH"
    env["PYTHONUNBUFFERED"] = "1"
    env["AGENT_PROJECT_ROOT"] = os.getcwd()
    
    # [IMPORTANT] Pass the unique file names to the Controller
    # The controller must be updated to read these env vars!
    env["VAL_INPUT_FILE"] = INSTANCE_MOTION_FILE
    env["VAL_OUTPUT_FILE"] = INSTANCE_REPORT_FILE
    
    # [MODIFIED] Use assigned dynamic port
    command = f'webots --stdout --stderr --mode=realtime --port={port} --batch "{WORLD_FILE_PATH}"'
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            shell=True,
            env=env
        )

        webots_log = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                 text = output.strip()
                 webots_log.append(text)
                 # Print Webots logs to console if needed (Suppress Warnings)
                 if "Warning" not in text and "WARNING" not in text and "[DEBUG]" not in text:
                     pass # print(f"[Webots] {text}")
        
        full_log_str = "\n".join(webots_log)
        
        rc = process.poll()
        
        # Check Report
        if not os.path.exists(INSTANCE_REPORT_FILE):
            errors.append({
                "error": "Agent Fall Violation", 
                "message": "Controller did not produce a report file.",
                "webots_log": full_log_str
            })
        else:
            with open(INSTANCE_REPORT_FILE, "r", encoding="utf-8") as f:
                report = json.load(f)

            
            if report.get("status") == "FAILED":
                fail_reason = report.get("reason", "Unknown agent fall failure")
                errors.append({
                    "error": "Agent Fall Violation", 
                    "message": fail_reason,
                    "webots_log": full_log_str # [ADDED] Return log on validation failure
                })
                print(f"      Agent Fall Check FAILED: {fail_reason}")
                errors.append({"error": "Agent Fall Violation", "message": fail_reason})
            else:
                 print("      Agent Fall Check PASSED!")

    except Exception as e:
        return [{"error": "WebotsExecutionError", "message": str(e)}]
        
    finally:
        # Cleanup unique files
        try:
            if os.path.exists(INSTANCE_MOTION_FILE): os.remove(INSTANCE_MOTION_FILE)
            if os.path.exists(INSTANCE_REPORT_FILE): os.remove(INSTANCE_REPORT_FILE)
        except:
            pass
    
    return errors

def validate_motion(motion_keyframes, constraints_data, initial_pose, 
                    check_angles=True, check_velocity=True, check_agent_fall=True):
    """
    Main validation function.
    constraints_data: The full loaded dictionary from joint_constraints.json
    flags: Toggle specific checks (default: All True)
    """
    if not isinstance(motion_keyframes, list) or len(motion_keyframes) == 0:
        return False, ["Video content is empty or invalid format."]

    constraints = constraints_data.get("motors", {})
    master_errors = []
    
    # 1. Angle Check (Joint Angle Violation)
    if check_angles:
        angle_errors = validate_angle_constraints(motion_keyframes, constraints)
        master_errors.extend(angle_errors)
    
    # 2. Velocity Check (Joint Velocity Violation)
    if check_velocity:
        vel_errors = validate_velocity_constraints(motion_keyframes, constraints, initial_pose)
        master_errors.extend(vel_errors)
    
    # 3. Agent Fall Check (Webots)
    # Only run if kinematic checks matched (to save time) AND flag is True
    if check_agent_fall and not master_errors:
        fall_errors = _validate_agent_fall(motion_keyframes)
        master_errors.extend(fall_errors)
    
    if master_errors:
        return False, master_errors
    
    return True, []

import random
import subprocess
import sys
from collections import defaultdict

# --- Configuration ---
SOLUTION_SCRIPT_NAME = "main.py" # The name of your solution file
TIMEOUT_SECONDS = 10              # Max time your solution is allowed to run
NUM_TESTS = 2                # Number of tests to run for the mean

# --- Test Case Generation Parameters ---
# Feel free to change these to test different scenarios
GENERATE_PARAMS = {
    "M_range": (5, 15),
    "N_range": (5, 15),
    "FN_range": (10, 50),
    "T_range": (100, 200),
    "B_range": (0.0, 1000.0),
    "Q_total_range": (1, 3000),
}

# --- Bandwidth Model (from PDF) ---
def get_bandwidth_multiplier(t_effective):
    t_mod_10 = t_effective % 10
    if t_mod_10 in [0, 1, 8, 9]: return 0.0
    if t_mod_10 in [2, 7]: return 0.5
    return 1.0

def generate_test_case():
    M = 70
    N = 70
    FN = 5000
    T = 500

    lines = [f"{M} {N} {FN} {T}"]
    
    for x in range(M):
        for y in range(N):
            B = round(random.uniform(*GENERATE_PARAMS["B_range"]), 2)
            phi = random.randint(0, 9)
            lines.append(f"{x} {y} {B} {phi}")

    # Generate Flows
    for f in range(FN):
        access_x = random.randint(0, M - 1)
        access_y = random.randint(0, N - 1)
        t_start = random.randint(0, 3 * T // 4)
        Q_total = random.randint(*GENERATE_PARAMS["Q_total_range"])
        
        m1 = random.randint(0, M - 1)
        m2 = random.randint(m1, M - 1)
        n1 = random.randint(0, N - 1)
        n2 = random.randint(n1, N - 1)
        
        lines.append(f"{f} {access_x} {access_y} {t_start} {Q_total} {m1} {n1} {m2} {n2}")
    
    return "\n".join(lines)

def run_solution(test_case_str):
    """Executes the user's solution and captures the output."""
    try:
        process = subprocess.run(
            [sys.executable, SOLUTION_SCRIPT_NAME],
            input=test_case_str,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=True
        )
        return process.stdout, None
    except FileNotFoundError:
        return None, f"ERROR: Solution script '{SOLUTION_SCRIPT_NAME}' not found."
    except subprocess.TimeoutExpired:
        return None, f"ERROR: Solution timed out after {TIMEOUT_SECONDS} seconds."
    except subprocess.CalledProcessError as e:
        return None, f"ERROR: Solution script crashed.\n--- STDERR ---\n{e.stderr}"

def parse_and_score(solution_output, test_case_str, verbose=True):
    """Parses the solution and scores it based on the official rules.
    
    If verbose=False, suppresses all print output.
    """
    # --- 1. Parse Inputs for Scoring ---
    lines = test_case_str.split('\n')
    M, N, FN, T = map(int, lines[0].split())
    
    uavs = {}
    for i in range(1, 1 + M * N):
        x, y, B, phi = lines[i].split()
        uavs[(int(x), int(y))] = {'B': float(B), 'phi': int(phi)}

    flows = {}
    total_q_all_flows = 0
    for i in range(1 + M * N, 1 + M * N + FN):
        f, x, y, ts, qt, m1, n1, m2, n2 = map(int, lines[i].split())
        flows[f] = {'ax':x, 'ay':y, 'ts':ts, 'qt':qt, 'm1':m1, 'n1':n1, 'm2':m2, 'n2':n2}
        total_q_all_flows += qt
        
    # --- 2. Parse Solution Output ---
    try:
        output_lines = solution_output.strip().split('\n')
        parsed_solution = defaultdict(list)
        line_idx = 0
        while line_idx < len(output_lines):
            f, p = map(int, output_lines[line_idx].split())
            line_idx += 1
            for _ in range(p):
                t, x, y, z = output_lines[line_idx].split()
                parsed_solution[f].append({'t':int(t), 'x':int(x), 'y':int(y), 'z':float(z)})
                line_idx += 1
    except Exception as e:
        if verbose:
            print(f"--- Scoring Error: Failed to parse solution output. ---")
            print(f"Error: {e}\nOutput preview:\n{' '.join(output_lines[:5])}...")
        return 0.0 # Return 0 for unparseable output

    # --- 3. Validate and Score ---
    validation_errors = []
    uav_usage = defaultdict(lambda: defaultdict(float))
    
    flow_scores = {}
    
    for f in range(FN): # Iterate through all expected flows to handle non-submission cases
        if f not in parsed_solution:
            flow_scores[f] = {'total': 0, 'traffic': 0, 'delay': 0, 'distance': 0, 'landing': 0}
            continue

        records = parsed_solution[f]
        flow_info = flows[f]
        total_sent_q = 0
        delay_score_num = 0
        dist_score_num = 0
        landing_points = set()

        for rec in records:
            t, x, y, z = rec['t'], rec['x'], rec['y'], rec['z']
            
            if not (flow_info['m1'] <= x <= flow_info['m2'] and flow_info['n1'] <= y <= flow_info['n2']):
                validation_errors.append(f"Flow {f} @t={t}: Landing point ({x},{y}) is outside its allowed range.")
            if t < flow_info['ts'] or t >= T:
                validation_errors.append(f"Flow {f} @t={t}: Transmission time is outside allowed range [{flow_info['ts']}, {T-1}].")
            
            uav_usage[t][(x,y)] += z
            total_sent_q += z
            landing_points.add((x,y))
            
            delay = t - flow_info['ts']
            distance = abs(x - flow_info['ax']) + abs(y - flow_info['ay'])
            
            delay_score_num += (10 / (delay + 10)) * z
            dist_score_num += (2**(-0.1 * distance)) * z

        if total_sent_q > flow_info['qt'] * 1.0001:
            validation_errors.append(f"Flow {f}: Total sent traffic ({total_sent_q:.2f}) exceeds Q_total ({flow_info['qt']}).")

        q_total = flow_info['qt']
        traffic_score = min(total_sent_q, q_total) / q_total if q_total > 0 else 0
        delay_score = delay_score_num / q_total if q_total > 0 else 0
        dist_score = dist_score_num / q_total if q_total > 0 else 0
        landing_score = 1.0 / len(landing_points) if landing_points else 0

        final_flow_score = 100 * (0.4 * traffic_score + 0.2 * delay_score + 0.3 * dist_score + 0.1 * landing_score)
        
        flow_scores[f] = {
            'total': final_flow_score,
            'traffic': traffic_score,
            'delay': delay_score,
            'distance': dist_score,
            'landing': landing_score
        }

    for t, usage_at_t in uav_usage.items():
        for (x,y), total_z in usage_at_t.items():
            uav_info = uavs[(x,y)]
            effective_time = t + uav_info['phi']
            capacity = uav_info['B'] * get_bandwidth_multiplier(effective_time)
            if total_z > capacity * 1.0001:
                validation_errors.append(f"UAV ({x},{y}) @t={t}: Exceeded capacity. Used: {total_z:.2f}, Capacity: {capacity:.2f}")

    # --- 4. Calculate Final Score ---
    overall_score = 0
    if total_q_all_flows > 0:
        for f, scores in flow_scores.items():
            overall_score += (flows[f]['qt'] / total_q_all_flows) * scores['total']
            
    # --- 5. Print Report (if verbose) ---
    if verbose:
        print("\n" + "="*60)
        print(" " * 22 + "SCORING REPORT")
        print("="*60)
        
        if validation_errors:
            print(f"\n🚨 Found {len(validation_errors)} VALIDATION ERRORS: 🚨")
            for err in validation_errors[:5]:
                print(f"  - {err}")
            if len(validation_errors) > 5:
                print(f"  ... and {len(validation_errors) - 5} more.")
            print("\nNote: Scores are calculated but may be invalid due to errors.")
            
        print(f"\n🏆 FINAL SCORE: {overall_score:.4f} 🏆\n")
        print("--- Score Breakdown (All Flows) ---")
        
        for f_id, scores in flow_scores.items():
            print(f"  Flow {f_id:<4} | Total Score: {scores['total']:>6.2f}")
            print(f"    └ Traffic: {scores['traffic']:.3f} | Delay: {scores['delay']:.3f} | Distance: {scores['distance']:.3f} | Landing: {scores['landing']:.3f}")
        
        print("="*60)

    return overall_score


if __name__ == "__main__":
    all_scores = []
    failed_tests = 0
    
    print(f"--- UAV Traffic Scheduler Tester ---")
    print(f"--- Running {NUM_TESTS} Test Cases ---")
    
    for i in range(NUM_TESTS):
        # Update progress bar
        progress = (i + 1) / NUM_TESTS
        bar_length = 30
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'Progress: |{bar}| {i+1}/{NUM_TESTS} ({progress*100:.1f}%)', end='\r')

        test_case = generate_test_case()
        output, error = run_solution(test_case)
        
        if error:
            print() # Move to a new line after the progress bar
            print(f"Test {i+1}/{NUM_TESTS} FAILED: {error.splitlines()[0]}")
            failed_tests += 1
            all_scores.append(0.0) 
        else:
            try:
                # Run scoring silently
                score = parse_and_score(output, test_case, verbose=False)
                all_scores.append(score)
            except Exception as e:
                print() # Move to a new line
                print(f"Test {i+1}/{NUM_TESTS} CRASHED DURING SCORING: {e}")
                failed_tests += 1
                all_scores.append(0.0)

    # Final summary
    print(f"\n\n{'='*30}")
    print("     TESTING SUMMARY")
    print(f"{'='*30}")
    
    if all_scores:
        mean_score = sum(all_scores) / len(all_scores)
        print(f"Total Tests Run:    {NUM_TESTS}")
        print(f"Tests Failed/Crashed: {failed_tests}")
        print(f"Successful Runs:    {NUM_TESTS - failed_tests}")
        print(f"\n🏆 MEAN SCORE: {mean_score:.4f} 🏆")
    else:
        print("No tests were run.")
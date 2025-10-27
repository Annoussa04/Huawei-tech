def get_bandwidth_multiplier(t_effective):
    t_mod_10 = t_effective % 10
    if t_mod_10 in [0, 1, 8, 9]:
        return 0.0
    elif t_mod_10 in [2, 7]:
        return 0.5
    else:
        return 1.0

EPSILON = 1e-9
ALPHA = 0.1
T_max = 10

M, N, FN, T = map(int, input().split())

UAVs = {}
for _ in range(M * N):
    line = input().split()
    x, y, B, phi = int(line[0]), int(line[1]), float(line[2]), int(line[3])
    UAVs[(x, y)] = {'B': B, 'phi': phi}

flows = {}
record_of_flows = {}
for _ in range(FN):
    f, x, y, t_start, Q_total, m1, n1, m2, n2 = map(int, input().split())
    record_of_flows[f] = []
    flows[f] = {
        'access_x': x, 'access_y': y, 't_start': t_start,
        'Q_total': float(Q_total), 'Q_rem': float(Q_total),
        'm1': m1, 'n1': n1, 'm2': m2, 'n2': n2,
        'last_uav': None, 'change_count': 0, 'score': 0 
    }

for t in range(T):
    available_bw = {}
    used_UAVs = set()
    for (x, y), uav_data in UAVs.items():
        B = uav_data['B']
        phi = uav_data['phi']
        effective_time = t + phi
        multiplier = get_bandwidth_multiplier(effective_time)
        available_bw[(x, y)] = B * multiplier
    
    def get_flow_priority(flow_item):
        f, data = flow_item
        Q_total = data['Q_total']
        best_uav_coords = None
        best_score = float('-inf')
        Q_rem = data['Q_rem']
        access_x, access_y = data['access_x'], data['access_y']
        m1, n1, m2, n2 = data['m1'], data['n1'], data['m2'], data['n2']
        for i in range(m1, m2 + 1):
            for j in range(n1, n2 + 1):
                candidate_coords = (i, j)

                if candidate_coords in available_bw and available_bw[candidate_coords] > 0:
                    distance = abs(access_x - i) + abs(access_y - j)
                    distance_score_multiplier = 2 ** (-ALPHA * distance)
                    q_i = min(data['Q_rem'], available_bw[candidate_coords])
                    score = 0.3 * q_i * distance_score_multiplier / Q_total
                    score += 0.4 * (q_i / Q_total) + 0.2 * T_max * q_i / ((t + T_max) * Q_total)
                    if (i, j) != data['last_uav']:
                        if data['change_count'] == 0:
                            score += 0.1
                        else:
                            score = score + 0.1 / (data['change_count'] + 1) - 0.1 / (data['change_count'])
                    score = Q_rem + Q_total*score
                    if score > best_score:
                        best_score = score
                        best_uav_coords = candidate_coords
        urgency = best_score

        return urgency, f, data, best_uav_coords
    
    def assign_UAV(flow_item):
        f, data = flow_item
        Q_total = data['Q_total']
        best_uav_coords = None
        best_score = float('-inf')
        Q_rem = data['Q_rem']
        access_x, access_y = data['access_x'], data['access_y']
        m1, n1, m2, n2 = data['m1'], data['n1'], data['m2'], data['n2']
        for i in range(m1, m2 + 1):
            for j in range(n1, n2 + 1):
                candidate_coords = (i, j)
                if candidate_coords in available_bw and available_bw[candidate_coords] > 0:
                    distance = abs(access_x - i) + abs(access_y - j)
                    distance_score_multiplier = 2 ** (-ALPHA * distance)
                    q_i = min(data['Q_rem'], available_bw[candidate_coords])
                    score = 0.3 * q_i * distance_score_multiplier / Q_total
                    score += 0.4 * (q_i / Q_total) + 0.2 * T_max * q_i / ((t + T_max) * Q_total)
                    if (i, j) != data['last_uav']:
                        if data['change_count'] == 0:
                            score += 0.1
                        else:
                            score = score + 0.1 / (data['change_count'] + 1) - 0.1 / (data['change_count'])
                    score = Q_rem + Q_total*score
                    if score > best_score:
                        best_score = score
                        best_uav_coords = candidate_coords
        urgency = best_score

        if best_uav_coords is not None:
            q_transferrable = min(data['Q_rem'], available_bw[best_uav_coords])

            if q_transferrable > 0:
                if best_uav_coords != data['last_uav']:
                    data['change_count'] += 1

                data['Q_rem'] -= q_transferrable
                available_bw[best_uav_coords] -= q_transferrable
                data['last_uav'] = best_uav_coords

                uav_x, uav_y = best_uav_coords
                record_of_flows[f].append([t, uav_x, uav_y, q_transferrable])

        return urgency, f, data, best_uav_coords


    active_flows = []
    for f, data in flows.items():
        if data['t_start'] <= t and data['Q_rem'] > 0:
            active_flows.append(get_flow_priority((f, data)))

    sorted_active_flows = sorted(active_flows, reverse=True)

    for urgency, f, flow_data, best_uav_coords in sorted_active_flows:
        if best_uav_coords in used_UAVs:
            assign_UAV((f,flow_data))
        else :
            if best_uav_coords is not None:
                used_UAVs.add((best_uav_coords))
                q_transferrable = min(flow_data['Q_rem'], available_bw[best_uav_coords])

                if q_transferrable > 0:
                    if best_uav_coords != flow_data['last_uav']:
                        flow_data['change_count'] += 1

                    flow_data['Q_rem'] -= q_transferrable
                    available_bw[best_uav_coords] -= q_transferrable
                    flow_data['last_uav'] = best_uav_coords

                    uav_x, uav_y = best_uav_coords
                    record_of_flows[f].append([t, uav_x, uav_y, q_transferrable])


for f, records in record_of_flows.items():
    print(f, len(records))
    for rec in records:
        print(f"{rec[0]} {rec[1]} {rec[2]} {rec[3]}")
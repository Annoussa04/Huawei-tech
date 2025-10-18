def get_bandwidth_multiplier(t_effective):
    t_mod_10 = t_effective % 10
    if t_mod_10 in [0, 1, 8, 9]:
        return 0.0
    elif t_mod_10 in [2, 7]:
        return 0.5
    else:
        return 1.0


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
        'Q_rem': float(Q_total),
        'm1': m1, 'n1': n1, 'm2': m2, 'n2': n2
            }

for t in range(T):
    available_bw = {}
    for (x, y), uav_data in UAVs.items():
        B = uav_data['B']
        phi = uav_data['phi']
        effective_time = t + phi
        multiplier = get_bandwidth_multiplier(effective_time)
        available_bw[(x, y)] = B * multiplier

    sorted_flows = sorted(flows.items(), key=lambda item: item[1]['t_start'])

    for f, flow_data in sorted_flows:
        if flow_data['t_start'] <= t and flow_data['Q_rem'] > 1e-9: 
            
            m1, n1, m2, n2 = flow_data['m1'], flow_data['n1'], flow_data['m2'], flow_data['n2']
            
            for i in range(m1, m2 + 1):
                for j in range(n1, n2 + 1):
                    landing_uav_coords = (i, j)
              
                    if landing_uav_coords in available_bw and available_bw[landing_uav_coords] > 1e-9:
                        q_transferrable = min(flow_data['Q_rem'], available_bw[landing_uav_coords])
                        
                        flow_data['Q_rem'] -= q_transferrable
                        
                        available_bw[landing_uav_coords] -= q_transferrable

                        record_of_flows[f].append([t, i, j, q_transferrable])
                        
                        break
                else: 
                    continue 
                break 

for f, records in record_of_flows.items():
    print(f, len(records))
    for rec in records:
        print(f"{rec[0]} {rec[1]} {rec[2]} {rec[3]}")
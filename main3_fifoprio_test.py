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


class FilePriorite:
    def __init__(self):
        self.data = []
        self.indices = {}

    def _parent(self, i): return (i - 1) // 2
    def _gauche(self, i): return 2 * i + 1
    def _droite(self, i): return 2 * i + 2

    def _echanger(self, i, j):
        self.indices[self.data[i][1][0]] = j
        self.indices[self.data[j][1][0]] = i
        self.data[i], self.data[j] = self.data[j], self.data[i]

    def _monter(self, i):
        while i > 0 and self.data[i][0] > self.data[self._parent(i)][0]:
            parent = self._parent(i)
            self._echanger(i, parent)
            i = parent

    def _descendre(self, i):
        n = len(self.data)
        while True:
            plus_grand = i
            g, d = self._gauche(i), self._droite(i)
            if g < n and self.data[g][0] > self.data[plus_grand][0]: plus_grand = g
            if d < n and self.data[d][0] > self.data[plus_grand][0]: plus_grand = d
            if plus_grand == i: break
            self._echanger(i, plus_grand)
            i = plus_grand

    def inserer(self, priorite, f_id, best_cord):
        queue_item = (f_id, best_cord)
        self.data.append((priorite, queue_item))
        self.indices[f_id] = len(self.data) - 1
        self._monter(len(self.data) - 1)

    def extraire_max(self):
        if not self.data: return None
        self._echanger(0, len(self.data) - 1)
        priority, queue_item = self.data.pop()
        del self.indices[queue_item[0]]
        if self.data:
            self._descendre(0)
        return priority, queue_item

    def supprimer(self, f_id):
        if f_id not in self.indices: return False
        i = self.indices[f_id]
        derniere_priorite = self.data[i][0]
        self._echanger(i, len(self.data) - 1)
        self.data.pop()
        del self.indices[f_id]
        if i < len(self.data):
            nouvelle_priorite = self.data[i][0]
            if nouvelle_priorite > derniere_priorite: self._monter(i)
            else: self._descendre(i)
        return True

    def contient(self, f_id):
        return f_id in self.indices

    def est_vide(self):
        return len(self.data) == 0

for t in range(T):
    available_bw = {}
    for (x, y), uav_data in UAVs.items():
        B, phi = uav_data['B'], uav_data['phi']
        effective_time = t + phi
        multiplier = get_bandwidth_multiplier(effective_time)
        available_bw[(x, y)] = B * multiplier

    active_flows = []
    for f, data in flows.items():
        if data['t_start'] <= t and data['Q_rem'] > EPSILON:
            active_flows.append((f, data))

    def get_flow_priority(flow_item):
        f, data = flow_item
        Q_total = data['Q_total']
        if Q_total < EPSILON: Q_total = 1.0

        best_score = float('-inf')
        best_cord = None
        access_x, access_y = data['access_x'], data['access_y']
        m1, n1, m2, n2 = data['m1'], data['n1'], data['m2'], data['n2']

        for i in range(m1, m2 + 1):
            for j in range(n1, n2 + 1):
                candidate_coords = (i, j)
                current_bw = available_bw.get(candidate_coords, 0)
                if current_bw > EPSILON:
                    distance = abs(access_x - i) + abs(access_y - j)
                    distance_score_multiplier = 2 ** (-ALPHA * distance)
                    q_i = min(data['Q_rem'], current_bw)

                    score = 0.3 * q_i * distance_score_multiplier / Q_total
                    score += 0.4 * (q_i / Q_total) + 0.2 * T_max * q_i / ((t + T_max) * Q_total)

                    if (i, j) != data['last_uav']:
                        if data['change_count'] == 0: score += 0.1
                        else: score += 0.1 / (data['change_count'] + 1) - 0.1 / (data['change_count'])

                    score = Q_total * score

                    if score > best_score:
                        best_score = score
                        best_cord = candidate_coords

        if best_cord is None:
            return [float('-inf'), None]

        return [best_score, best_cord]

    file = FilePriorite()
    uav_chosen_by = {}
    flow_current_best_uav = {}

    for f, data in active_flows:
        priorite, best_cord = get_flow_priority((f, data))
        if best_cord is not None:
            file.inserer(priorite, f, best_cord)
            uav_chosen_by.setdefault(best_cord, []).append(f)
            flow_current_best_uav[f] = best_cord

    processed_flows_this_timestep = set()

    while not file.est_vide():
        extracted = file.extraire_max()
        if extracted is None: break

        priorite, queue_item = extracted
        f, current_best_uav_in_queue = queue_item
        flow_data = flows[f]

        if f in processed_flows_this_timestep: continue
        if flow_data['Q_rem'] < EPSILON: continue

        current_priority, current_actual_best_uav = get_flow_priority((f, flow_data))
        current_bw_at_chosen_uav = available_bw.get(current_best_uav_in_queue, 0)

        if current_actual_best_uav != current_best_uav_in_queue or \
           current_priority < priorite or \
           current_bw_at_chosen_uav < EPSILON:

            if current_best_uav_in_queue in uav_chosen_by and f in uav_chosen_by[current_best_uav_in_queue]:
                 uav_chosen_by[current_best_uav_in_queue].remove(f)
                 if not uav_chosen_by[current_best_uav_in_queue]:
                     del uav_chosen_by[current_best_uav_in_queue]

            if current_actual_best_uav is not None:
                file.inserer(current_priority, f, current_actual_best_uav)
                uav_chosen_by.setdefault(current_actual_best_uav, []).append(f)
                flow_current_best_uav[f] = current_actual_best_uav
            else:
                 if f in flow_current_best_uav: del flow_current_best_uav[f]
            continue

        best_uav_coords = current_best_uav_in_queue
        q_transferrable = min(flow_data['Q_rem'], current_bw_at_chosen_uav)

        if q_transferrable > EPSILON:
            if best_uav_coords != flow_data['last_uav']:
                flow_data['change_count'] += 1

            flow_data['Q_rem'] -= q_transferrable
            available_bw[best_uav_coords] -= q_transferrable
            flow_data['last_uav'] = best_uav_coords
            record_of_flows[f].append([t, best_uav_coords[0], best_uav_coords[1], q_transferrable])

            processed_flows_this_timestep.add(f)

            if f in flow_current_best_uav: del flow_current_best_uav[f]
            if best_uav_coords in uav_chosen_by and f in uav_chosen_by[best_uav_coords]:
                 uav_chosen_by[best_uav_coords].remove(f)
                 if not uav_chosen_by[best_uav_coords]:
                     del uav_chosen_by[best_uav_coords]

            affected_flow_ids_copy = list(uav_chosen_by.get(best_uav_coords, []))

            for affected_f_id in affected_flow_ids_copy:
                if affected_f_id in processed_flows_this_timestep: continue
                if not file.contient(affected_f_id): continue

                affected_flow_data = flows[affected_f_id]
                if affected_flow_data['Q_rem'] < EPSILON: continue

                file.supprimer(affected_f_id)

                if affected_f_id in flow_current_best_uav: del flow_current_best_uav[affected_f_id]

                new_priorite, new_best_cord = get_flow_priority((affected_f_id, affected_flow_data))
                if new_best_cord is not None:
                    file.inserer(new_priorite, affected_f_id, new_best_cord)
                    uav_chosen_by.setdefault(new_best_cord, []).append(affected_f_id)
                    flow_current_best_uav[affected_f_id] = new_best_cord

all_flow_ids = list(flows.keys())
all_flow_ids.sort()
for f in all_flow_ids:
    records = record_of_flows.get(f, [])
    print(f, len(records))
    for rec in records:
        print(f"{rec[0]} {rec[1]} {rec[2]} {rec[3]}")
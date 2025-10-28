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

UAV_flow = {}
for uav_coords in UAVs.keys():
    UAV_flow[uav_coords] = []

for f, flow_data in flows.items():
    m1, n1, m2, n2 = flow_data['m1'], flow_data['n1'], flow_data['m2'], flow_data['n2']
    for i in range(m1, m2 + 1):
        for j in range(n1, n2 + 1):
            uav_coords = (i, j)
            if uav_coords in UAV_flow:
                UAV_flow[uav_coords].append(f)

precomputed_distance = {}
for f, data in flows.items():
    access_x, access_y = data['access_x'], data['access_y']
    precomputed_distance[f] = {}
    for i in range(data['m1'], data['m2'] + 1):
        for j in range(data['n1'], data['n2'] + 1):
            dist = abs(access_x - i) + abs(access_y - j)
            precomputed_distance[f][(i, j)] = 2 ** (-ALPHA * dist)


class FilePriorite:
    def __init__(self):
        self.data = []
        self.indices = {}
        self.UAV_besties = {}

    def _parent(self, i): return (i - 1) // 2
    def _gauche(self, i): return 2 * i + 1
    def _droite(self, i): return 2 * i + 2

    def _echanger(self, i, j):
        val_i_id = self.data[i][1][0]
        val_j_id = self.data[j][1][0]
        self.indices[val_i_id] = j
        self.indices[val_j_id] = i
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
            if g < n and self.data[g][0] > self.data[plus_grand][0]:
                plus_grand = g
            if d < n and self.data[d][0] > self.data[plus_grand][0]:
                plus_grand = d
            if plus_grand == i:
                break
            self._echanger(i, plus_grand)
            i = plus_grand

    def inserer(self, priorite, valeur):
        self.data.append((priorite, valeur))
        self.indices[valeur[0]] = len(self.data) - 1
        uav_id = valeur[2]
        if uav_id not in self.UAV_besties:
            self.UAV_besties[uav_id] = set()
        self.UAV_besties[uav_id].add(valeur[0])
        self._monter(len(self.data) - 1)

    def extraire_max(self):
        if not self.data:
            return None
        self._echanger(0, len(self.data) - 1)
        item = self.data.pop()
        del self.indices[item[1][0]]
        uav_id = item[1][2]
        if uav_id in self.UAV_besties:
            self.UAV_besties[uav_id].discard(item[1][0])
            if not self.UAV_besties[uav_id]:
                del self.UAV_besties[uav_id]
        if self.data:
            self._descendre(0)
        return item

    def maj_priorite(self, valeur, nouvelle_priorite):
        if valeur[0] not in self.indices:
            return False
        i = self.indices[valeur[0]]
        ancienne_priorite = self.data[i][0]
        self.data[i] = (nouvelle_priorite, valeur)
        if nouvelle_priorite > ancienne_priorite:
            self._monter(i)
        elif nouvelle_priorite < ancienne_priorite:
            self._descendre(i)
        return True


for t in range(T):
    available_bw = {}
    for (x, y), uav_data in UAVs.items():
        B = uav_data['B']
        phi = uav_data['phi']
        multiplier = get_bandwidth_multiplier(t + phi)
        available_bw[(x, y)] = B * multiplier

    active_flows = []
    for f, data in flows.items():
        if data['t_start'] <= t and data['Q_rem'] > EPSILON:
            active_flows.append((f, data))

    def get_flow_priority(flow_item):
        f, data = flow_item
        Q_total = data['Q_total']
        best_score = float('-inf')
        best_cord = None
        distances = precomputed_distance[f]
        for (i, j), dist_mult in distances.items():
            if (i, j) in available_bw and available_bw[(i, j)] > EPSILON:
                q_i = min(data['Q_rem'], available_bw[(i, j)])
                score = 0.3 * q_i * dist_mult / Q_total
                score += 0.4 * (q_i / Q_total) + 0.2 * T_max * q_i / ((t + T_max) * Q_total)
                if (i, j) != data['last_uav']:
                    if data['change_count'] == 0:
                        score += 0.1
                    else:
                        score += 0.1 / (data['change_count'] + 1) - 0.1 / (data['change_count'])
                score = Q_total * score
                if score > best_score:
                    best_score = score
                    best_cord = (i, j)
        return [best_score, best_cord]

    file = FilePriorite()
    for f, data in active_flows:
        L = get_flow_priority((f, data))
        valeur = (f, data, L[1])
        file.inserer(L[0], valeur)

    initial_heap_size = len(file.data)
    for _ in range(initial_heap_size):
        item = file.extraire_max()
        if item is None:
            break
        priorite, (f, flow_data, best_uav_coords) = item
        if best_uav_coords is None:
            continue
        q_transferrable = min(flow_data['Q_rem'], available_bw[best_uav_coords])
        if q_transferrable > EPSILON:
            if best_uav_coords != flow_data['last_uav']:
                flow_data['change_count'] += 1
            flow_data['Q_rem'] -= q_transferrable
            available_bw[best_uav_coords] -= q_transferrable
            flow_data['last_uav'] = best_uav_coords
            uav_x, uav_y = best_uav_coords
            record_of_flows[f].append([t, uav_x, uav_y, q_transferrable])
        if best_uav_coords in file.UAV_besties:
            for f2 in file.UAV_besties[best_uav_coords].copy():
                A = get_flow_priority((f2, flows[f2]))
                nouvelle_valeur = (f2, flows[f2], A[1])
                file.maj_priorite(nouvelle_valeur, A[0])

for f, records in record_of_flows.items():
    print(f, len(records))
    for rec in records:
        print(f"{rec[0]} {rec[1]} {rec[2]} {rec[3]}")

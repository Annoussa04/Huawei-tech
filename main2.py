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

# Création du dictionnaire UAV_flow de manière optimisée
UAV_flow = {}
for uav_coords in UAVs.keys():
    UAV_flow[uav_coords] = []

# Remplissage du dictionnaire UAV_flow
for f, flow_data in flows.items():
    m1, n1, m2, n2 = flow_data['m1'], flow_data['n1'], flow_data['m2'], flow_data['n2']
    
    # Trouver tous les UAVs dans la zone de transfert de ce flow
    for i in range(m1, m2 + 1):
        for j in range(n1, n2 + 1):
            uav_coords = (i, j)
            if uav_coords in UAV_flow:
                UAV_flow[uav_coords].append(f)

class FilePriorite:
    def __init__(self):
        self.data = []  # Liste de tuples (priorité, valeur)
        self.indices = {}  # Dictionnaire valeur -> index O(1)
    
    def _parent(self, i): return (i - 1) // 2
    def _gauche(self, i): return 2 * i + 1
    def _droite(self, i): return 2 * i + 2
    
    def _echanger(self, i, j):
        # Échange les éléments et met à jour les indices
        self.data[i], self.data[j] = self.data[j], self.data[i]
        self.indices[self.data[i][1]] = i
        self.indices[self.data[j][1]] = j
    
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
        """Insère un élément en O(log n)"""
        self.data.append((priorite, valeur))
        index = len(self.data) - 1
        self.indices[valeur] = index
        self._monter(index)
    
    def extraire_max(self):
        """Extrait le maximum en O(log n)"""
        if not self.data:
            return None
        
        max_item = self.data[0]
        dernier_item = self.data.pop()
        
        if self.data:
            self.data[0] = dernier_item
            self.indices[dernier_item[1]] = 0
            del self.indices[max_item[1]]
            self._descendre(0)
        else:
            del self.indices[max_item[1]]
        
        return max_item
    
    def maj_priorite(self, valeur, nouvelle_priorite):
        """Met à jour la priorité en O(log n)"""
        if valeur not in self.indices:
            return False
        
        i = self.indices[valeur]
        ancienne_priorite = self.data[i][0]
        
        if ancienne_priorite == nouvelle_priorite:
            return True
        
        self.data[i] = (nouvelle_priorite, valeur)
        
        if nouvelle_priorite > ancienne_priorite:
            self._monter(i)
        else:
            self._descendre(i)
        
        return True
    
    def supprimer(self, valeur):
        """Supprime un élément en O(log n)"""
        if valeur not in self.indices:
            return False
        
        i = self.indices[valeur]
        derniere_priorite = self.data[i][0]
        
        # Remplacer par le dernier élément
        dernier_element = self.data.pop()
        
        if i < len(self.data):
            self.data[i] = dernier_element
            self.indices[dernier_element[1]] = i
            del self.indices[valeur]
            
            # Ajuster la position
            if dernier_element[0] > derniere_priorite:
                self._monter(i)
            else:
                self._descendre(i)
        else:
            del self.indices[valeur]
        
        return True
    
    def contient(self, valeur):
        """Vérifie l'existence en O(1)"""
        return valeur in self.indices
    
    def get_priorite(self, valeur):
        """Obtient la priorité en O(1)"""
        return self.data[self.indices[valeur]][0] if valeur in self.indices else None
    
    def est_vide(self):
        return len(self.data) == 0
    
    def taille(self):
        return len(self.data)
    
    def trier(self):
        """Méthode de secours - à éviter pour de grandes tailles"""
        self.data.sort(reverse=True)
        # Reconstruire les indices
        self.indices = {valeur: i for i, (_, valeur) in enumerate(self.data)}

for t in range(T):
    available_bw = {}
    for (x, y), uav_data in UAVs.items():
        B = uav_data['B']
        phi = uav_data['phi']
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
        best_score = float('-inf')
        best_cord = None
        access_x, access_y = data['access_x'], data['access_y']
        m1, n1, m2, n2 = data['m1'], data['n1'], data['m2'], data['n2']
        
        for i in range(m1, m2 + 1):
            for j in range(n1, n2 + 1):
                candidate_coords = (i, j)
                if candidate_coords in available_bw and available_bw[candidate_coords] > EPSILON:
                    distance = abs(access_x - i) + abs(access_y - j)
                    distance_score_multiplier = 2 ** (-ALPHA * distance)
                    q_i = min(data['Q_rem'], available_bw[candidate_coords])
                    score = 0.3 * q_i * distance_score_multiplier / Q_total
                    score += 0.4 * (q_i / Q_total) + 0.2 * T_max * q_i / ((t + T_max) * Q_total)
                    if (i, j) != data['last_uav']:
                        if data['change_count'] == 0:
                            score += 0.1
                        else:
                            score += 0.1 / (data['change_count'] + 1) - 0.1 / (data['change_count'])
                    score = Q_total * score
                    if score > best_score:
                        best_score = score
                        best_cord = candidate_coords
        return [best_score, best_cord]

    file = FilePriorite()
    flow_to_value = {}
    
    # Initialisation optimisée
    for f, data in active_flows:
        L = get_flow_priority((f, data))
        valeur = (f, data, L[1])
        file.inserer(L[0], valeur)
        flow_to_value[f] = valeur

    # Traitement par ordre de priorité
    processed_flows = set()
    
    while not file.est_vide():
        priorite, (f, flow_data, best_uav_coords) = file.extraire_max()
        
        # Éviter les doublons
        if f in processed_flows:
            continue
        processed_flows.add(f)
        
        if best_uav_coords is not None and flow_data['Q_rem'] > EPSILON:
            q_transferrable = min(flow_data['Q_rem'], available_bw[best_uav_coords])
            if q_transferrable > EPSILON:
                if best_uav_coords != flow_data['last_uav']:
                    flow_data['change_count'] += 1
                flow_data['Q_rem'] -= q_transferrable
                available_bw[best_uav_coords] -= q_transferrable
                flow_data['last_uav'] = best_uav_coords
                uav_x, uav_y = best_uav_coords
                record_of_flows[f].append([t, uav_x, uav_y, q_transferrable])
                
                # Mise à jour optimisée des flows affectés
                for affected_flow_id in UAV_flow[best_uav_coords]:
                    if (affected_flow_id in flows and 
                        flows[affected_flow_id]['Q_rem'] > EPSILON and
                        affected_flow_id not in processed_flows):
                        
                        affected_flow_data = flows[affected_flow_id]
                        nouvelle_priorite = get_flow_priority((affected_flow_id, affected_flow_data))[0]
                        nouvelle_valeur = (affected_flow_id, affected_flow_data, get_flow_priority((affected_flow_id, affected_flow_data))[1])
                        
                        if file.contient(flow_to_value.get(affected_flow_id)):
                            file.maj_priorite(flow_to_value[affected_flow_id], nouvelle_priorite)
                        else:
                            file.inserer(nouvelle_priorite, nouvelle_valeur)
                        flow_to_value[affected_flow_id] = nouvelle_valeur
        
        # Réinsérer seulement si nécessaire
        if flow_data['Q_rem'] > EPSILON:
            nouvelle_priorite = get_flow_priority((f, flow_data))[0]
            nouvelle_valeur = (f, flow_data, get_flow_priority((f, flow_data))[1])
            file.inserer(nouvelle_priorite, nouvelle_valeur)
            flow_to_value[f] = nouvelle_valeur
            processed_flows.remove(f)  # Permettre un nouveau traitement

for f, records in record_of_flows.items():
    print(f, len(records))
    for rec in records:
        print(f"{rec[0]} {rec[1]} {rec[2]} {rec[3]}")

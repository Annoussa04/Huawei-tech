import numpy as np

def b(t):
  if t%10 in [0,1,8,9]:
    return 0
  elif t%10 in [2,7]:
    return 0.5
  else:
    return 1

def perform_flow_f (f, t, q, x_arr, y_arr):
  #[x, y, t_start, Q_total, m1, n1, m2, n2] = flows[f] 
  flows[f][3] -= q
  record_of_flows[f].append([t,x_arr,y_arr,q])

record_of_flows = {}


M,N,FN,T = map(int, input().split())
UAV = {}
for _ in range(M*N):
  x,y,B,phi = map(int, input().split())
  UAV[(x,y)] = (B,phi)
flows = {}
for _ in range(FN):
  f, x, y, t_start, Q_total, m1, n1, m2, n2 = map(int, input().split()) 
  record_of_flows[f] = []
  # record_of_flows[f] -> list of many [t, x, y, q], updated each time f is used
  flows[f] = [x, y, t_start, Q_total, m1, n1, m2, n2]

for t in range(T):
  checked = np.zeros((M, N))
  for f in flows:
    if flows[f][2] <= t and flows[f][3] > 0 and b(t + UAV[(flows[f][0] , flows[f][1])][1])> 0 :
      q_transferrable = min(flows[f][3], b(t + UAV[(flows[f][0] , flows[f][1])][1]) * UAV[(flows[f][0] , flows[f][1])][0])
      found = False
      m1, n1, m2, n2 = flows[f][4], flows[f][5], flows[f][6], flows[f][7]
      for i in range(m1, m2+1):
        for j in range(n1, n2+1):
          if checked[i,j] == 0 and not found:
            checked[i,j] = 1
            perform_flow_f(f, t, q_transferrable, i, j)
            found = True

for f in flows:
  print(f , len(record_of_flows[f]))
  for i in range(len(record_of_flows[f])):
    print(record_of_flows[f][i][0], record_of_flows[f][i][1], record_of_flows[f][i][2], record_of_flows[f][i][3])



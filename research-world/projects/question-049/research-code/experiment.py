import numpy as np
from scipy.integrate import solve_ivp

def deriv(t, state):
    x, y, vx, vy = state
    r = np.sqrt(x**2 + y**2)
    ax = -x / r**3
    ay = -y / r**3
    return [vx, vy, ax, ay]

np.random.seed(42)
r0 = 1.0
v0 = np.sqrt(1.0 / r0)
y0 = [r0, 0.0, 0.0, v0]

t_span = (0.0, 100.0)
t_eval = np.linspace(0.0, 100.0, 1000)

sol = solve_ivp(deriv, t_span, y0, method='RK45', t_eval=t_eval, rtol=1e-9, atol=1e-12)

energies = 0.5*(sol.y[2]**2 + sol.y[3]**2) - 1.0/np.sqrt(sol.y[0]**2 + sol.y[1]**2)
E0 = energies[0]
max_dev = float(np.max(np.abs(energies - E0)))
print(f'MAX_ENERGY_DEVIATION={max_dev:.2e}')
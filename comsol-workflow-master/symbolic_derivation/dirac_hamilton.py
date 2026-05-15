import sympy as sp

# -----------------------------------------------------------------------------
# Symbols
t0, t1, t2, t3, a = sp.symbols("t0:4,a", real=True)
kx, ky = sp.symbols("kx,ky", real=True)
I = sp.I
pi = sp.pi
sqrt = sp.sqrt

# -----------------------------------------------------------------------------
# Lattice vectors
a1 = sp.Matrix([a, 0])
a2 = sp.Matrix([a/2, sqrt(3)*a/2])
a3 = a2 - a1  # (-a/2, sqrt(3)*a/2)

def kdot(vec):
    return kx*vec[0] + ky*vec[1]

# -----------------------------------------------------------------------------
# Fourier real basis from the doc (N=6, 0-start indexing)
N = 6
n = sp.Symbol("n", integer=True)
thetas = [2*pi*nn/N for nn in range(N)]

# v0 (DC)
v0 = (1/sqrt(N)) * sp.Matrix([1]*N)

# cosine/sine paired vectors
def cvec(k):
    return sqrt(2) / sqrt(N) * sp.Matrix([sp.cos(k*th) for th in thetas])

def svec(k):
    return sqrt(2) / sqrt(N) * sp.Matrix([sp.sin(k*th) for th in thetas])

c1, s1 = cvec(1), svec(1)
c2, s2 = cvec(2), svec(2)

# Nyquist (only for even N): entry n is (-1)^n
v3 = (1/sqrt(N)) * sp.Matrix([(-1)**nn for nn in range(N)])

# Recommended ordering in the doc: (v0, c1, s1, c2, s2, v3)
U = sp.Matrix.hstack(v0, c1, s1, c2, s2, v3)

# -----------------------------------------------------------------------------
# 6x6 Hamiltonian in site basis
# H0: intra-cell ring (t0)
# H0mat = sp.Matrix([
#     [0,1,0,0,0,1],
#     [1,0,1,0,0,0],
#     [0,1,0,1,0,0],
#     [0,0,1,0,1,0],
#     [0,0,0,1,0,1],
#     [1,0,0,0,1,0],
# ])

# # H1(k): inter-cell couplings (t1) with Bloch phases
# H1mat = sp.Matrix([
#     [0,0,0,sp.exp(I*kdot(a1)),0,0],
#     [0,0,0,0,sp.exp(I*kdot(a2)),0],
#     [0,0,0,0,0,sp.exp(I*kdot(a3))],
#     [sp.exp(-I*kdot(a1)),0,0,0,0,0],
#     [0,sp.exp(-I*kdot(a2)),0,0,0,0],
#     [0,0,sp.exp(-I*kdot(a3)),0,0,0],
# ])

# # On-site modulation
# Vsite = sp.diag(*s2)

# # Total Bloch Hamiltonian with on-site term
# H = t0*H0mat + t1*H1mat + t2*Vsite

# import pdb;pdb.set_trace()
# H_Gamma = H.subs({kx: 0, ky: 0})
# H_Gamma.eigenvals()
# # eigenvects() returns a list of tuples: (eigenvalue, multiplicity, [eigenvectors])
# H_Gamma.subs(t1,t0).eigenvects()
# eigenvects_trunc_t2(H_Gamma.subs(t1,t0).eigenvects())

# -----------------------------------------------------------------------------
m = c2

def avg_m(i, j):
    return (m[i] * m[j]) / 2

bonds_intra = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0)]
bounds_inter = [((0,3), sp.exp(I*kdot(a1))), ((1,4), sp.exp(I*kdot(a2))), ((2,5), sp.exp(I*kdot(a3)))]

H_intra = sp.zeros(6)
for i, j in bonds_intra:
    t_ij = t0 + t2*avg_m(i, j)
    H_intra[i, j] = t_ij
    H_intra[j, i] = t_ij

H_inter = sp.zeros(6)
for (i, j), phase in bounds_inter:
    t_ij = t1 + t3*avg_m(i, j)
    H_inter[i, j] = t_ij * phase
    H_inter[j, i] = t_ij * sp.conjugate(phase)

H = H_intra + H_inter

H_Gamma = H.subs({kx: 0, ky: 0})
ev = H_Gamma.subs({t1: t0, t3: t2}).eigenvects()

Uinv_times = []
for lam, mult, vecs in ev:
    for v in vecs:
        c = U.H * v
        Uinv_times.append((lam, c))
import pdb;pdb.set_trace()
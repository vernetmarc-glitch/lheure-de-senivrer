"""TEST 2b -- A(lambda, a) applique PAR BANDE DE k, non par layer.

Defaut corrige : avec A indexe par layer, une particule partagee entre deux
layers recoit deux deplacements differents (mesure : 4,59 Mpc = 18 px entre
F et G a a=0.8). La position devient ambigue -> rupture au fondu, exactement
le §11.1.

Avec A par bande :
    Psi(a) = somme_k  A(lambda_k, a) . Psi_k        lambda_k = 2 pi / k

la position d'une particule est une fonction UNIQUE de a, identique quel que
soit le layer qui la rend. Le layer ne decide plus que des bandes qu'il resout.

La table a_form(s) du §11.4.a est conservee telle quelle -- elle est deja
indexee par ECHELLE, ce qui est sa lecture physique la plus fidele.
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M

# Points de controle du §11.4.a, interpoles en log10(s) (cf. matrice §3)
A_FORM_NODES = np.array([
    [0.03, 0.20], [2.4, 0.20], [8.49, 0.55], [30.0, 0.65], [67.08, 0.70],
    [150.0, 0.92], [2100.0, 0.95], [5531.46, 1.0], [14570.0, 1.0],
])


def a_form_of_scale(s_mpc):
    ls = np.log10(np.clip(s_mpc, 1e-4, None))
    return np.interp(ls, np.log10(A_FORM_NODES[:, 0]), A_FORM_NODES[:, 1])


def A_of(a, s_mpc):
    """Courbe du §11.4.b avec le correctif de continuite du 13 juillet."""
    af = a_form_of_scale(s_mpc)
    w = np.maximum(-np.log10(af), 0.05)
    centre = np.minimum(np.log10(af), -w)
    x = np.log10(a) - centre
    t = np.clip((x + w) / (2 * w), 0, 1)
    return np.where(a >= 1.0, 1.0, t * t * (3 - 2 * t))


def band_edges(lam_min, lam_max, n_bands):
    return np.logspace(np.log10(lam_min), np.log10(lam_max), n_bands + 1)


def psi_bands_at(delta, box, n, pts, edges, amp):
    """Psi projete sur chaque bande de k, echantillonne aux positions pts.

    Retourne (n_bandes, n_points, 3) et la longueur d'onde centrale de chaque
    bande. Le cout FFT est paye UNE FOIS ; chaque epoque se recombine ensuite
    au niveau des particules (somme ponderee), donc les frames temporelles
    sont bon marche.
    """
    KX, KY, KZ, kmag = M.k_grid3(n, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    c = ((pts + box / 2.0) / box * n).T
    nb = len(edges) - 1
    out = np.zeros((nb, len(pts), 3), np.float32)
    for b in range(nb):
        k_hi = 2 * np.pi / edges[b]        # petite longueur d'onde -> grand k
        k_lo = 2 * np.pi / edges[b + 1]
        sel = (kmag >= k_lo) & (kmag < k_hi)
        for a, K in enumerate((KX, KY, KZ)):
            p = np.fft.irfftn(np.where(sel, 1j * K * dk / k2, 0), s=(n,) * 3).astype(np.float32)
            out[b, :, a] = ndimage.map_coordinates(p, c, order=1, mode="wrap")
            del p
    lam_c = np.sqrt(edges[:-1] * edges[1:])
    rms = np.sqrt(np.mean(np.sum(out.sum(0) ** 2, axis=1)) / 3.0)
    return out * np.float32(amp / max(rms, 1e-9)), lam_c


def displace(q, psi_b, lam_c, a, lam_resolue_min):
    """Position a l'epoque a, pour un layer resolvant lambda >= lam_resolue_min."""
    w = A_of(np.float64(a), lam_c).astype(np.float32)
    w = np.where(lam_c >= lam_resolue_min, w, 0.0)
    return q + np.tensordot(w, psi_b, axes=(0, 0))


# ---- facteur de croissance lineaire GLOBAL (correctif du 28 juillet) -------
def growth_D(a, om=0.315):
    """D(a) LCDM, normalise a D(1)=1. Identique a TOUTES les echelles.

    La hierarchie du §11.4.a (galaxies tot, amas tard) n'est PAS une difference
    de vitesse de croissance : c'est une consequence EMERGENTE de la
    non-linearite. L'imposer par bande fait survivre les petites echelles
    artificiellement, et elles envahissent l'image quand les grandes s'eteignent.
    """
    ol = 1.0 - om
    a = np.atleast_1d(np.asarray(a, dtype=np.float64))
    def integ(x):
        t = np.linspace(1e-8, x, 4000)
        E = np.sqrt(om / t ** 3 + ol)
        return np.trapezoid(1.0 / (t * E) ** 3, t)
    E_a = np.sqrt(om / a ** 3 + ol)
    D = 2.5 * om * E_a * np.array([integ(float(x)) for x in a])
    E1 = np.sqrt(om + ol)
    D1 = 2.5 * om * E1 * integ(1.0)
    return (D / D1)

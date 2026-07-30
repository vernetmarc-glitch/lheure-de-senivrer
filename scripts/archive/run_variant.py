import sys, time, json, numpy as np, mcpm_web as M

N = 192
BOX = 450.0          # layer G (l3, demi-champ 150 Mpc, marge 1.5)
HALF = 150.0

VARIANTS = {
    "A_base":      dict(sense_mpc=4 * BOX / N, attract=2.2, decay=0.12, turn=0.45),
    "B_sense_far": dict(sense_mpc=9 * BOX / N, attract=2.2, decay=0.12, turn=0.45),
    "C_attr_lo":   dict(sense_mpc=6 * BOX / N, attract=0.7, decay=0.12, turn=0.45),
    "D_decay_hi":  dict(sense_mpc=6 * BOX / N, attract=2.2, decay=0.40, turn=0.45),
    "E_turn_lo":   dict(sense_mpc=6 * BOX / N, attract=2.2, decay=0.12, turn=0.15),
    "F_attr_hi":   dict(sense_mpc=6 * BOX / N, attract=6.0, decay=0.25, turn=0.45),
}


def build_field():
    d = M.gen_delta3(N, BOX, 102)
    pos, mass = M.extract_halos(d, BOX, smooth_mpc=2.0, thresh_sigma=0.4,
                                min_sep_mpc=2.0, max_n=600000)
    pos = M.zeldovich_points(pos, d, BOX, s_rms_mpc=4.0)
    np.save("/tmp/Gd.npy", d)
    np.save("/tmp/Gpos.npy", pos)
    np.save("/tmp/Gmass.npy", mass)
    print("halos", len(pos))


if __name__ == "__main__":
    if sys.argv[1] == "field":
        build_field()
    else:
        pos = np.load("/tmp/Gpos.npy")
        mass = np.load("/tmp/Gmass.npy")
        for name in sys.argv[1:]:
            t0 = time.time()
            tr = M.mcpm(pos, mass, BOX, N, n_agents=150000, steps=300,
                        diffuse_every=5, **VARIANTS[name])
            np.save(f"/tmp/tr_{name}.npy", tr.astype(np.float32))
            print(f"{name:12s} {time.time()-t0:5.1f}s  frac>0 {float((tr>0).mean()):.3f} "
                  f"max/moy {float(tr.max()/tr.mean()):.0f}", flush=True)

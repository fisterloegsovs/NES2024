def calculate_dPQ_TX(bH, bC, lL, r, rH):
    return (bH + bC + lL) / (r - rH)

def calculate_dTX_DQ(lf, r):
    return lf / r

def calculate_dDQ_SO(bH, bCj, bj, lj, lL, r, rH):
    return max((bH + bCj + bj - lj + lL) / (r - rH) + lj / r)

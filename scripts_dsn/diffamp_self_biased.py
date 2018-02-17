# -*- coding: utf-8 -*-

import yaml

import scipy.optimize as sciopt

from verification_ec.mos.query import MOSDBDiscrete


def get_db(mos_type, dsn_specs):
    mos_specs = dsn_specs[mos_type]

    spec_file = mos_specs['spec_file']
    interp_method = mos_specs.get('interp_method', 'spline')
    sim_env = mos_specs.get('sim_env', 'tt')
    layout_kwargs = mos_specs['layout_kwargs']

    db = MOSDBDiscrete([char_spec], interp_method=interp_method)
    db.env_list = [sim_env]
    db.set_dsn_params(**layout_kwargs)

    return db

def solve_vs(db, vstar, vg, vd, vb):
    # define zero function.
    vstar_fun = db.get_function('vstar')
    def fun_zero(vs):
        farg = [vb - vs, vd - vs, vg - vs]
        return vstar_fun(farg) - vstar

    # get vs limit.
    vs_max = vs_min = None
    for idx, vup in enumerate([vb, vd, vg]):
        vmin, vmax = vstar_fun.get_input_range(idx)
        if vs_max is None:
            vs_max = vup - vmin
            vs_min = vup - vmax
        else:
            vs_max = min(vs_max, vup - vmin)
            vs_min = max(vs_min, vup - vmax)

    if fun_zero(vs_max) * fun_zero(vs_min) > 0:
        raise ValueError('No solution.')

    return sciopt.brentq(fun_zero, vs_min, vs_max)


def design_amp(dsn_specs):
    vstar_targ = dsn_specs['vstar']
    vincm = dsn_specs['vincm']
    voutcm = dsn_specs['voutcm']
    vdd = dsn_specs['vdd']

    nch_db = get_db('nch', dsn_specs)
    pch_db = get_db('pch', dsn_specs)
    
    # get vntail/vptail
    vntail = solve_vs(nch_db, vstar_targ, vincm, voutcm, 0)
    vptail = solve_vs(pch_db, vstar_targ, vincm, voutcm, vdd)
    
    # get transistor operating points and ratios
    nin_op = nch_db.query(vbs=-vntail, vds=voutcm-vntail, vgs=vincm-vntail)
    pin_op = pch_db.query(vbs=vdd-vptail, vds=voutcm-vptail, vgs=vincm-vptail)
    ntail_op = nch_db.query(vbs=0, vds=vntail, vgs=voutcm)
    ptail_op = pch_db.query(vbs=0, vds=vptail-vdd, vgs=voutcm-vdd)
    ibias_unit = nin_op['ibias']
    scale_pin = ibias_unit / pin_op['ibias']
    scale_ntail = ibias_unit / ntail_op['ibias']
    scale_ptail = ibias_unit / ptail_op['ibias']

    print(vntail, vptail, scale_pin, scale_ntail, scale_ptail)


def run_main():
    spec_file = 'specs_dsn_sample/diffamp_self_biased.yaml'

    with open(spec_file, 'r') as f:
        dsn_specs = yaml.load(f)

    design_amp(dsn_specs)

if __name__ == '__main__':
    run_main()

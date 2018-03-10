# -*- coding: utf-8 -*-


import pprint

import yaml

from bag.io import read_yaml, open_file
from bag.core import BagProject

from verification_ec.mos.query import MOSDBDiscrete
from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStage, OpAmpTwoStageChar


def design(top_specs, nch_db, pch_db):
    dsn_specs = top_specs['dsn_specs']

    print('create design')
    dsn = OpAmpTwoStage(nch_db, pch_db)
    print('run design')
    dsn.design(**dsn_specs)

    dsn_info = dsn.get_dsn_info()
    print('corners: ', nch_db.env_list)
    pprint.pprint(dsn_info, width=120)

    return dsn


def design_only():
    interp_method = 'spline'
    nch_conf_list = ['data/mos_char_nch_stack_w4_vbs/specs.yaml', ]
    pch_conf_list = ['data/mos_char_pch_stack_w4_vbs/specs.yaml', ]
    amp_specs_fname = 'specs_design/opamp_two_stage_1e8.yaml'

    print('create transistor database')
    nch_db = MOSDBDiscrete(nch_conf_list, interp_method=interp_method)
    pch_db = MOSDBDiscrete(pch_conf_list, interp_method=interp_method)

    top_specs = read_yaml(amp_specs_fname)
    design(top_specs, nch_db, pch_db)


def design_close_loop(prj, max_iter=100):
    interp_method = 'spline'
    nch_conf_list = ['data/mos_char_nch_stack_w4_vbs/specs.yaml', ]
    pch_conf_list = ['data/mos_char_pch_stack_w4_vbs/specs.yaml', ]
    amp_specs_fname = 'specs_design/opamp_two_stage_1e8.yaml'
    ver_specs_fname = 'specs_verification/opamp_two_stage_1e8.yaml'
    iter_cnt = 0
    f_unit_min_sim = -1
    k_max = 2.0
    k_min = 1.1

    print('create transistor database')
    nch_db = MOSDBDiscrete(nch_conf_list, interp_method=interp_method)
    pch_db = MOSDBDiscrete(pch_conf_list, interp_method=interp_method)

    top_specs = read_yaml(amp_specs_fname)
    f_unit_dsn_targ = f_unit_targ = top_specs['dsn_specs']['f_unit']

    cfb, corner_list, f_unit_list, pm_list = None, None, None, None
    sim, dsn_info = None, None
    while f_unit_min_sim < f_unit_targ and iter_cnt < max_iter:
        print('Iteration %d, f_unit_dsn_targ = %.4g' % (iter_cnt, f_unit_dsn_targ))
        top_specs['dsn_specs']['f_unit'] = f_unit_dsn_targ
        if dsn_info is not None:
            top_specs['dsn_specs']['i1_min_size'] = dsn_info['i1_size']

        dsn = design(top_specs, nch_db, pch_db)
        dsn_info = dsn.get_dsn_info()
        f_unit_min_dsn = min(dsn_info['f_unit'])

        ver_specs = dsn.get_specs_verification(top_specs)

        with open_file(ver_specs_fname, 'w') as f:
            yaml.dump(ver_specs, f)

        sim = OpAmpTwoStageChar(prj, ver_specs_fname)
        cfb, corner_list, f_unit_list, pm_list = sim.find_cfb(min_scale=0.6, max_scale=1.6)

        f_unit_min_sim = min(f_unit_list)
        k = f_unit_targ / f_unit_min_sim
        k_real = max(k_min, min(k, k_max))
        print('k = %.4g, k_real = %.4g' % (k, k_real))
        f_unit_dsn_targ = f_unit_min_dsn * k_real
        iter_cnt += 1

    print('close loop design done.')
    print('running DC simulation')
    sim.run_simulations(tb_type='tb_dc')
    _, gain_list = sim.process_dc_data()
    print('cfb = %.4g' % cfb)
    print('corners = %s' % corner_list)
    print('funit = %s' % f_unit_list)
    print('phase margin = %s' % pm_list)
    print('gain = %s' % gain_list)

    return dsn_info


def plot_data(prj):
    ver_specs_fname = 'specs_verification/opamp_two_stage_1e8.yaml'
    sim = OpAmpTwoStageChar(prj, ver_specs_fname)

    sim.process_dc_data(plot=True)
    sim.process_ac_data(plot=True)
    import matplotlib.pyplot as plt
    plt.show()


if __name__ == '__main__':
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    # design_close_loop(bprj, max_iter=10)
    design_only()
    # plot_data(bprj)

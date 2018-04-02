# -*- coding: utf-8 -*-


import pprint

import yaml

from bag.io import read_yaml, open_file
from bag.core import BagProject
from bag.simulation.core import DesignManager

from verification_ec.mos.query import MOSDBDiscrete
from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStage


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
    nch_conf_list = ['data/nch_w4_stack/specs.yaml', ]
    pch_conf_list = ['data/pch_w4_stack/specs.yaml', ]
    amp_specs_fname = 'specs_design/opamp_two_stage_1e8.yaml'

    print('create transistor database')
    nch_db = MOSDBDiscrete(nch_conf_list, interp_method=interp_method)
    pch_db = MOSDBDiscrete(pch_conf_list, interp_method=interp_method)

    top_specs = read_yaml(amp_specs_fname)
    design(top_specs, nch_db, pch_db)


def design_close_loop(prj, funity_min_first=None, max_iter=100):
    interp_method = 'spline'
    nch_conf_list = ['data/nch_w4_stack/specs.yaml', ]
    pch_conf_list = ['data/pch_w4_stack/specs.yaml', ]
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
    funity_dsn_targ = funity_targ = top_specs['dsn_specs']['f_unit']

    sim, dsn_info = None, None
    summary = None
    while f_unit_min_sim < funity_targ and iter_cnt < max_iter:
        print('Iteration %d, f_unit_dsn_targ = %.4g' % (iter_cnt, funity_dsn_targ))
        top_specs['dsn_specs']['f_unit'] = funity_dsn_targ
        if dsn_info is not None:
            top_specs['dsn_specs']['i1_min_size'] = dsn_info['i1_size']

        if funity_min_first is not None and iter_cnt == 0:
            generate = False
            f_unit_min_dsn = funity_min_first
        else:
            generate = True
            dsn = design(top_specs, nch_db, pch_db)
            dsn_info = dsn.get_dsn_info()
            f_unit_min_dsn = min(dsn_info['f_unit'])

            ver_specs = dsn.get_specs_verification(top_specs)

            with open_file(ver_specs_fname, 'w') as f:
                yaml.dump(ver_specs, f)

        sim = DesignManager(prj, ver_specs_fname)
        sim.characterize_designs(generate=generate, measure=True, load_from_file=False)
        dsn_name = list(sim.get_dsn_name_iter())[0]
        summary = sim.get_result(dsn_name)['opamp_ac']

        funity_list = summary['funity']

        print('Iteration %d, result:' % iter_cnt)
        pprint.pprint(summary)

        f_unit_min_sim = min(funity_list)
        k = funity_targ / f_unit_min_sim
        k_real = max(k_min, min(k, k_max))
        print('k = %.4g, k_real = %.4g' % (k, k_real))
        funity_dsn_targ = f_unit_min_dsn * k_real
        iter_cnt += 1

    print('close loop design done.  Final result:')
    pprint.pprint(summary)

    return dsn_info


if __name__ == '__main__':
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    design_close_loop(bprj, funity_min_first=None, max_iter=10)
    # design_only()

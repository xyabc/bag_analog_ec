# -*- coding: utf-8 -*-


import pprint

from bag.io import read_yaml

from ckt_dsn_ec.mos.core import MOSDBDiscrete
from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStage


def design_only():
    interp_method = 'spline'
    w_list = [2]
    nch_conf_list = ['data/mos_char_nch_stack_w2_vbs/specs.yaml', ]
    pch_conf_list = ['data/mos_char_pch_stack_w2_vbs/specs.yaml', ]
    amp_specs_fname = 'dsn_specs/opamp_two_stage_1e8.yaml'

    top_specs = read_yaml(amp_specs_fname)
    dsn_specs = top_specs['dsn_specs']

    print('create transistor database')
    nch_db = MOSDBDiscrete(w_list, nch_conf_list, 1, method=interp_method, cfit_method='average')
    pch_db = MOSDBDiscrete(w_list, pch_conf_list, 1, method=interp_method, cfit_method='average')

    print('create design')
    dsn = OpAmpTwoStage(nch_db, pch_db)
    print('run design')
    dsn.design(**dsn_specs)

    dsn_info = dsn.get_dsn_info()
    print('corners: ', nch_db.env_list)
    pprint.pprint(dsn_info, width=120)


if __name__ == '__main__':
    design_only()

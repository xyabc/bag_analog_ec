# -*- coding: utf-8 -*-

from bag.core import BagProject

from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStageChar


def run_main(prj):
    phase_margin = 45
    res_var = 0.2
    spec_file = 'specs_layout/opamp_two_stage_1e8.yaml'

    sim = OpAmpTwoStageChar(prj, spec_file)

    cfb, corner_list, funity_list, pm_list = sim.find_cfb(phase_margin, res_var,  gen_dsn=True)


if __name__ == '__main__':

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    run_main(bprj)

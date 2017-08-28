# -*- coding: utf-8 -*-

from bag.core import BagProject

from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStageChar


def run_main(prj):
    spec_file = 'layout_specs/opamp_two_stage_1e8.yaml'

    sim = OpAmpTwoStageChar(prj, spec_file)

    ans = sim.find_cfb(45, 0.2,  gen_dsn=False)
    cfb = list(ans.values())[0]
    # cfb = 30e-15
    rfb = sim.specs['feedback_params']['rfb']

    sim.verify(rfb, cfb, gen_dsn=False)


if __name__ == '__main__':

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    run_main(bprj)

# -*- coding: utf-8 -*-

import pprint

import yaml

from bag.core import BagProject

from analog_ec.layout.passives.resistor.termination import Termination


def generate_em(prj, specs, gen_sch=False, run_lvs=False, use_cybagoa=False):
    params = specs['params'].copy()
    em_params = specs['em_params']

    tech_info = prj.tech_info

    res_options = params['res_options']
    if res_options is None:
        res_type = 'standard'
    else:
        res_type = res_options.get('res_type', 'standard')

    res_targ = em_params['res_targ']
    num_even = em_params['num_even']
    em_specs = em_params['em_specs']
    num_par, num_ser, w, l = tech_info.design_resistor(res_type, res_targ,
                                                       num_even=num_even, **em_specs)
    params['nser'] = num_ser
    params['npar'] = num_par
    params['l'] = l
    params['w'] = w
    params['em_specs'] = em_specs
    pprint.pprint(params)

    specs['params'] = params

    prj.generate_cell(specs, Termination, gen_sch=gen_sch, run_lvs=run_lvs, use_cybagoa=use_cybagoa)


if __name__ == '__main__':

    with open('specs_test/res/termination.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    # bprj.generate_cell(block_specs, Termination, gen_sch=True, run_lvs=True, use_cybagoa=True)
    generate_em(bprj, block_specs, gen_sch=True, run_lvs=True, use_cybagoa=True)

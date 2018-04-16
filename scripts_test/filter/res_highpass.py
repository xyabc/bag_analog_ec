# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject

from analog_ec.layout.passives.filter.highpass import ResHighPassDiff


if __name__ == '__main__':
    with open('specs_test/filter/res_highpass.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    bprj.generate_cell(block_specs, ResHighPassDiff, gen_sch=False, run_lvs=False, use_cybagoa=True)
    # bprj.generate_cell(block_specs, ResHighPassDiff, gen_sch=True, run_lvs=True, use_cybagoa=True)

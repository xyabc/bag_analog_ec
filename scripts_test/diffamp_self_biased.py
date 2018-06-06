# -*- coding: utf-8 -*-

import yaml

import bag
from analog_ec.layout.amplifiers.diffamp import DiffAmpSelfBiased


if __name__ == '__main__':
    with open('specs_test/analog_ec/diffamp_self_biased.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = bag.BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    bprj.generate_cell(block_specs, DiffAmpSelfBiased, debug=True)
    # bprj.generate_cell(block_specs, DiffAmpSelfBiased, gen_sch=True, debug=True)

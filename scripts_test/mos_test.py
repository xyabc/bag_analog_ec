# -*- coding: utf-8 -*-

import yaml

import bag
from abs_templates_ec.mos_char import Transistor


if __name__ == '__main__':
    with open('specs_test/analog_ec/mos_test.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = bag.BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    # bprj.generate_cell(block_specs, Transistor, debug=True)
    bprj.generate_cell(block_specs, Transistor, gen_sch=True, run_rcx=True, debug=True)

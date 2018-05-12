# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject

from analog_ec.layout.passives.capacitor.momcap import MOMCapChar


if __name__ == '__main__':
    with open('specs_test/analog_ec/cap/momcap.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    bprj.generate_cell(block_specs, MOMCapChar, debug=True)
    # bprj.generate_cell(block_specs, MOMCapChar, gen_sch=True, run_lvs=True, debug=True)

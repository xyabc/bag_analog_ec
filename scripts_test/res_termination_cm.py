# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject
from bag.layout import RoutingGrid, TemplateDB

from analog_ec.layout.passives.resistor.termination import TerminationCMCore


def make_tdb(prj, target_lib, specs):
    grid_specs = specs['routing_grid']
    layers = grid_specs['layers']
    spaces = grid_specs['spaces']
    widths = grid_specs['widths']
    bot_dir = grid_specs['bot_dir']

    routing_grid = RoutingGrid(prj.tech_info, layers, spaces, widths, bot_dir)
    tdb = TemplateDB('template_libs.def', routing_grid, target_lib, use_cybagoa=True)
    return tdb


def generate(prj, specs):
    impl_lib = specs['impl_lib']
    impl_cell = specs['impl_cell']
    params = specs['params']

    temp_db = make_tdb(prj, impl_lib, specs)

    print('creating layouts')
    template = temp_db.new_template(params=params, temp_cls=TerminationCMCore, debug=False)
    temp_db.batch_layout(prj, [template], [impl_cell])
    print('done')


if __name__ == '__main__':

    with open('specs_test/res_termination_cm.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    generate(bprj, block_specs)

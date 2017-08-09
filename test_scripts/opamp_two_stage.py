# -*- coding: utf-8 -*-

from bag.io import read_yaml
from bag.core import BagProject
from bag.layout import RoutingGrid, TemplateDB

from analog_ec.op_amp.core import OpAmpTwoStage


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
    cell_name = specs['cell_name']
    params = specs['params']

    temp_db = make_tdb(prj, impl_lib, specs)

    name_list = [cell_name]
    template = temp_db.new_template(params=params, temp_cls=OpAmpTwoStage, debug=False)
    print('creating layout')
    temp_db.batch_layout(prj, [template], name_list)
    print('layout done')
    return template.sch_params


def generate_sch(prj, specs, sch_params):
    dut_lib = 'bag_analog_ec'
    dut_cell = 'opamp_two_stage'

    impl_lib = specs['impl_lib']
    cell_name = specs['cell_name']

    dsn = prj.create_design_module(dut_lib, dut_cell)
    print('designing schematic')
    dsn.design(**sch_params)
    print('creating schematic')
    dsn.implement_design(impl_lib, top_cell_name=cell_name, erase=True)
    print('schematic done')


def run_lvs_rcx(prj, specs):
    impl_lib = specs['impl_lib']
    cell_name = specs['cell_name']

    print('run lvs')
    lvs_passed, lvs_log = prj.run_lvs(impl_lib, cell_name)
    if not lvs_passed:
        raise ValueError('LVS died.  check log: %s' % lvs_log)
    print('lvs passed')
    print('run rcx')
    rcx_passed, rcx_log = prj.run_rcx(impl_lib, cell_name)
    if not rcx_passed:
        raise ValueError('RCX died.  check log: %s' % rcx_log)
    print('rcx passed')

if __name__ == '__main__':

    block_specs = read_yaml('layout_specs/opamp_two_stage.yaml')

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    sch_info = generate(bprj, block_specs)
    generate_sch(bprj, block_specs, sch_info)
    run_lvs_rcx(bprj, block_specs)

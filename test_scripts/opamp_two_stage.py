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


def generate_tb_dc(prj, specs):
    impl_lib = specs['impl_lib']
    cell_name = specs['cell_name']
    tb_specs = specs['tb_dc']

    tb_lib = tb_specs['lib_name']
    tb_cell = tb_specs['cell_name']
    wrapper_cell = tb_specs['wrapper_name']
    gain_cmfb = tb_specs['gain_cmfb']
    cload = tb_specs['cload']
    vdd = tb_specs['vdd']
    voutcm = tb_specs['voutcm']
    ibias = tb_specs['ibias']

    sim_envs = tb_specs['sim_envs']
    view_name = tb_specs['view_name']
    vmax = tb_specs['vmax']
    num_pts = tb_specs['num_pts']
    vindc = tb_specs['vindc']

    wrapper_sch = prj.create_design_module(tb_lib, wrapper_cell)
    print('designing wrapper schematic')
    wrapper_sch.design(dut_lib=impl_lib, dut_cell=cell_name, gain_cmfb='gain_cmfb', cload='cload',
                       vdd='vdd', voutcm='voutcm', ibias='ibias')
    print('creating wrapper schematic')
    wrapper_sch.implement_design(impl_lib, top_cell_name=wrapper_cell, erase=True)

    tb_sch = prj.create_design_module(tb_lib, tb_cell)
    print('designing tb schematic')
    tb_sch.design(dut_lib=impl_lib, dut_cell=wrapper_cell)
    print('creating tb schematic')
    tb_sch.implement_design(impl_lib, top_cell_name=tb_cell, erase=True)

    tb = prj.configure_testbench(impl_lib, tb_cell)
    tb.set_simulation_environments(sim_envs)
    tb.set_simulation_view(impl_lib, cell_name, view_name)

    tb.set_parameter('vdd', vdd)
    tb.set_parameter('gain_fb', gain_cmfb)
    tb.set_parameter('gain_cmfb', gain_cmfb)
    tb.set_parameter('cload', cload)
    tb.set_parameter('voutcm', voutcm)
    tb.set_parameter('ibias', ibias)
    tb.set_parameter('vindc', vindc)
    tb.set_parameter('vmax', vmax)
    tb.set_parameter('num_pts', num_pts)
    tb.update_testbench()

    print('generate tb_dc done')

if __name__ == '__main__':

    block_specs = read_yaml('layout_specs/opamp_two_stage.yaml')

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    # sch_info = generate(bprj, block_specs)
    # generate_sch(bprj, block_specs, sch_info)
    # run_lvs_rcx(bprj, block_specs)
    generate_tb_dc(bprj, block_specs)
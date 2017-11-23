# -*- coding: utf-8 -*-

from bag.core import BagProject


def run_main(prj):
    impl_lib = 'AAAFOO_CAP'
    impl_cell = 'cap_mom'

    dsn = prj.create_design_module('bag_analog_ec', 'cap_mom')
    dsn.design(w=0.3e-6, l=4.1e-6, layer=6)
    dsn.implement_design(impl_lib, impl_cell)


if __name__ == '__main__':

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    run_main(bprj)

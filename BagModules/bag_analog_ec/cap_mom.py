# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'cap_mom.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__cap_mom(Module):
    """Module for library bag_analog_ec cell cap_mom.

    A MOM cap schematic.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            res_in_info='input metal resistor information.',
            res_out_info='output metal resistor information.',
            sub_name='substrate name.  Empty string to disable.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, res_in_info, res_out_info, sub_name):
        self.instances['XP'].design(w=res_in_info[1], l=res_in_info[2], layer=res_in_info[0])
        self.instances['XN'].design(w=res_in_info[1], l=res_in_info[2], layer=res_in_info[0])

        if not sub_name:
            # delete substrate pin
            self.delete_instance('XSUPCONN')
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)
            self.reconnect_instance_terminal('XSUPCONN', 'noConn', sub_name)

# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'opamp_tb_dc.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__opamp_tb_dc(Module):
    """Module for library bag_analog_ec cell opamp_tb_dc.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            dut_lib='Device-under-test library name.',
            dut_cell='Device-under-test cell name.',
        )

    def design(self, dut_lib, dut_cell):
        """To be overridden by subclasses to design this module.

        This method should fill in values for all parameters in
        self.parameters.  To design instances of this module, you can
        call their design() method or any other ways you coded.

        To modify schematic structure, call:

        rename_pin()
        delete_instance()
        replace_instance_master()
        reconnect_instance_terminal()
        restore_instance()
        array_instance()
        """
        if not dut_lib or not dut_cell:
            raise ValueError('Invalid dut_lib/dut_cell = (%s, %s)' % (dut_lib, dut_cell))

        self.replace_instance_master('XDUT', dut_lib, dut_cell, static=True)

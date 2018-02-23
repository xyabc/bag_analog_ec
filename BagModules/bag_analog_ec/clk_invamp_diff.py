# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'clk_invamp_diff.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__clk_invamp_diff(Module):
    """Module for library bag_analog_ec cell clk_invamp_diff.

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
            cap_params='AC coupling cap schematic parameters.',
            inv_params='Inverter amplifier parameters.',
            res_params='Feedback resistor parameters.',
        )

    def design(self, cap_params, inv_params, res_params):
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
        self.instances['XCAPP'].design(**cap_params)
        self.instances['XCAPN'].design(**cap_params)
        self.instances['XAMPP'].design(**inv_params)
        self.instances['XAMPN'].design(**inv_params)
        self.instances['XRES'].design(**res_params)
        res_sub_name = res_params.get('sub_name', 'VSS')
        if res_sub_name and res_sub_name != 'VSS':
            self.reconnect_instance_terminal('XRES', res_sub_name, res_sub_name)

# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'clk_invamp_diff_reset.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__clk_invamp_diff_reset(Module):
    """Module for library bag_analog_ec cell clk_invamp_diff_reset.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            amp_params='AC coupling amplifier schematic parameters.',
            nor_params='NOR amplifier parameters.',
            dig_params='digital logic parameters.',
        )

    def design(self, amp_params, nor_params, dig_params):
        self.instances['XAMP'].design(**amp_params)
        self.instances['XNORP'].design(**nor_params)
        self.instances['XNORN'].design(**nor_params)
        self.instances['XDIG'].design(**dig_params)

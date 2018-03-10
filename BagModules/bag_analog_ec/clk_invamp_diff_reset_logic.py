# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__,
                                            os.path.join('netlist_info',
                                                         'clk_invamp_diff_reset_logic.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__clk_invamp_diff_reset_logic(Module):
    """Module for library bag_analog_ec cell clk_invamp_diff_reset_logic.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            flop_info='flop static master library/cell info.',
            inv_info='inverter static master library/cell info.',
        )

    def design(self, flop_info, inv_info):
        for inst_name, clk, in_name, out_name in [('XFFB0', 'clkn', 'rstp0', 'rstn0'),
                                                  ('XFFB1', 'clkn', 'rstn0', 'noconn'),
                                                  ('XFFT0', 'clkp', 'rst', 'rstd'),
                                                  ('XFFT1', 'clkp', 'rstd', 'rstp0'), ]:
            self.replace_instance_master(inst_name, flop_info[0], flop_info[1], static=True)
            self.reconnect_instance_terminal(inst_name, 'VDD', 'VDD')
            self.reconnect_instance_terminal(inst_name, 'VSS', 'VSS')
            self.reconnect_instance_terminal(inst_name, 'CLK', clk)
            self.reconnect_instance_terminal(inst_name, 'I', in_name)
            self.reconnect_instance_terminal(inst_name, 'O', out_name)
        for inst_name, in_name, out_name in [('XINVB0', 'rstn0', 'rstnb'),
                                             ('XINVB1', 'rstnb', 'rstn'),
                                             ('XINVT0', 'rstp0', 'rstpb'),
                                             ('XINVT1', 'rstpb', 'rstp'), ]:
            self.replace_instance_master(inst_name, inv_info[0], inv_info[1], static=True)
            self.reconnect_instance_terminal(inst_name, 'VDD', 'VDD')
            self.reconnect_instance_terminal(inst_name, 'VSS', 'VSS')
            self.reconnect_instance_terminal(inst_name, 'I', in_name)
            self.reconnect_instance_terminal(inst_name, 'O', out_name)

# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'noramp.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__noramp(Module):
    """Module for library bag_analog_ec cell noramp.

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
            lch='Channel length, in meters.',
            w_dict='Transistor width dictionary.',
            th_dict='Transistor threshold dictionary.',
            seg_dict='Transistor number of segments dictionary.',
            dum_info='Dummy information data structure.',
        )

    def design(self, lch, w_dict, th_dict, seg_dict, dum_info):
        # design main transistors
        tran_info_list = [('XP', 'invp', 'p'), ('XN', 'invn', 'n'),
                          ('XPEN', 'enp', 'p'), ('XN', 'enn', 'n'),
                          ]

        for inst_name, inst_type, row_type in tran_info_list:
            w = w_dict[row_type]
            th = th_dict[row_type]
            seg = seg_dict[inst_type]
            stack = 1
            self.instances[inst_name].design(w=w, l=lch, seg=seg, intent=th, stack=stack)

        # design dummies
        self.design_dummy_transistors(dum_info, 'XDUM', 'VDD', 'VSS')
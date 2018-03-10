# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'invamp.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__invamp(Module):
    """Module for library bag_analog_ec cell invamp.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            lch='Channel length, in meters.',
            w_dict='Transistor width dictionary.',
            th_dict='Transistor threshold dictionary.',
            seg_dict='Transistor number of segments dictionary.',
            dum_info='Dummy information data structure.',
        )

    def design(self, lch, w_dict, th_dict, seg_dict, dum_info):
        # design main transistors
        tran_info_list = [('XP', 'p'), ('XN', 'n')]

        for inst_name, inst_type in tran_info_list:
            w = w_dict[inst_type]
            th = th_dict[inst_type]
            seg = seg_dict[inst_type]
            self.instances[inst_name].design(w=w, l=lch, nf=seg, intent=th)

        # design dummies
        self.design_dummy_transistors(dum_info, 'XDUM', 'VDD', 'VSS')

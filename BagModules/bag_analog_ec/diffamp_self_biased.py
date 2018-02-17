# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_self_biased.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__diffamp_self_biased(Module):
    """Module for library bag_analog_ec cell diffamp_self_biased.

    This is a self-biased differential amplifier with single-ended output.
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
        tran_info_list = [('XNTAIL1', 'ntail'), ('XNTAIL2', 'ntail'),
                          ('XNINP', 'nin'), ('XNINN', 'nin'),
                          ('XPINP', 'pin'), ('XPINN', 'pin'),
                          ('XPTAIL1', 'ptail'), ('XPTAIL2', 'ptail'),
                          ]

        for inst_name, inst_type in tran_info_list:
            w = w_dict[inst_type]
            th = th_dict[inst_type]
            seg = seg_dict[inst_type]
            stack = 1
            self.instances[inst_name].design(w=w, l=lch, seg=seg, intent=th, stack=stack)

        # design dummies
        self.design_dummy_transistors(dum_info, 'XDUM', 'VDD', 'VSS')

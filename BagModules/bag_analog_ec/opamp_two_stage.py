# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'opamp_two_stage.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__opamp_two_stage(Module):
    """Module for library bag_analog_ec cell opamp_two_stage.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            lch='Channel length, in meters.',
            w_dict='Dictionary of transistor widths.',
            th_dict='Dictionary of transistor threshold.',
            seg_dict='Dictionary of transistor number of segments.',
            stack_dict='Dictionary of transistor stack count.',
            dum_info='Dummy information data structure.',
        )

    def design(self, lch, w_dict, th_dict, seg_dict, stack_dict, dum_info):
        """Design the differential amplifier with diode/positive-feedback load.
        """
        # design dummies
        w_tail = w_dict['tail']
        w_in = w_dict['in']
        w_load = w_dict['load']
        th_tail = th_dict['tail']
        th_in = th_dict['in']
        th_load = th_dict['load']

        # design main transistors
        seg_tail1 = seg_dict['tail1']
        seg_tail2 = seg_dict['tail2']
        seg_tailcm = seg_dict['tailcm']
        seg_in = seg_dict['in']
        seg_ref = seg_dict['ref']
        seg_diode1 = seg_dict['diode1']
        seg_ngm1 = seg_dict['ngm1']
        seg_diode2 = seg_dict['diode2']
        seg_ngm2 = seg_dict['ngm2']

        stack_tail = stack_dict['tail']
        stack_in = stack_dict['in']
        stack_diode = stack_dict['diode']
        stack_ngm = stack_dict['ngm']

        self.instances['XTAIL'].design(w=w_tail, l=lch, seg=seg_tail1 * 2, intent=th_tail,
                                       stack=stack_tail)
        self.instances['XTAIL2L'].design(w=w_tail, l=lch, seg=seg_tail2, intent=th_tail,
                                         stack=stack_tail)
        self.instances['XTAIL2R'].design(w=w_tail, l=lch, seg=seg_tail2, intent=th_tail,
                                         stack=stack_tail)
        self.instances['XCML'].design(w=w_tail, l=lch, seg=seg_tailcm, intent=th_tail,
                                      stack=stack_tail)
        self.instances['XCMR'].design(w=w_tail, l=lch, seg=seg_tailcm, intent=th_tail,
                                      stack=stack_tail)
        self.instances['XREF'].design(w=w_tail, l=lch, seg=seg_ref, intent=th_tail,
                                      stack=stack_tail)
        self.instances['XINL'].design(w=w_in, l=lch, seg=seg_in, intent=th_in, stack=stack_in)
        self.instances['XINR'].design(w=w_in, l=lch, seg=seg_in, intent=th_in, stack=stack_in)
        self.instances['XRES'].design(w=w_in, l=lch, seg=seg_ref, intent=th_in, stack=stack_in)
        self.instances['XDIOL'].design(w=w_load, l=lch, seg=seg_diode1, intent=th_load,
                                       stack=stack_diode)
        self.instances['XDIOR'].design(w=w_load, l=lch, seg=seg_diode1, intent=th_load,
                                       stack=stack_diode)
        self.instances['XNGML'].design(w=w_load, l=lch, seg=seg_ngm1, intent=th_load,
                                       stack=stack_ngm)
        self.instances['XNGMR'].design(w=w_load, l=lch, seg=seg_ngm1, intent=th_load,
                                       stack=stack_ngm)
        self.instances['XDIO2L'].design(w=w_load, l=lch, seg=seg_diode2, intent=th_load,
                                        stack=stack_diode)
        self.instances['XDIO2R'].design(w=w_load, l=lch, seg=seg_diode2, intent=th_load,
                                        stack=stack_diode)
        self.instances['XNGM2L'].design(w=w_load, l=lch, seg=seg_ngm2, intent=th_load,
                                        stack=stack_ngm)
        self.instances['XNGM2R'].design(w=w_load, l=lch, seg=seg_ngm2, intent=th_load,
                                        stack=stack_ngm)

        # design dummies
        self.design_dummy_transistors(dum_info, 'XDUM', 'VDD', 'VSS')

# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_diode_pfb.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__diffamp_diode_pfb(Module):
    """Module for library bag_analog_ec cell diffamp_diode_pfb.

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
            w_dict='Dictionary of transistor widths.',
            th_dict='Dictionary of transistor threshold.',
            seg_dict='Dictionary of transistor number of segments.',
            stack_dict='Dictionary of transistor stack count.',
            dum_dict='Dictionary of dummies.',
        )

    def design(self, lch, w_dict, th_dict, seg_dict, stack_dict, dum_dict):
        """Design the differential amplifier with diode/positive-feedback load.
        """
        # design dummies
        w_tail = w_dict['tail']
        w_in = w_dict['in']
        w_load = w_dict['load']
        th_tail = th_dict['tail']
        th_in = th_dict['in']
        th_load = th_dict['load']
        ndum_tail = dum_dict['tail']
        ndum_in = dum_dict['in']
        ndum_load = dum_dict['load']
        pdum_list = []
        if ndum_tail > 0:
            pdum_list.append((w_tail, th_tail, ndum_tail))
        if ndum_in > 0:
            pdum_list.append((w_in, th_in, ndum_in))

        # array pmos dummies and design
        self.array_instance('XPD', ['XPDD%s' % idx for idx in range(len(pdum_list))])
        for inst, (w_cur, th_cur, ndum_cur) in zip(self.instances['XPD'], pdum_list):
            inst.design(w=w_cur, l=lch, intent=th_cur, nf=ndum_cur)

        # design rest of the dummies
        for name in ('XPD1', 'XPD2', 'XPD3'):
            self.instances[name].design(w=w_in, l=lch, intent=th_in, nf=2)
        for name in ('XND1', 'XND2'):
            self.instances[name].design(w=w_load, l=lch, intent=th_load, nf=2)
        self.instances['XND'].design(w=w_load, l=lch, intent=th_load, nf=ndum_load)

        # design main transistors
        seg_tail = seg_dict['tail']
        seg_in = seg_dict['in']
        seg_ref = seg_dict['ref']
        seg_diode = seg_dict['diode']
        seg_ngm = seg_dict['ngm']

        stack_tail = stack_dict['tail']
        stack_in = stack_dict['in']
        stack_diode = stack_dict['diode']
        stack_ngm = stack_dict['ngm']

        self.instances['XTAIL'].design(w=w_tail, l=lch, seg=seg_tail * 2, intent=th_tail, stack=stack_tail)
        self.instances['XREF'].design(w=w_tail, l=lch, seg=seg_ref, intent=th_tail, stack=stack_tail)
        self.instances['XINL'].design(w=w_in, l=lch, seg=seg_in, intent=th_in, stack=stack_in)
        self.instances['XINR'].design(w=w_in, l=lch, seg=seg_in, intent=th_in, stack=stack_in)
        self.instances['XRES'].design(w=w_in, l=lch, seg=seg_ref, intent=th_in, stack=stack_in)
        self.instances['XDIOL'].design(w=w_load, l=lch, seg=seg_diode, intent=th_load, stack=stack_diode)
        self.instances['XDIOR'].design(w=w_load, l=lch, seg=seg_diode, intent=th_load, stack=stack_diode)
        self.instances['XNGML'].design(w=w_load, l=lch, seg=seg_ngm, intent=th_load, stack=stack_ngm)
        self.instances['XNGMR'].design(w=w_load, l=lch, seg=seg_ngm, intent=th_load, stack=stack_ngm)

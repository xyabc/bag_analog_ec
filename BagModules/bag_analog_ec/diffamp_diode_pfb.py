# -*- coding: utf-8 -*-
########################################################################################################################
#
# Copyright (c) 2014, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################################################################

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_diode_pfb.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__diffamp_diode_pfb(Module):
    """Module for library bag_analog_ec cell diffamp_diode_pfb.

    Fill in high level description here.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'seg_dict', 'stack_dict', 'dum_dict']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self, lch=90e-9, w_dict=None, th_dict=None, seg_dict=None, stack_dict=None,
               dum_dict=None):
        """Design the differential amplifier with diode/positive-feedback load.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        # desig dummies
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

    def get_layout_params(self, **kwargs):
        """Returns a dictionary with layout parameters.

        This method computes the layout parameters used to generate implementation's
        layout.  Subclasses should override this method if you need to run post-extraction
        layout.

        Parameters
        ----------
        kwargs :
            any extra parameters you need to generate the layout parameters dictionary.
            Usually you specify layout-specific parameters here, like metal layers of
            input/output, customizable wire sizes, and so on.

        Returns
        -------
        params : dict[str, any]
            the layout parameters dictionary.
        """
        return {}

    def get_layout_pin_mapping(self):
        """Returns the layout pin mapping dictionary.

        This method returns a dictionary used to rename the layout pins, in case they are different
        than the schematic pins.

        Returns
        -------
        pin_mapping : dict[str, str]
            a dictionary from layout pin names to schematic pin names.
        """
        return {}

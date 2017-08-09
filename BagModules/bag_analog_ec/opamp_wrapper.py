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


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'opamp_wrapper.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__opamp_wrapper(Module):
    """Module for library bag_analog_ec cell opamp_wrapper.

    Fill in high level description here.
    """

    param_list = ['dut_lib', 'dut_cell', 'gain_cmfb', 'cload', 'vdd', 'voutcm', 'ibias']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self, dut_lib='', dut_cell='', gain_cmfb=200, cload=200e-15, vdd=1.0, voutcm=0.5, ibias=100e-9):
        """Create the OpAmp wrapper for simulation purposes.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        if not dut_lib or not dut_cell:
            raise ValueError('Invalid dut_lib/dut_cell = (%s, %s)' % (dut_lib, dut_cell))

        self.replace_instance_master('XDUT', dut_lib, dut_cell, static=True)
        vcvs = self.instances['ECMFB']
        vcvs.parameters['egain'] = gain_cmfb
        vcvs.parameters['minm'] = '0.0'
        vcvs.parameters['maxm'] = vdd
        self.instances['COUTP'].parameters['c'] = cload
        self.instances['COUTN'].parameters['c'] = cload

        voltage_dict = {'outcm': ('outcm', 'VSS', voutcm)}
        current_dict = {'ibias': ('ibias', 'VSS', ibias)}
        self.instances['XBIAS'].design(voltage_dict=voltage_dict, current_dict=current_dict)
        self.reconnect_instance_terminal('XBIAS', 'outcm', 'outcm')
        self.reconnect_instance_terminal('XBIAS', 'ibias', 'ibias')

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

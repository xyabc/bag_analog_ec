# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag import float_to_si_string
from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'opamp_two_stage_wrapper_dm.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__opamp_two_stage_wrapper_dm(Module):
    """Module for library bag_analog_ec cell opamp_two_stage_wrapper_dm.

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
            dut_lib='Device-under-test library name.',
            dut_cell='Device-under-test cell name.',
            gain_cmfb='Common-mode feedback gain.',
            cload='Load capacitance.',
            cfb='Miller-feedback capacitance.',
            rfb='Miller-feedback resistance.',
            vdd='Supply voltage.',
        )

    def design(self, dut_lib, dut_cell, gain_cmfb, cload, cfb, rfb, vdd):
        """Create the OpAmp wrapper for simulation purposes.
        """
        if not dut_lib or not dut_cell:
            raise ValueError('Invalid dut_lib/dut_cell = (%s, %s)' % (dut_lib, dut_cell))

        self.replace_instance_master('XDUT', dut_lib, dut_cell, static=True)
        vcvs = self.instances['ECMFB']

        if not isinstance(gain_cmfb, str):
            gain_cmfb = float_to_si_string(gain_cmfb)
        if not isinstance(vdd, str):
            vdd = float_to_si_string(vdd)
        if not isinstance(cload, str):
            cload = float_to_si_string(cload)
        if not isinstance(cfb, str):
            cfb = float_to_si_string(cfb)
        if not isinstance(rfb, str):
            rfb = float_to_si_string(rfb)

        vcvs.parameters['egain'] = gain_cmfb
        vcvs.parameters['minm'] = '0.0'
        vcvs.parameters['maxm'] = vdd
        self.instances['COUTP'].parameters['c'] = cload
        self.instances['COUTN'].parameters['c'] = cload
        self.instances['CFBP'].parameters['c'] = cfb
        self.instances['CFBN'].parameters['c'] = cfb
        self.instances['RFBP'].parameters['r'] = rfb
        self.instances['RFBN'].parameters['r'] = rfb

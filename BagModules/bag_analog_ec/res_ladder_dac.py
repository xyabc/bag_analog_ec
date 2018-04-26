# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'res_ladder_dac.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_ladder_dac(Module):
    """Module for library bag_analog_ec cell res_ladder_dac.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            nout='number of outputs.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            nout=1,
        )

    def design(self, nin0, nin1, nout, res_params, mux_params):
        nin = nin0 + nin1
        # rename pins
        sel_suf = '<%d:0>' % (nin - 1)
        code_name = 'code<%d:0>' % (nin * nout - 1)
        self.rename_pin('code', code_name)

        # design resistor ladder
        nout_ladder = 1 << nin
        out_suf = '<%d:1>' % (nout_ladder - 1)
        mid_name = 'vmid' + out_suf
        self.instances['XCORE'].design(nout=nout_ladder, **res_params)
        self.reconnect_instance_terminal('XCORE', 'out' + out_suf, mid_name)

        # design mux
        self.instances['XMUX'].design(nin0=nin0, nin1=nin1, **mux_params)
        in_name = 'in<%d:0>' % nout_ladder
        if nout == 1:
            self.reconnect_instance_terminal('XMUX', in_name, mid_name + ',VSS')
            self.reconnect_instance_terminal('XMUX', 'sel' + sel_suf, code_name)
        else:
            out_name = 'out<%d:0>' % (nout - 1)
            self.rename_pin('out', out_name)
            term_dict = {in_name: mid_name + ',VSS', 'sel' + sel_suf: code_name,
                         'out': out_name}
            self.array_instance('XCORE', ['XCORE<%d:0>' % (nout - 1)], term_list=[term_dict])

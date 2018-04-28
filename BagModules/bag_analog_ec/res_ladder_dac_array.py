# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'res_ladder_dac_array.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_ladder_dac_array(Module):
    """Module for library bag_analog_ec cell res_ladder_dac_array.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            dac_params='DAC parameters.',
            ndac='number of DACs.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            nout=1,
        )

    def design(self, dac_params, ndac):
        nout = dac_params.get('nout', 1)
        nin0 = dac_params['nin0']
        nin1 = dac_params['nin1']
        nin = nin0 + nin1

        # rename pins
        code_name = 'code<%d:0>' % (nin * nout * ndac - 1)
        self.rename_pin('code', code_name)
        if nout * ndac == 1:
            out_name = 'out<0>'
        else:
            out_name = 'out<%d:0>' % (nout * ndac - 1)
        self.rename_pin('out', out_name)

        # design DAC
        nout_ladder = 1 << nin
        out_suf = '<%d:1>' % (nout_ladder - 1)
        mid_name = 'vmid' + out_suf
        self.instances['XDAC'].design(**dac_params)

        # array instance
        if ndac == 1:
            self.reconnect_instance_terminal('XDAC', code_name, code_name)
            if nout == 1:
                self.reconnect_instance_terminal('XDAC', 'out', out_name)
            else:
                self.reconnect_instance_terminal('XDAC', out_name, out_name)
        else:
            name_list = ['XDAC<%d:0>' % (ndac - 1)]
            pin_list = self.instances['XDAC'].master.pin_list
            term_dict = {}
            for name in pin_list:
                if name.startswith('code'):
                    term_dict[name] = code_name
                elif name.startswith('out'):
                    term_dict[name] = out_name
            self.array_instance('XDAC', name_list, term_list=[term_dict])

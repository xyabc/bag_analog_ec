# -*- coding: utf-8 -*-

from typing import Dict

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
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            nout_arr_list='list of number of outputs and mosaic factor.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
        )

    def design(self, nin0, nin1, nout_arr_list, res_params, mux_params):
        nin = nin0 + nin1

        name_list = []
        term_list = []
        in_off = out_off = 0
        code_fmt = 'code<%d:%d>'
        out_fmt = 'out<%d:%d>'
        for idx, (nout, nx) in enumerate(nout_arr_list):
            if nx == 1:
                name_list.append('XDAC%d' % idx)
            else:
                name_list.append('XDAC%d<%d:0>' % (idx, (nx - 1)))

            term_dict = {}
            num_in = nin * nout * nx
            term_dict[code_fmt % (nin * nout - 1, 0)] = code_fmt % (num_in + in_off - 1, in_off)
            num_out = nout * nx
            if nout == 1:
                if nx == 1:
                    term_dict['out'] = 'out<%d>' % out_off
                else:
                    term_dict['out'] = out_fmt % (num_out + out_off - 1, out_off)
            else:
                term_dict[out_fmt % (nout - 1, 0)] = out_fmt % (num_out + out_off - 1, out_off)
            term_list.append(term_dict)

            in_off += num_in
            out_off += num_out

        # rename pins
        code_name = code_fmt % (in_off - 1, 0)
        self.rename_pin('code', code_name)
        if out_off == 1:
            out_name = 'out<0>'
        else:
            out_name = out_fmt % (out_off - 1, 0)
        self.rename_pin('out', out_name)

        # design DAC
        self.array_instance('XDAC', name_list, term_list=term_list)
        for inst, (nout, _) in zip(self.instances['XDAC'], nout_arr_list):
            inst.design(nin0=nin0, nin1=nin1, nout=nout, res_params=res_params,
                        mux_params=mux_params)

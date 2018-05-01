# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources
from itertools import islice

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
            io_name_list='input/output names.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            nout=1,
            io_name_list=None,
        )

    def design(self, nin0, nin1, nout_arr_list, res_params, mux_params, io_name_list):
        nin = nin0 + nin1

        if io_name_list is None:
            name_list, term_list, nout_list = self._get_name_term_code(nin, nout_arr_list)
        else:
            name_list, term_list, nout_list = self._get_name_term(nin, nout_arr_list, io_name_list)

        # design DAC
        self.array_instance('XDAC', name_list, term_list=term_list)
        for inst, nout in zip(self.instances['XDAC'], nout_list):
            inst.design(nin0=nin0, nin1=nin1, nout=nout, res_params=res_params,
                        mux_params=mux_params)

    def _get_name_term(self, nin, nout_arr_list, io_name_list):
        max_in_idx = nin - 1
        io_off = 0
        dac_idx = 0
        name_list = []
        term_list = []
        nout_list = []
        for nout, nx in nout_arr_list:
            in_term = 'code<%d:0>' % (nout * nin - 1)
            out_term = 'out' if nout == 1 else 'out<%d:0>' % (nout - 1)
            for _ in range(nx):
                out_list = []
                in_list = []
                for name_idx in range(io_off + nout - 1, io_off - 1, -1):
                    name = io_name_list[name_idx]
                    out_list.append('v_%s' % name)
                    in_list.append('bias_%s<%d:0>' % (name, max_in_idx))

                out_name = ','.join(out_list)
                in_name = ','.join(in_list)
                name_list.append('XDAC%d' % dac_idx)
                term_list.append({out_term: out_name, in_term: in_name})
                nout_list.append(nout)

                dac_idx += 1
                io_off += nout

        name0 = io_name_list[0]
        self.rename_pin('code', 'bias_%s<%d:0>' % (name0, max_in_idx))
        self.rename_pin('out', 'v_%s' % name0)
        for name in islice(io_name_list, 1, None):
            self.add_pin('bias_%s<%d:0>' % (name, max_in_idx), 'input')
            self.add_pin('v_%s' % name, 'output')

        return name_list, term_list, nout_list

    def _get_name_term_code(self, nin, nout_arr_list):
        name_list = []
        term_list = []
        nout_list = []
        in_off = out_off = 0
        code_fmt = 'code<%d:%d>'
        out_fmt = 'out<%d:%d>'
        for idx, (nout, nx) in enumerate(nout_arr_list):
            nout_list.append(nout)
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

        code_name = code_fmt % (in_off - 1, 0)
        if out_off == 1:
            out_name = 'out<0>'
        else:
            out_name = out_fmt % (out_off - 1, 0)
        self.rename_pin('code', code_name)
        self.rename_pin('out', out_name)

        return name_list, term_list, nout_list

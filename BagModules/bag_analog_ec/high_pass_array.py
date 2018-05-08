# -*- coding: utf-8 -*-

from typing import Dict

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'high_pass_array.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__high_pass_array(Module):
    """Module for library bag_analog_ec cell high_pass_array.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            narr='number of high-pass filters in this array.',
            ndum='number of dummy resistors.',
            hp_params='high-pass filter parameters.',
        )

    def design(self, narr, ndum, hp_params):
        if narr <= 0:
            raise ValueError('narr must be greater than 0.')

        l = hp_params['l']
        w = hp_params['w']
        intent = hp_params['intent']
        sub_name = hp_params['sub_name']

        self.instances['XDUM'].design(l=l, w=w, intent=intent, ndum=ndum, sub_name=sub_name)
        self.instances['XHP'].design(**hp_params)

        if narr > 1:
            suf = '<%d:0>' % (narr - 1)
            term_dict = {}
            for name in ('in', 'out', 'bias'):
                new_name = name + suf
                self.rename_pin(name + '<0>', new_name)
                term_dict[name] = new_name

            self.array_instance('XHP', ['XHP' + suf], term_list=[term_dict])

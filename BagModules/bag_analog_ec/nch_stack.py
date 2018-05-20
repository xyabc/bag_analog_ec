# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'nch_stack.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__nch_stack(Module):
    """Module for library bag_analog_ec cell nch_stack.

    A transistor with optional stack parameter.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            w='Transistor width in meters or number of fins.',
            l='Transistor length in meters.',
            seg='Transistor number of segments.',
            intent='Transistor threshold flavor.',
            stack='Number of stacked transistors in a segment.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            intent='standard',
            stack=1,
        )

    def design(self, w, l, seg, intent, stack):
        inst_name = 'XN'

        # array instances
        name_list = []
        term_list = []
        if stack == 1:
            self.instances[inst_name].design(w=w, l=l, nf=seg, intent=intent)
        else:
            # add stack transistors
            suf = '' if seg == 1 else '<%d:0>' % (seg - 1)
            for idx in range(stack):
                name_list.append('%s%d' % (inst_name, idx) + suf)
                cur_term = {}
                if idx != stack - 1:
                    cur_term['S'] = ('mid%d' % idx) + suf
                if idx != 0:
                    cur_term['D'] = ('mid%d' % (idx - 1)) + suf
                term_list.append(cur_term)

            self.instances[inst_name].design(w=w, l=l, nf=1, intent=intent)
            self.array_instance(inst_name, name_list, term_list=term_list)

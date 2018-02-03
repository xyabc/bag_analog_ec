# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'nch_stack.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__nch_stack(Module):
    """Module for library bag_analog_ec cell nch_stack.

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
        """To be overridden by subclasses to design this module.

        This method should fill in values for all parameters in
        self.parameters.  To design instances of this module, you can
        call their design() method or any other ways you coded.

        To modify schematic structure, call:

        rename_pin()
        delete_instance()
        replace_instance_master()
        reconnect_instance_terminal()
        restore_instance()
        array_instance()
        """
        if seg == 1:
            raise ValueError('Cannot make 1 finger transistor.')

        inst_name = 'XN'

        # array instances
        name_list = []
        term_list = []
        # add stack transistors
        for idx in range(stack):
            name_list.append('%s%d<%d:0>' % (inst_name, idx, seg - 1))
            cur_term = {}
            if idx != stack - 1:
                cur_term['S'] = 'mid%d<%d:0>' % (idx, seg - 1)
            if idx != 0:
                cur_term['D'] = 'mid%d<%d:0>' % (idx - 1, seg - 1)
            term_list.append(cur_term)

        self.instances[inst_name].design(w=w, l=l, nf=1, intent=intent)
        self.array_instance(inst_name, name_list, term_list=term_list)

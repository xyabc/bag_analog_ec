# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'res_feedback_diff.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_feedback_diff(Module):
    """Module for library bag_analog_ec cell res_feedback_diff.

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
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            intent='resistor type.',
            nser='number of resistors in series in a branch.',
            sub_name='substrate name.  Empty string to disable'
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, l, w, intent, nser, sub_name):
        if nser <= 0:
            raise ValueError('Illegal values of ndum, npar, or nser.')

        # handle substrate pin
        if not sub_name:
            # delete substrate pin
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)

        # design main resistors
        for inst_name, parity in (('RP', 'p'), ('RN', 'n')):
            self.instances[inst_name].design(w=w, l=l, intent=intent)
            if nser == 1:
                if sub_name and sub_name != 'VSS':
                    self.reconnect_instance_terminal(inst_name, 'BULK', sub_name)
            else:
                if nser == 2:
                    pos_name = 'in%s,mid%s' % (parity, parity)
                    neg_name = 'mid%s,out%s' % (parity, parity)
                else:
                    pos_name = 'in%s,mid%s<%d:0>' % (parity, parity, nser - 2)
                    neg_name = 'mid%s<%d:0>,out%s' % (parity, nser - 2, parity)

                name_list = ['%s<%d:0>' % (inst_name, nser - 1)]
                term_list = [dict(
                    PLUS=pos_name,
                    MINUS=neg_name,
                )]
                if sub_name and sub_name != 'VSS':
                    term_list[0]['BULK'] = sub_name

                self.array_instance(inst_name, name_list, term_list=term_list)

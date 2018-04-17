# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'high_pass_diff.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__high_pass_diff(Module):
    """Module for library bag_analog_ec cell high_pass_diff.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            intent='resistor type.',
            nser='number of resistors in series in a branch.',
            ndum='number of dummy resistors.',
            res_vm_info='vertical metal resistor information.',
            res_in_info='input metal resistor information.',
            res_out_info='output metal resistor information.',
            sub_name='substrate name.  Empty string to disable.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, l, w, intent, nser, ndum, res_vm_info, res_in_info, res_out_info, sub_name):
        if ndum < 0 or nser <= 0:
            raise ValueError('Illegal values of ndum or nser.')

        # handle substrate pin
        if not sub_name:
            # delete substrate pin
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)

        # design dummy
        if ndum == 0:
            self.delete_instance('RDUMP')
            self.delete_instance('RDUMN')
        else:
            self.instances['RDUMP'].design(w=w, l=l, intent=intent)
            self.instances['RDUMN'].design(w=w, l=l, intent=intent)
            if ndum > 1:
                if sub_name and sub_name != 'VSS':
                    term_list = [dict(BULK=sub_name)]
                else:
                    term_list = None
                self.array_instance('RDUMP', ['RDUMP<%d:0>' % (ndum - 1)], term_list=term_list)
                self.array_instance('RDUMN', ['RDUMN<%d:0>' % (ndum - 1)], term_list=term_list)
            elif sub_name and sub_name != 'VSS':
                self.reconnect_instance_terminal('RDUMP', 'BULK', sub_name)
                self.reconnect_instance_terminal('RDUMN', 'BULK', sub_name)

        # design main resistors
        for inst_name, in_name, out_name, mid_name in (('RP', 'rp', 'biasp', 'midp'),
                                                       ('RN', 'rn', 'biasn', 'midn')):
            self.instances[inst_name].design(w=w, l=l, intent=intent)
            if nser == 1:
                if sub_name and sub_name != 'VSS':
                    self.reconnect_instance_terminal(inst_name, 'BULK', sub_name)
            else:
                if nser == 2:
                    pos_name = '%s,%s' % (in_name, mid_name)
                    neg_name = '%s,%s' % (mid_name, out_name)
                else:
                    pos_name = '%s,%s<%d:0>' % (in_name, mid_name, nser - 2)
                    neg_name = '%s<%d:0>,%s' % (mid_name, nser - 2, out_name)
                if sub_name and sub_name != 'VSS':
                    term_dict = dict(PLUS=pos_name, MINUS=neg_name, BULK=sub_name)
                else:
                    term_dict = dict(PLUS=pos_name, MINUS=neg_name)
                name_list = ['%s<%d:0>' % (inst_name, nser - 1)]
                term_list = [term_dict]

                self.array_instance(inst_name, name_list, term_list=term_list)

        # design metal resistors
        names_list = [('RMIP', 'RMIN'), ('RMOP', 'RMON'), ('RMVP', 'RMVN')]
        info_list = [res_in_info, res_out_info, res_vm_info]
        for res_names, (res_lay, res_w, res_l) in zip(names_list, info_list):
            for name in res_names:
                self.instances[name].design(layer=res_lay, w=res_w, l=res_l)

# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'res_term_diff.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_term_diff(Module):
    """Module for library bag_analog_ec cell res_term_diff.

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
            npar='number of branches in parallel.',
            ndum='number of dummy resistors.',
            sub_name='substrate name.  Empty string to disable'
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, l, w, intent, nser, npar, ndum, sub_name):
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
        if ndum < 0 or npar <= 0 or nser <= 0:
            raise ValueError('Illegal values of ndum, npar, or nser.')

        # handle substrate pin
        if not sub_name:
            # delete substrate pin
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)

        # design dummy
        if ndum == 0:
            self.delete_instance('RDUM')
        else:
            self.instances['RDUM'].design(w=w, l=l, intent=intent)
            if ndum > 1:
                if sub_name and sub_name != 'VSS':
                    term_list = [dict(BULK=sub_name)]
                else:
                    term_list = None
                self.array_instance('RDUM', ['RDUM<%d:0>' % (ndum - 1)], term_list=term_list)
            elif sub_name and sub_name != 'VSS':
                self.reconnect_instance_terminal('RDUM', 'BULK', sub_name)

        # design main resistors
        for inst_name, in_name, mid_name in (('RP', 'inp', 'midp'), ('RN', 'inn', 'midn')):
            self.instances[inst_name].design(w=w, l=l, intent=intent)
            if nser == 1:
                if npar == 1:
                    if sub_name and sub_name != 'VSS':
                        self.reconnect_instance_terminal(inst_name, 'BULK', sub_name)
                else:
                    if sub_name and sub_name != 'VSS':
                        term_list = [dict(BULK=sub_name)]
                    else:
                        term_list = None
                    self.array_instance(inst_name, ['%s<%d:0>' % (inst_name, npar - 1)], term_list=term_list)
            else:
                name_list = []
                term_list = []
                for par_idx in range(npar):
                    if nser == 2:
                        pos_name = '%s,%s%d' % (in_name, mid_name, par_idx)
                        neg_name = '%s%d,incm' % (mid_name, par_idx)
                    else:
                        pos_name = '%s,%s%d<%d:0>' % (in_name, mid_name, par_idx, nser - 2)
                        neg_name = '%s%d<%d:0>,incm' % (mid_name, par_idx, nser - 2)
                    if sub_name and sub_name != 'VSS':
                        term_dict = dict(PLUS=pos_name, MINUS=neg_name, BULK=sub_name)
                    else:
                        term_dict = dict(PLUS=pos_name, MINUS=neg_name)
                    name_list.append('%s%d<%d:0>' % (inst_name, par_idx, nser - 1))
                    term_list.append(term_dict)

                self.array_instance(inst_name, name_list, term_list=term_list)

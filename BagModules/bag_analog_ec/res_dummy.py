# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'res_dummy.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_dummy(Module):
    """Module for library bag_analog_ec cell res_dummy.

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
            ndum='number of dummy resistors.',
            sub_name='substrate name.  Empty string to disable.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, l, w, intent, ndum, sub_name):
        rename_sub = False
        # handle substrate pin
        if not sub_name:
            # delete substrate pin
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)
            rename_sub = True

        # design dummy
        if ndum == 0:
            self.delete_instance('RDUM')
        else:
            self.instances['RDUM'].design(w=w, l=l, intent=intent)
            if ndum > 1:
                term_list = [dict(BULK=sub_name)] if rename_sub else None
                self.array_instance('XRDUM', ['XRDUM<%d:0>' % (ndum - 1)], term_list=term_list)
            elif rename_sub:
                self.reconnect_instance_terminal('XRDUM', 'BULK', sub_name)

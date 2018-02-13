# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'cap_mom.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__cap_mom(Module):
    """Module for library bag_analog_ec cell cap_mom.

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
            w='metal resistor width, in meters.',
            l='metal resistor length, in meters.',
            layer='metal resistor layer ID.',
            sub_name='substrate name.  Empty string to disable'
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, w, l, layer, sub_name):
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
        self.instances['XP'].design(w=w, l=l, layer=layer)
        self.instances['XN'].design(w=w, l=l, layer=layer)

        if not sub_name:
            # delete substrate pin
            self.delete_instance('XSUPCONN')
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            self.rename_pin('VSS', sub_name)
            self.reconnect_instance_terminal('XSUPCONN', 'noConn', sub_name)

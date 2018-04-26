# -*- coding: utf-8 -*-

from typing import Dict, Any

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info',
                                                                   'res_ladder_core.yaml'))


# noinspection PyPep8Naming
class bag_analog_ec__res_ladder_core(Module):
    """Module for library bag_analog_ec cell res_ladder_core.

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
            nout='number of outputs.',
            ndum='number of dummy resistors.',
            sub_name='substrate name.  Empty string to disable.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_name='VSS',
        )

    def design(self, l, w, intent, nout, ndum, sub_name):
        if ndum < 0 or nout < 2:
            raise ValueError('Illegal values of ndum or npar')

        # handle pin renaming
        self.rename_pin('out', 'out<%d:1>' % (nout - 1))
        rename = False
        if not sub_name:
            # delete substrate pin
            self.remove_pin('VSS')
        elif sub_name != 'VSS':
            rename = True
            self.rename_pin('VSS', sub_name)

        # design dummy
        if ndum == 0:
            self.delete_instance('RDUM')
        else:
            self.instances['RDUM'].design(w=w, l=l, intent=intent)
            if ndum > 1:
                if rename:
                    term_list = [dict(BULK=sub_name, PLUS=sub_name, MINUS=sub_name)]
                else:
                    term_list = None
                self.array_instance('RDUM', ['RDUM<%d:0>' % (ndum - 1)], term_list=term_list)
            elif rename:
                for name in ('BULK', 'PLUS', 'MINUS'):
                    self.reconnect_instance_terminal('RDUM', name, sub_name)

        # design main resistors
        self.instances['RCORE'].design(w=w, l=l, intent=intent)
        term_list = [dict(PLUS='VDD,out<%d:1>' % (nout - 1),
                          MINUS='out<%d:1>,VSS' % (nout - 1))]
        if rename:
            term_list[0]['BULK'] = sub_name
        self.array_instance('RCORE', ['RCORE<%d:0>' % (nout - 1)], term_list=term_list)

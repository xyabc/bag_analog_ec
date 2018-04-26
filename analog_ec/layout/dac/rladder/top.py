# -*- coding: utf-8 -*-


"""This module defines an array of resistor ladder DACs.
"""

from typing import Dict, Set, Any

from bag.layout.template import TemplateDB, TemplateBase

from .core import ResLadderDAC


class RDACRow(TemplateBase):
    """A voltage DAC made of resistor string ladder.

    Parameters
    ----------
    temp_db : TemplateDB
        the template database.
    lib_name : str
        the layout library name.
    params : Dict[str, Any]
        the parameter values.
    used_names : Set[str]
        a set of already used cell names.
    **kwargs :
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **kwargs) -> None
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        params = ResLadderDAC.get_params_info()
        params['ndacs'] = 'number of DACs in a row.'
        return params

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return ResLadderDAC.get_default_param_values()

    def draw_layout(self):
        # type: () -> None
        ndacs = self.params['ndacs']
        show_pins = self.params['show_pins']

        params = self.params.copy()
        params['show_pins'] = False
        master = self.new_template(params=params, temp_cls=ResLadderDAC)

        bnd_box = master.bound_box
        inst = self.add_instance(master, 'XDAC', nx=ndacs, spx=bnd_box.width_unit, unit_mode=True)

        bnd_box = inst.bound_box
        self.set_size_from_bound_box(master.top_layer, bnd_box)
        self.array_box = bnd_box

        self._sch_params = master.sch_params.copy()

# -*- coding: utf-8 -*-

"""This package contain layout classes for differential amplifiers."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from typing import Dict, Any, Set

from bag.layout.template import TemplateDB

from abs_templates_ec.analog_core import AnalogBase, AnalogBaseInfo


class DiffAmpDiodeLoadPFB(AnalogBase):
    """A differential amplifier with diode load/positive feedback.

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
    **kwargs
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(DiffAmpDiodeLoadPFB, self).__init__(temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            fg_dict='NMOS/PMOS number of fingers dictionary.',
            stack_dict='NMOS/PMOS stack parameter dictionary.',
            ref_ratio='current reference ratio.',
            ndum='Number of left/right dummy fingers.',
            tr_widths='signal wire width dictionary.',
            tr_spaces='signal wire space dictionary.',
            show_pins='True to create pin labels.',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
        )

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        # type: () -> None

        lch = self.params['lch']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        w_dict = self.params['w_dict']
        th_dict = self.params['th_dict']
        fg_dict = self.params['fg_dict']
        stack_dict = self.params['stack_dict']
        ref_ratio = self.params['ref_ratio']
        ndum = self.params['ndum']
        tr_widths = self.params['tr_widths']
        tr_spaces = self.params['tr_spaces']
        show_pins = self.params['show_pins']
        guard_ring_nf = self.params['guard_ring_nf']


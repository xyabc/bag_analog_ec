# -*- coding: utf-8 -*-

"""This module defines various passive high-pass filter generators
"""

from typing import Dict, Set, Any

from bag.util.search import BinaryIterator
from bag.layout.template import TemplateDB

from abs_templates_ec.resistor.core import ResArrayBase, ResArrayBaseInfo


class ResHighPassDiff(ResArrayBase):
    """bias resistor for differential high pass filter.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
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
        ResArrayBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            w='unit resistor width, in meters.',
            h_unit='total height, in resolution units.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            top_layer='The top layer ID',
            nser='number of resistors in series in a branch.',
            ndum='number of dummy resistors.',
            res_type='Resistor intent',
            res_options='Configuration dictionary for ResArrayBase.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            res_type='standard',
            res_options=None,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        w = self.params['w']
        h_unit = self.params['h_unit']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        top_layer = self.params['top_layer']
        nser = self.params['nser']
        ndum = self.params['ndum']
        res_type = self.params['res_type']
        res_options = self.params['res_options']
        show_pins = self.params['show_pins']

        res = self.grid.resolution
        lay_unit = self.grid.layout_unit
        w_unit = int(round(w / lay_unit / res))

        info = ResArrayBaseInfo(self.grid, sub_type, threshold, top_layer=top_layer,
                                res_type=res_type, ext_dir='y', options=res_options,
                                connect_up=True, half_blk_x=True, half_blk_y=True)

        lmin, lmax = info.get_res_length_bounds()
        bin_iter = BinaryIterator(lmin, lmax, step=2)
        while bin_iter.has_next():
            lcur = bin_iter.get_next()
            htot = info.get_place_info(lcur, w_unit, 1, 1)[3]
            if htot < h_unit:
                bin_iter.save()
                bin_iter.up()
            else:
                bin_iter.down()

        l_unit = bin_iter.get_last_save()
        nx = 2 * (nser + ndum)
        self.draw_array(l_unit * lay_unit * res, w, sub_type, threshold, nx=nx, ny=1,
                        top_layer=top_layer, res_type=res_type, ext_dir='y', options=res_options,
                        connect_up=True, half_blk_x=True, half_blk_y=True, min_height=h_unit)




        self._sch_params = dict(
            l=l_unit * lay_unit * res,
            w=w,
            res_type=res_type,
        )

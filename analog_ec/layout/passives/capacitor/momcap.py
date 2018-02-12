# -*- coding: utf-8 -*-

"""This package defines various passives template classes.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.util import BBox
from bag.layout.routing import TrackID
from bag.layout.template import TemplateBase

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class MOMCapCore(TemplateBase):
    """A metal-only finger cap.

    ports are drawn on the layer above cap_top_layer.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
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
        return dict(
            cap_bot_layer='MOM cap bottom layer.',
            cap_top_layer='MOM cap top layer.',
            cap_width='MOM cap width, in layout units.',
            cap_height='MOM cap height, in layout units.',
            port_width='port track width, in number of tracks.',
            show_pins='True to show pin labels.',
            cap_options='MOM cap layout options.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            port_layer=None,
            show_pins=False,
            cap_options=None,
        )

    def draw_layout(self):
        # type: () -> None
        cap_bot_layer = self.params['cap_bot_layer']
        cap_top_layer = self.params['cap_top_layer']
        cap_width = self.params['cap_width']
        cap_height = self.params['cap_height']
        port_width = self.params['port_width']
        show_pins = self.params['show_pins']
        cap_options = self.params['cap_options']

        if cap_options is None:
            cap_options = {}

        cap_box = BBox(0, 0, cap_width, cap_height, self.grid.resolution)
        self.set_size_from_bound_box(cap_top_layer, cap_box, round_up=True)

        num_layer = cap_top_layer - cap_bot_layer + 1
        cap_ports = self.add_mom_cap(self.bound_box, cap_bot_layer, num_layer, **cap_options)

        cp, cn = cap_ports[cap_top_layer]
        cp = cp[0]
        cn = cn[0]
        port_layer = cap_top_layer + 1
        tidx = self.grid.coord_to_nearest_track(port_layer, cp.middle, half_track=True)
        port_tid = TrackID(port_layer, tidx, width=port_width)
        if cp.track_id.base_index < cn.track_id.base_index:
            warr0, warr1 = cp, cn
            name0, name1 = 'plus', 'minus'
        else:
            warr0, warr1 = cn, cp
            name0, name1 = 'minus', 'plus'

        warr0 = self.connect_to_tracks(warr0, port_tid, min_len_mode=-1)
        warr1 = self.connect_to_tracks(warr1, port_tid, min_len_mode=1)
        port_len = warr0.upper - warr0.lower
        self.add_res_metal_warr(port_layer, tidx, warr0.lower - port_len, warr0.lower, width=port_width)
        self.add_res_metal_warr(port_layer, tidx, warr1.upper, warr1.upper + port_len, width=port_width)
        warr0 = self.add_wires(port_layer, tidx, warr0.lower - 2 * port_len,
                               warr0.lower - port_len, width=port_width)
        warr1 = self.add_wires(port_layer, tidx, warr1.upper + port_len,
                               warr1.upper + 2 * port_len, width=port_width)

        self.add_pin(name0, warr0, show=show_pins)
        self.add_pin(name1, warr1, show=show_pins)

        res_w = self.grid.get_track_width(port_layer, port_width) * self.grid.layout_unit
        res_l = port_len * self.grid.layout_unit
        self._sch_params = dict(
            res_w=res_w,
            res_l=res_l,
        )

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

        res = self.grid.resolution

        # setup capacitor options
        port_layer = cap_top_layer + 1
        port_dir = self.grid.get_direction(port_layer)
        top_w = self.grid.get_track_width(port_layer, port_width, unit_mode=True)
        cap_port_width = self.grid.get_min_track_width(cap_top_layer, top_w=top_w, unit_mode=True)
        if cap_options is None:
            cap_options = dict(port_widths={cap_top_layer: cap_port_width})
        elif 'port_widths' in cap_options:
            cap_options = cap_options.copy()
            cap_options['port_widths'] = {cap_top_layer: cap_port_width}
        bot_w = self.grid.get_track_width(cap_top_layer, cap_port_width, unit_mode=True)

        # get port locations
        min_len = self.grid.get_min_length(port_layer, port_width, unit_mode=True)
        via_ext = self.grid.get_via_extensions(cap_top_layer, cap_port_width, port_width, unit_mode=True)[1]
        res_len = top_w
        port_len = max(top_w, min_len - 2 * via_ext - bot_w - res_len)
        port_ext = res_len + port_len

        # set size
        cap_width = int(round(cap_width / res))
        cap_height = int(round(cap_height / res))
        if port_dir == 'y':
            bnd_box = BBox(0, 0, cap_width, cap_height + 2 * port_ext, res, unit_mode=True)
        else:
            bnd_box = BBox(0, 0, cap_width + 2 * port_ext, cap_height, res, unit_mode=True)

        self.set_size_from_bound_box(port_layer, bnd_box, round_up=True)
        bnd_box = self.bound_box

        # draw cap
        cap_xl = bnd_box.xc_unit - cap_width // 2
        cap_yb = bnd_box.yc_unit - cap_height // 2
        cap_box = BBox(cap_xl, cap_yb, cap_xl + cap_width, cap_yb + cap_height, res, unit_mode=True)
        num_layer = cap_top_layer - cap_bot_layer + 1
        cap_ports = self.add_mom_cap(cap_box, cap_bot_layer, num_layer, **cap_options)

        cp, cn = cap_ports[cap_top_layer]
        cp = cp[0]
        cn = cn[0]
        tidx = self.grid.coord_to_nearest_track(port_layer, cp.middle, half_track=True)
        port_tid = TrackID(port_layer, tidx, width=port_width)
        if cp.track_id.base_index < cn.track_id.base_index:
            warr0, warr1 = cp, cn
            name0, name1 = 'plus', 'minus'
        else:
            warr0, warr1 = cn, cp
            name0, name1 = 'minus', 'plus'

        warr0 = self.connect_to_tracks(warr0, port_tid)
        warr1 = self.connect_to_tracks(warr1, port_tid)
        res_len *= res
        port_len *= res
        self.add_res_metal_warr(port_layer, tidx, warr0.lower - res_len, warr0.lower, width=port_width)
        self.add_res_metal_warr(port_layer, tidx, warr1.upper, warr1.upper + res_len, width=port_width)
        warr0 = self.add_wires(port_layer, tidx, warr0.lower - res_len - port_len,
                               warr0.lower - res_len, width=port_width)
        warr1 = self.add_wires(port_layer, tidx, warr1.upper + res_len,
                               warr1.upper + res_len + port_len, width=port_width)

        self.add_pin(name0, warr0, show=show_pins)
        self.add_pin(name1, warr1, show=show_pins)

        res_w = top_w * self.grid.layout_unit
        res_l = res_len * self.grid.layout_unit
        self._sch_params = dict(
            res_w=res_w,
            res_l=res_l,
        )

# -*- coding: utf-8 -*-

"""This package defines various passives template classes.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.util import BBox
from bag.layout.routing import TrackID
from bag.layout.template import TemplateBase

from abs_templates_ec.analog_mos.mos import DummyFillActive

from ..substrate import SubstrateWrapper

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
        # type: () -> Dict[str, Any]
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            bot_layer='MOM cap bottom layer.',
            top_layer='MOM cap top layer.',
            width='MOM cap width, in resolution units.',
            height='MOM cap height, in resolution units.',
            margin='margin between cap and boundary, in resolution units.',
            in_tid='Input TrackID information.',
            out_tid='Output TrackID information.',
            port_tr_w='MOM cap port track width, in number of tracks.',
            options='MOM cap layout options.',
            fill_config='Fill configuration dictionary.  If not None, quantize to fill grid.',
            fill_dummy='True to draw dummy fill.',
            fill_pitch='dummy fill pitch.',
            mos_type='dummy fill transistor type.',
            threshold='dummy fill threshold.',
            half_blk_x='True to allow half horizontal blocks.',
            half_blk_y='True to allow half vertical blocks.',
            show_pins='True to show pin labels.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            margin=0,
            in_tid=None,
            out_tid=None,
            port_tr_w=1,
            options=None,
            fill_config=None,
            fill_dummy=False,
            filL_pitch=2,
            mos_type='nch',
            threshold='standard',
            half_blk_x=True,
            half_blk_y=True,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        bot_layer = self.params['bot_layer']
        top_layer = self.params['top_layer']
        width = self.params['width']
        height = self.params['height']
        margin = self.params['margin']
        in_tid = self.params['in_tid']
        out_tid = self.params['out_tid']
        port_tr_w = self.params['port_tr_w']
        options = self.params['options']
        fill_config = self.params['fill_config']
        fill_dummy = self.params['fill_dummy']
        fill_pitch = self.params['fill_pitch']
        mos_type = self.params['mos_type']
        threshold = self.params['threshold']
        half_blk_x = self.params['half_blk_x']
        half_blk_y = self.params['half_blk_y']
        show_pins = self.params['show_pins']

        res = self.grid.resolution

        io_layer = top_layer + 1
        w_tot = width + 2 * margin
        h_tot = height + 2 * margin
        if fill_config is None:
            w_blk, h_blk = self.grid.get_block_size(io_layer, unit_mode=True,
                                                    half_blk_x=half_blk_x, half_blk_y=half_blk_y)
        else:
            w_blk, h_blk = self.grid.get_fill_size(io_layer, fill_config, unit_mode=True,
                                                   half_blk_x=half_blk_x, half_blk_y=half_blk_y)
        w_tot = -(-w_tot // w_blk) * w_blk
        h_tot = -(-h_tot // h_blk) * h_blk

        # set size
        self.array_box = bnd_box = BBox(0, 0, w_tot, h_tot, res, unit_mode=True)
        self.set_size_from_bound_box(io_layer, bnd_box)
        self.add_cell_boundary(bnd_box)

        # get input/output track location
        io_horiz = self.grid.get_direction(io_layer) == 'x'
        mid_coord = bnd_box.yc_unit if io_horiz else bnd_box.xc_unit
        io_tidx = self.grid.coord_to_nearest_track(io_layer, mid_coord, half_track=True,
                                                   mode=0, unit_mode=True)
        if in_tid is None:
            in_tidx = io_tidx
            in_tr_w = 2
        else:
            in_tidx, in_tr_w = in_tid
        if out_tid is None:
            out_tidx = io_tidx
            out_tr_w = 2
        else:
            out_tidx, out_tr_w = out_tid
        in_tid = TrackID(io_layer, in_tidx, width=in_tr_w)
        out_tid = TrackID(io_layer, out_tidx, width=out_tr_w)

        # setup capacitor options
        # get port width dictionary.  Make sure we can via up to top_layer + 1
        in_w = self.grid.get_track_width(io_layer, in_tr_w, unit_mode=True)
        out_w = self.grid.get_track_width(io_layer, out_tr_w, unit_mode=True)
        top_port_tr_w = self.grid.get_min_track_width(top_layer, top_w=max(in_w, out_w),
                                                      unit_mode=True)
        top_port_tr_w = max(top_port_tr_w, port_tr_w)
        port_tr_w_dict = {lay: port_tr_w for lay in range(bot_layer, top_layer + 1)}
        port_tr_w_dict[top_layer] = top_port_tr_w
        if options is None:
            options = dict(port_widths=port_tr_w_dict)
        else:
            options = options.copy()
            options['port_widths'] = port_tr_w_dict

        # draw cap
        cap_xl = (bnd_box.width_unit - width) // 2
        cap_yb = (bnd_box.height_unit - height) // 2
        cap_box = BBox(cap_xl, cap_yb, cap_xl + width, cap_yb + height, res, unit_mode=True)
        num_layer = top_layer - bot_layer + 1
        cap_ports = self.add_mom_cap(cap_box, bot_layer, num_layer, **options)

        # connect input/output, draw metal resistors
        cout, cin = cap_ports[top_layer]
        cin = cin[0]
        cout = cout[0]
        in_min_len = self.grid.get_min_length(io_layer, in_tr_w, unit_mode=True)
        res_upper = cin.track_id.get_bounds(self.grid, unit_mode=True)[0]
        res_lower = res_upper - in_min_len
        in_lower = min(0, res_lower - in_min_len)
        self.connect_to_tracks(cin, in_tid, track_lower=in_lower, unit_mode=True)
        self.add_res_metal_warr(io_layer, in_tidx, res_lower, res_upper, width=in_tr_w,
                                unit_mode=True)
        in_warr = self.add_wires(io_layer, in_tidx, in_lower, res_lower, width=in_tr_w,
                                 unit_mode=True)

        out_min_len = self.grid.get_min_length(io_layer, out_tr_w, unit_mode=True)
        res_lower = cout.track_id.get_bounds(self.grid, unit_mode=True)[1]
        res_upper = res_lower + out_min_len
        out_upper = max(w_tot, res_upper + out_min_len)
        self.connect_to_tracks(cout, out_tid, track_upper=out_upper, unit_mode=True)
        self.add_res_metal_warr(io_layer, out_tidx, res_lower, res_upper, width=out_tr_w,
                                unit_mode=True)
        out_warr = self.add_wires(io_layer, out_tidx, res_upper, out_upper, width=out_tr_w,
                                  unit_mode=True)

        self.add_pin('plus', in_warr, show=show_pins)
        self.add_pin('minus', out_warr, show=show_pins)

        if fill_dummy:
            for lay in range(1, io_layer + 1):
                self.do_max_space_fill(lay, bnd_box, fill_pitch=fill_pitch)
            dum_params = dict(
                mos_type=mos_type,
                threshold=threshold,
                width=w_tot,
                height=h_tot
            )
            master_dum = self.new_template(params=dum_params, temp_cls=DummyFillActive)
            self.add_instance(master_dum, unit_mode=True)

        lay_unit = self.grid.layout_unit
        self._sch_params = dict(
            res_in_info=(io_layer, in_w * res * lay_unit, in_min_len * res * lay_unit),
            res_out_info=(io_layer, out_w * res * lay_unit, out_min_len * res * lay_unit),
        )


class MOMCapChar(SubstrateWrapper):
    """A MOM Cap with substrate contact.

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
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **kwargs) -> None
        SubstrateWrapper.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            cap_params='MOM cap parameters.',
            sub_lch='Substrate channel length.',
            sub_w='Substrate width.',
            sub_type='Substrate type.  Either "ptap" or "ntap".',
            threshold='Substrate threshold.',
            sub_tr_w='substrate track width in number of tracks.  None for default.',
            show_pins='True to show pin labels.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_tr_w=1,
            show_pins=True,
        )

    def draw_layout(self):
        cap_params = self.params['cap_params'].copy()
        sub_lch = self.params['sub_lch']
        sub_w = self.params['sub_w']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        sub_tr_w = self.params['sub_tr_w']
        show_pins = self.params['show_pins']

        self.draw_layout_helper(MOMCapCore, cap_params, sub_lch, sub_w, sub_tr_w, sub_type,
                                threshold, show_pins, is_passive=False)

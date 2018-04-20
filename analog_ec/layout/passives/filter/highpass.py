# -*- coding: utf-8 -*-

"""This module defines various passive high-pass filter generators
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.util.search import BinaryIterator
from bag.layout.util import BBox
from bag.layout.routing import TrackID

from abs_templates_ec.resistor.core import ResArrayBase, ResArrayBaseInfo

from ..substrate import SubstrateWrapper

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class HighPassDiffCore(ResArrayBase):
    """A differential RC high-pass filter.

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
        # type: () -> Dict[str, Any]
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
            in_tr_info='Input track info.',
            out_tr_info='Output track info.',
            res_type='Resistor intent',
            res_options='Configuration dictionary for ResArrayBase.',
            cap_spx='Capacitor horizontal separation, in resolution units.',
            cap_spy='Capacitor vertical space from resistor ports, in resolution units.',
            cap_margin='Capacitor space from edge, in resolution units.',
            half_blk_x='True to allow for half horizontal blocks.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            res_type='standard',
            res_options=None,
            cap_spx=0,
            cap_spy=0,
            cap_margin=0,
            half_blk_x=True,
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
        in_tr_info = self.params['in_tr_info']
        out_tr_info = self.params['out_tr_info']
        res_type = self.params['res_type']
        res_options = self.params['res_options']
        cap_spx = self.params['cap_spx']
        cap_spy = self.params['cap_spy']
        cap_margin = self.params['cap_margin']
        half_blk_x = self.params['half_blk_x']
        show_pins = self.params['show_pins']

        res = self.grid.resolution
        lay_unit = self.grid.layout_unit
        w_unit = int(round(w / lay_unit / res))

        # find resistor length
        info = ResArrayBaseInfo(self.grid, sub_type, threshold, top_layer=top_layer,
                                res_type=res_type, ext_dir='y', options=res_options,
                                connect_up=True, half_blk_x=half_blk_x, half_blk_y=True)

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

        # draw resistor
        l_unit = bin_iter.get_last_save()
        nx = 2 * (nser + ndum)
        self.draw_array(l_unit * lay_unit * res, w, sub_type, threshold, nx=nx, ny=1,
                        top_layer=top_layer, res_type=res_type, grid_type=None, ext_dir='y',
                        options=res_options, connect_up=True, half_blk_x=half_blk_x,
                        half_blk_y=True, min_height=h_unit)
        # connect resistors
        vdd, biasp, biasn, outp_h, outn_h = self.connect_resistors(ndum, nser)
        # draw MOM cap
        xl = self.grid.get_wire_bounds(biasp.layer_id, biasp.track_id.base_index,
                                       width=biasp.track_id.width, unit_mode=True)[1]
        xr = self.grid.get_wire_bounds(biasn.layer_id, biasn.track_id.base_index,
                                       width=biasn.track_id.width, unit_mode=True)[0]
        caplp, capln, caprp, caprn = self.draw_mom_cap(nser, xl, xr, cap_spx, cap_spy, cap_margin)

        # connect resistors to MOM cap, and draw metal resistors
        vm_layer = self.bot_layer_id + 1
        self.connect_to_tracks(outp_h, capln.track_id)
        self.connect_to_tracks(outn_h, caprn.track_id)

        # connect outputs to horizontal tracks
        hm_layer = vm_layer + 1
        pidx, nidx, tr_w = in_tr_info
        res_in_w = self.grid.get_track_width(hm_layer, tr_w, unit_mode=True)
        inp, inn = self.connect_differential_tracks(caplp, caprp, hm_layer, pidx, nidx, width=tr_w)
        tr_lower, tr_upper = inp.lower_unit, inp.upper_unit
        self.add_res_metal_warr(hm_layer, pidx, tr_lower - res_in_w, tr_lower, width=tr_w,
                                unit_mode=True)
        self.add_res_metal_warr(hm_layer, nidx, tr_lower - res_in_w, tr_lower, width=tr_w,
                                unit_mode=True)
        inp = self.add_wires(hm_layer, pidx, tr_lower - 2 * res_in_w, tr_lower - res_in_w,
                             width=tr_w, unit_mode=True)
        inn = self.add_wires(hm_layer, nidx, tr_lower - 2 * res_in_w, tr_lower - res_in_w,
                             width=tr_w, unit_mode=True)
        pidx, nidx, tr_w = out_tr_info
        res_out_w = self.grid.get_track_width(hm_layer, tr_w, unit_mode=True)
        self.connect_differential_tracks(capln, caprn, hm_layer, pidx, nidx, track_lower=tr_lower,
                                         track_upper=tr_upper, width=tr_w, unit_mode=True)
        self.add_res_metal_warr(hm_layer, pidx, tr_upper, tr_upper + res_out_w, width=tr_w,
                                unit_mode=True)
        self.add_res_metal_warr(hm_layer, nidx, tr_upper, tr_upper + res_out_w, width=tr_w,
                                unit_mode=True)
        outp = self.add_wires(hm_layer, pidx, tr_upper + res_out_w, tr_upper + 2 * res_out_w,
                              width=tr_w, unit_mode=True)
        outn = self.add_wires(hm_layer, nidx, tr_upper + res_out_w, tr_upper + 2 * res_out_w,
                              width=tr_w, unit_mode=True)

        # add pins
        self.add_pin('biasp', biasp, show=show_pins)
        self.add_pin('biasn', biasn, show=show_pins)
        self.add_pin('outp', outp, show=show_pins)
        self.add_pin('outn', outn, show=show_pins)
        self.add_pin('inp', inp, show=show_pins)
        self.add_pin('inn', inn, show=show_pins)
        self.add_pin('VDD', vdd, label='VDD:', show=show_pins)

        self._sch_params = dict(
            l=l_unit * lay_unit * res,
            w=w,
            intent=res_type,
            nser=nser,
            ndum=ndum,
            res_in_info=(hm_layer, res_in_w * res * lay_unit, res_in_w * res * lay_unit),
            res_out_info=(hm_layer, res_out_w * res * lay_unit, res_out_w * res * lay_unit),
        )

    def connect_resistors(self, ndum, nser):
        nx = 2 * (nser + ndum)
        biasp, biasn, outp, outn = [], [], None, None
        for idx in range(ndum):
            biasp.extend(self.get_res_ports(0, idx))
            biasn.extend(self.get_res_ports(0, nx - 1 - idx))
        for idx in range(ndum, nser + ndum):
            cpl = self.get_res_ports(0, idx)
            cpr = self.get_res_ports(0, nx - 1 - idx)
            conn_par = (idx - ndum) % 2
            if idx == ndum:
                biasp.append(cpl[1 - conn_par])
                biasn.append(cpr[1 - conn_par])
            if idx == nser + ndum - 1:
                if idx == ndum:
                    outp = cpl[conn_par]
                    outn = cpr[conn_par]
                else:
                    outp = cpl[1 - conn_par]
                    outn = cpr[1 - conn_par]
            else:
                npl = self.get_res_ports(0, idx + 1)
                npr = self.get_res_ports(0, nx - 2 - idx)
                self.connect_wires([npl[conn_par], cpl[conn_par]])
                self.connect_wires([npr[conn_par], cpr[conn_par]])

        biasp = self.connect_wires(biasp)
        biasn = self.connect_wires(biasn)

        # connect bias wires to vertical tracks
        vm_layer = self.bot_layer_id + 1
        t0 = self.grid.find_next_track(vm_layer, 0, half_track=True,
                                       mode=1, unit_mode=True)
        t1 = self.grid.find_next_track(vm_layer, self.bound_box.right_unit, half_track=True,
                                       mode=-1, unit_mode=True)
        bp_tid = TrackID(vm_layer, t0 + 1)
        bn_tid = TrackID(vm_layer, t1 - 1)
        biasp = self.connect_to_tracks(biasp, bp_tid)
        biasn = self.connect_to_tracks(biasn, bn_tid)
        vdd = self.add_wires(vm_layer, t0, biasp.lower_unit, biasp.upper_unit,
                             num=2, pitch=t1 - t0, unit_mode=True)

        return vdd, biasp, biasn, outp, outn

    def draw_mom_cap(self, nser, xl, xr, cap_spx, cap_spy, cap_margin):
        res = self.grid.resolution

        # get port location
        bot_pin, top_pin = self.get_res_ports(0, 0)
        bot_pin_box = bot_pin.get_bbox_array(self.grid).base
        top_pin_box = top_pin.get_bbox_array(self.grid).base
        bnd_box = self.bound_box
        cap_yb_list = [bnd_box.bottom_unit + cap_spy, bot_pin_box.top_unit + cap_spy,
                       top_pin_box.top_unit + cap_spy]
        cap_yt_list = [bot_pin_box.bottom_unit - cap_spy, top_pin_box.bottom_unit - cap_spy,
                       bnd_box.top_unit - cap_spy]

        # draw MOM cap
        xc = bnd_box.xc_unit
        num_layer = 2
        bot_layer = self.bot_layer_id
        top_layer = bot_layer + num_layer - 1
        # set bottom parity based on number of resistors to avoid via-to-via spacing errors
        if nser % 2 == 0:
            bot_par_list = [(1, 0), (0, 1), (1, 0)]
        else:
            bot_par_list = [(0, 1), (1, 0), (0, 1)]

        spx_le = self.grid.get_line_end_space(bot_layer, 1, unit_mode=True)
        spx_le2 = -(-spx_le // 2)
        cap_spx2 = max(cap_spx // 2, spx_le2)
        cap_xl_list = [xl + cap_margin, xc + cap_spx2]
        cap_xr_list = [xc - cap_spx2, xr - cap_margin]

        rects = []
        capp_list, capn_list = [], []
        port_parity = {top_layer: (1, 0)}
        for cap_xl, cap_xr in zip(cap_xl_list, cap_xr_list):
            curp_list, curn_list = [], []
            for idx, (cap_yb, cap_yt, bot_par) in enumerate(zip(cap_yb_list, cap_yt_list,
                                                                bot_par_list)):
                port_parity[bot_layer] = bot_par
                cap_box = BBox(cap_xl, cap_yb, cap_xr, cap_yt, res, unit_mode=True)
                if idx == 1:
                    ports, cur_rects = self.add_mom_cap(cap_box, bot_layer, num_layer,
                                                        port_parity=port_parity,
                                                        return_cap_wires=True)
                    rects.extend(cur_rects[-1])
                else:
                    ports = self.add_mom_cap(cap_box, bot_layer, num_layer,
                                             port_parity=port_parity)
                capp, capn = ports[top_layer]
                curp_list.append(capp[0])
                curn_list.append(capn[0])

            capp_list.append(curp_list)
            capn_list.append(curn_list)
            port_parity[top_layer] = (0, 1)

        caplp = self.connect_wires(capp_list[0])[0]
        caprp = self.connect_wires(capp_list[1])[0]
        capln = self.connect_wires(capn_list[0])[0]
        caprn = self.connect_wires(capn_list[1])[0]

        # merge cap wires
        yb = caplp.lower_unit
        yt = caplp.upper_unit
        for rect in rects:
            box = BBox(rect.bbox.left_unit, yb, rect.bbox.right_unit, yt, res, unit_mode=True)
            self.add_rect(rect.layer, box)

        # return ports
        return caplp, capln, caprp, caprn


class HighPassDiff(SubstrateWrapper):
    """A differential RC high-pass filter with substrate contact.

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
            w='unit resistor width, in meters.',
            h_unit='total height, in resolution units.',
            sub_w='Substrate width.',
            sub_lch='Substrate channel length.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            top_layer='The top layer ID',
            nser='number of resistors in series in a branch.',
            ndum='number of dummy resistors.',
            in_tr_info='Input track info.',
            out_tr_info='Output track info.',
            res_type='Resistor intent',
            res_options='Configuration dictionary for ResArrayBase.',
            cap_spx='Capacitor horizontal separation, in resolution units.',
            cap_spy='Capacitor vertical space from resistor ports, in resolution units.',
            cap_margin='Capacitor space from edge, in resolution units.',
            sub_tr_w='substrate track width in number of tracks.  None for default.',
            sub_tids='Substrate contact tr_idx/tr_width tuples.',
            end_mode='substrate end mode flag.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            res_type='standard',
            res_options=None,
            cap_spx=0,
            cap_spy=0,
            cap_margin=0,
            sub_tr_w=None,
            sub_tids=None,
            end_mode=15,
            show_pins=True,
        )

    def draw_layout(self):
        h_unit = self.params['h_unit']
        sub_w = self.params['sub_w']
        sub_lch = self.params['sub_lch']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        top_layer = self.params['top_layer']
        in_tr_info = self.params['in_tr_info']
        out_tr_info = self.params['out_tr_info']
        sub_tr_w = self.params['sub_tr_w']
        sub_tids = self.params['sub_tids']
        end_mode = self.params['end_mode']
        show_pins = self.params['show_pins']

        # compute substrate contact height, subtract from h_unit
        bot_end_mode, top_end_mode = self.get_sub_end_modes(end_mode)
        h_subb = self.get_substrate_height(self.grid, top_layer, sub_lch, sub_w, sub_type,
                                           threshold, end_mode=bot_end_mode, is_passive=True)
        h_subt = self.get_substrate_height(self.grid, top_layer, sub_lch, sub_w, sub_type,
                                           threshold, end_mode=top_end_mode, is_passive=True)

        hm_layer = ResArrayBase.get_port_layer_id(self.grid.tech_info) + 2
        tr_off = self.grid.find_next_track(hm_layer, h_subb, half_track=True, mode=1,
                                           unit_mode=True)
        params = self.params.copy()
        params['h_unit'] = h_unit - h_subb - h_subt
        params['in_tr_info'] = (in_tr_info[0] - tr_off, in_tr_info[1] - tr_off, in_tr_info[2])
        params['out_tr_info'] = (out_tr_info[0] - tr_off, out_tr_info[1] - tr_off, out_tr_info[2])
        self.draw_layout_helper(HighPassDiffCore, params, sub_lch, sub_w, sub_tr_w, sub_type,
                                threshold, show_pins, end_mode=end_mode, is_passive=True,
                                sub_tids=sub_tids, )

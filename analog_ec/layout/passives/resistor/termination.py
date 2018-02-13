# -*- coding: utf-8 -*-

"""This module defines termination resistor layout generators.
"""

from typing import TYPE_CHECKING, Dict, Set, Any, List

import math
from itertools import chain

from bag.layout.routing import TrackID
from bag.layout.template import TemplateBase, TemplateDB

from abs_templates_ec.resistor.core import ResArrayBase
from abs_templates_ec.analog_core.substrate import SubstrateContact

if TYPE_CHECKING:
    from bag.layout.routing import WireArray


class TerminationCore(ResArrayBase):
    """An template for creating termination resistors.

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
        ResArrayBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nser='number of resistors in series in a branch.',
            npar='number of branches in parallel.',
            ndum='number of dummy resistors.',
            port_layer='The port layer.',
            em_specs='EM specifications for the termination network.',
            show_pins='True to show pins.',
            res_options='Configuration dictionary for ResArrayBase.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            em_specs=None,
            show_pins=True,
            res_options=None,
        )

    def draw_layout(self):
        # type: () -> None
        l = self.params['l']
        w = self.params['w']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        nser = self.params['nser']
        npar = self.params['npar']
        ndum = self.params['ndum']
        port_layer = self.params['port_layer']
        em_specs = self.params['em_specs']
        show_pins = self.params['show_pins']
        res_options = self.params['res_options']

        bot_layer_id = self.bot_layer_id
        if port_layer < bot_layer_id + 2:
            raise ValueError('port_layer = %d must be at least %d' % (port_layer, bot_layer_id + 2))

        if em_specs is None:
            em_specs = {}
        if res_options is None:
            res_options = {}
        else:
            res_options = res_options.copy()
            del res_options['min_tracks']

        direction = self.grid.get_direction(port_layer)
        min_tracks = [1] * (port_layer - bot_layer_id)
        if direction == 'x':
            nx = npar + 2 * ndum
            ny = 2 * (nser + ndum)
            min_tracks[1] = 2
        else:
            nx = 2 * (nser + ndum)
            ny = npar + 2 * ndum

        div_em_specs = em_specs.copy()
        for key in ('idc', 'iac_rms', 'iac_peak'):
            if key in div_em_specs:
                div_em_specs[key] = div_em_specs[key] / npar
            else:
                div_em_specs[key] = 0.0

        port_width = self.grid.get_min_track_width(port_layer, **em_specs)

        self.draw_array(l, w, sub_type, threshold, nx=nx, ny=ny, min_tracks=min_tracks,
                        em_specs=div_em_specs, top_layer=port_layer, **res_options)

        dum_warrs = self._connect_dummies(direction, nx, ny, ndum)

        if direction == 'x':
            lay_start, port_wires = self._connect_horizontal(nx, ny, ndum)
        else:
            lay_start, port_wires = self._connect_vertical(nx, ny, ndum)

        self._connect_up(port_layer, port_width, lay_start, ndum, npar, port_wires, dum_warrs, show_pins)

    def _connect_up(self, port_layer, port_width, lay_start, ndum, npar, port_wires, dum_warrs, show_pins):
        direction = self.grid.get_direction(port_layer)
        last_dir = 'y' if direction == 'x' else 'x'
        for next_layer in range(lay_start, port_layer + 1):
            if next_layer == port_layer:
                next_w = port_width
            else:
                next_w = self.w_tracks[next_layer - self.bot_layer_id]
            next_dir = self.grid.get_direction(next_layer)
            if next_layer != last_dir:
                # layer direction is orthogonal
                if next_dir == direction:
                    # connect all wires in last layer to one wire
                    for warrs_idx in range(3):
                        cur_warrs = port_wires[warrs_idx]
                        if len(cur_warrs) > 1:
                            mid_coord = (cur_warrs[0].middle + cur_warrs[1].middle) / 2
                        else:
                            mid_coord = cur_warrs[0].middle
                        mid_coord_unit = int(round(mid_coord / self.grid.resolution))
                        tidx = self.grid.coord_to_nearest_track(next_layer, mid_coord_unit,
                                                                half_track=True, unit_mode=True)
                        tid = TrackID(next_layer, tidx, width=next_w)
                        if warrs_idx == 1 and next_layer == lay_start:
                            # connect dummy wires to common mode
                            cur_warrs = cur_warrs + dum_warrs
                        port_wires[warrs_idx] = [self.connect_to_tracks(cur_warrs, tid)]
                else:
                    # draw one wire in middle of each row, then connect last wire to it
                    # this way we distribute currents evenly.
                    cur_p = self.num_tracks[next_layer - self.bot_layer_id]
                    # relative base index.  Round down if we have half-integer number of tracks
                    base_idx_rel = (int(round(cur_p * 2)) // 2 - 1) / 2
                    base_idx = self.get_abs_track_index(next_layer, ndum, base_idx_rel)
                    tid = TrackID(next_layer, base_idx, width=next_w, num=npar, pitch=cur_p)
                    for warrs_idx in range(3):
                        port_wires[warrs_idx] = [self.connect_to_tracks(port_wires[warrs_idx], tid, min_len_mode=0)]
            else:
                # layer direction is the same.  Strap wires to current layer.
                for warrs_idx in range(3):
                    cur_warrs = port_wires[warrs_idx]
                    new_warrs = [self.strap_wires(warr, next_layer, tr_w_list=[next_w], min_len_mode_list=[0])
                                 for warr in cur_warrs]
                    port_wires[warrs_idx] = new_warrs

            last_dir = next_dir

        self.add_pin('inp', port_wires[0], show=show_pins)
        self.add_pin('inn', port_wires[2], show=show_pins)
        self.add_pin('incm', port_wires[1], show=show_pins)

    def _connect_horizontal(self, nx, ny, ndum):
        # connect series column resistors
        lay_offset = self.bot_layer_id
        vm_layer = lay_offset + 1
        vm_w = self.w_tracks[1]
        vm_num = self.num_tracks[1]
        vm_sp = self.grid.get_num_space_tracks(vm_layer, vm_w)
        port_wires = [[], [], []]
        for col_idx in range(ndum, nx - ndum):
            mtr_sum = 2 * self.get_abs_track_index(vm_layer, col_idx, 0) + (vm_num - 1)
            if isinstance(mtr_sum, float):
                mtr_sum = math.floor(mtr_sum)
            mtr_idx = mtr_sum / 2

            tr_id_sel = (TrackID(vm_layer, mtr_idx - (vm_sp + vm_w) / 2, width=vm_w),
                         TrackID(vm_layer, mtr_idx + (vm_sp + vm_w) / 2, width=vm_w))

            for row_idx in range(ndum, ny - ndum - 1):
                ports_b = self.get_res_ports(row_idx, col_idx)
                ports_t = self.get_res_ports(row_idx + 1, col_idx)
                con_par = (col_idx + row_idx) % 2
                mid_wire = self.connect_to_tracks([ports_b[con_par], ports_t[con_par]], tr_id_sel[con_par])
                if row_idx == ndum:
                    bot_wire = self.connect_to_tracks([ports_b[1 - con_par]], tr_id_sel[1 - con_par], min_len_mode=0)
                    port_wires[0].append(bot_wire)
                if row_idx == ny - ndum - 2:
                    top_wire = self.connect_to_tracks([ports_t[1 - con_par]], tr_id_sel[1 - con_par], min_len_mode=0)
                    port_wires[2].append(top_wire)
                if row_idx == (ny // 2) - 1:
                    port_wires[1].append(mid_wire)

        return self.bot_layer_id + 2, port_wires

    def _connect_vertical(self, nx, ny, ndum):
        # connect series row resistors
        port_wires = [[], [], []]
        for row_idx in range(ndum, ny - ndum):
            for col_idx in range(ndum, nx - ndum - 1):
                ports_l = self.get_res_ports(row_idx, col_idx)
                ports_r = self.get_res_ports(row_idx, col_idx + 1)
                con_par = (col_idx + row_idx) % 2
                mid_wire = self.connect_wires([ports_l[con_par], ports_r[con_par]])
                if col_idx == ndum:
                    port_wires[0].append(ports_l[1 - con_par])
                if col_idx == nx - ndum - 2:
                    port_wires[2].append(ports_r[1 - con_par])
                if col_idx == (nx // 2) - 1:
                    port_wires[1].append(mid_wire[0])

        return self.bot_layer_id + 1, port_wires

    def _connect_dummies(self, direction, nx, ny, ndum):
        # type: (str, int, int, int) -> List[WireArray]
        if ndum == 0:
            return []

        # connect row dummies
        row_warrs = []
        for row_idx in chain(range(0, ndum), range(ny - ndum, ny)):
            bot_warrs, top_warrs = [], []
            for col_idx in range(nx):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            row_warrs.extend(self.connect_wires(bot_warrs))
            row_warrs.extend(self.connect_wires(top_warrs))

        # connect left and right dummies
        left_warrs, right_warrs = [], []
        for row_idx in range(ny):
            bot_warrs, top_warrs = [], []
            for col_idx in range(0, ndum):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            left_warrs.extend(self.connect_wires(bot_warrs))
            left_warrs.extend(self.connect_wires(top_warrs))
            bot_warrs, top_warrs = [], []
            for col_idx in range(nx - ndum, nx):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            right_warrs.extend(self.connect_wires(bot_warrs))
            right_warrs.extend(self.connect_wires(top_warrs))

        vm_layer = self.bot_layer_id + 1
        # short left and right dummies to dummy rows
        if direction == 'x':
            test_port = self.get_res_ports(0, ndum - 1)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=-1)
            tid = TrackID(vm_layer, tidx)
            wleft = self.connect_to_tracks(left_warrs + row_warrs, tid)
            test_port = self.get_res_ports(0, nx - ndum)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=1)
            tid = TrackID(vm_layer, tidx)
            wright = self.connect_to_tracks(right_warrs + row_warrs, tid)
            # return vertical wires
            return [wleft, wright]
        else:

            test_port = self.get_res_ports(0, 0)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=-1)
            tid = TrackID(vm_layer, tidx)
            self.connect_to_tracks(left_warrs + row_warrs, tid)
            test_port = self.get_res_ports(0, nx - 1)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=1)
            tid = TrackID(vm_layer, tidx)
            self.connect_to_tracks(right_warrs + row_warrs, tid)
            # return horizontal row wires
            return row_warrs


class Termination(TemplateBase):
    """An template for creating termination resistors.

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

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nser='number of resistors in series in a branch.',
            npar='number of branches in parallel.',
            ndum='number of dummy resistors.',
            port_layer='the port layer.',
            sub_w='substrate contact width. Set to 0 to disable drawing substrate contact.',
            sub_lch='substrate contact channel length.',
            em_specs='EM specifications for the termination network.',
            show_pins='True to show pins.',
            res_options='Configuration dictionary for ResArrayBase.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            em_specs=None,
            show_pins=True,
            res_options=None,
        )

    def draw_layout(self):
        # type: () -> None

        res_params = self.params.copy()
        sub_lch = res_params.pop('sub_lch')
        sub_w = res_params.pop('sub_w')
        sub_type = self.params['sub_type']
        show_pins = self.params['show_pins']
        res_options = self.params['res_options']

        if res_options is None:
            res_options = {}
        res_type = res_options.get('res_type', 'standard')

        res_master = self.new_template(params=res_params, temp_cls=TerminationCore)
        if sub_w == 0:
            # do not draw substrate contact.
            inst = self.add_instance(res_master, inst_name='XRES', loc=(0, 0), unit_mode=True)
            for port_name in inst.port_names_iter():
                self.reexport(inst.get_port(port_name), show=show_pins)
            self.array_box = inst.array_box
            self.set_size_from_bound_box(res_master.top_layer, res_master.bound_box)
        else:
            # draw contact and move array up
            top_layer, nx_arr, ny_arr = res_master.size
            w_pitch, h_pitch = self.grid.get_size_pitch(top_layer, unit_mode=True)
            sub_params = dict(
                top_layer=top_layer,
                lch=sub_lch,
                w=sub_w,
                sub_type=sub_type,
                threshold=self.params['threshold'],
                well_width=res_master.get_well_width(),
                show_pins=False,
                is_passive=True,
                tot_width_parity=nx_arr % 2,
            )
            sub_master = self.new_template(params=sub_params, temp_cls=SubstrateContact)
            sub_box = sub_master.bound_box
            ny_shift = -(-sub_box.height_unit // h_pitch)

            # compute substrate X coordinate so substrate is on its own private horizontal pitch
            sub_x_pitch, _ = sub_master.grid.get_size_pitch(sub_master.size[0], unit_mode=True)
            sub_x = ((w_pitch * nx_arr - sub_box.width_unit) // 2 // sub_x_pitch) * sub_x_pitch

            bot_inst = self.add_instance(sub_master, inst_name='XBSUB', loc=(sub_x, 0), unit_mode=True)
            res_inst = self.add_instance(res_master, inst_name='XRES', loc=(0, ny_shift * h_pitch), unit_mode=True)
            top_yo = (ny_arr + 2 * ny_shift) * h_pitch
            top_inst = self.add_instance(sub_master, inst_name='XTSUB', loc=(sub_x, top_yo),
                                         orient='MX', unit_mode=True)

            # connect implant layers of resistor array and substrate contact together
            for lay in self.grid.tech_info.get_implant_layers(sub_type, res_type=res_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            self.reexport(bot_inst.get_port(port_name), show=show_pins)
            self.reexport(top_inst.get_port(port_name), show=show_pins)
            self.size = top_layer, nx_arr, ny_arr + 2 * ny_shift
            self.array_box = bot_inst.array_box.merge(top_inst.array_box)
            self.add_cell_boundary(self.bound_box)

            for port_name in res_inst.port_names_iter():
                self.reexport(res_inst.get_port(port_name), show=show_pins)


class TerminationCMCore(ResArrayBase):
    """a high-resistance termination used for common-mode biasing.

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
        ResArrayBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            show_pins=True,
            res_options=None,
        )

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nres='number of resistors in a segment.',
            nseg='number of segments.',
            ndum='number of dummy resistors.',
            show_pins='True to draw pin layous.',
            res_options='Configuration dictionary for ResArrayBase.',
        )

    def draw_layout(self):
        # type: () -> None
        l = self.params['l']
        w = self.params['w']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        nres = self.params['nres']
        nseg = self.params['nseg']
        ndum = self.params['ndum']
        show_pins = self.params['show_pins']
        res_options = self.params['res_options']

        if nseg % 2 != 0 or nseg < 0:
            raise ValueError('nseg = %d is not positive and even' % nseg)
        if res_options is None:
            res_options = {}

        min_tracks = res_options.pop('min_tracks', [1, 2, 1])
        nx = nseg + 2 * ndum
        ny = 2 * (nres + ndum)
        self.draw_array(l, w, sub_type, threshold, nx=nx, ny=ny,
                        min_tracks=tuple(min_tracks), **res_options)

        # connect resistors
        dum_warrs = self._connect_dummies('x', nx, ny, ndum)
        inp, inn, incm = self._connect_res(nres, nseg, ndum)
        hm_layer = self.bot_layer_id + 2
        tidx = self.grid.coord_to_nearest_track(hm_layer, incm.middle, half_track=True)
        tid = TrackID(hm_layer, tidx)
        cm_warr = self.connect_to_tracks(dum_warrs + [incm], tid)
        self.add_pin('incm', cm_warr, show=show_pins)
        for warr, name, mode in ((inp, 'inp', 1), (inn, 'inn', -1)):
            tidx = self.grid.coord_to_nearest_track(hm_layer, warr.middle, half_track=True, mode=mode)
            tid = TrackID(hm_layer, tidx)
            self.add_pin(name, self.connect_to_tracks(warr, tid, min_len_mode=0), show=show_pins)

    def _connect_res(self, nres, nseg, ndum):
        lay_offset = self.bot_layer_id
        vm_layer = lay_offset + 1
        vm_w = self.w_tracks[1]
        vm_num = self.num_tracks[1]
        vm_sp = self.grid.get_num_space_tracks(vm_layer, vm_w)
        # draw all vertical connections
        inp = inn = incm = None
        for col_idx in range(ndum, ndum + nseg):
            mtr_sum = 2 * self.get_abs_track_index(vm_layer, col_idx, 0) + (vm_num - 1)
            if isinstance(mtr_sum, float):
                mtr_sum = math.floor(mtr_sum)
            mtr_idx = mtr_sum / 2
            tr_id_sel = (TrackID(vm_layer, mtr_idx - (vm_sp + vm_w) / 2, width=vm_w),
                         TrackID(vm_layer, mtr_idx + (vm_sp + vm_w) / 2, width=vm_w))

            row_offset_top = ndum + nres
            row_offset_bot = ndum + nres - 1
            for row_cnt in range(nres - 1):
                con_par = (row_cnt + 1) % 2
                # top half
                row_idx = row_offset_top + row_cnt
                ports_b0 = self.get_res_ports(row_idx, col_idx)
                ports_t0 = self.get_res_ports(row_idx + 1, col_idx)
                self.connect_to_tracks([ports_b0[con_par], ports_t0[con_par]], tr_id_sel[con_par])
                # bottom half
                row_idx = row_offset_bot - row_cnt
                ports_t1 = self.get_res_ports(row_idx, col_idx)
                ports_b1 = self.get_res_ports(row_idx - 1, col_idx)
                self.connect_to_tracks([ports_b1[1 - con_par], ports_t1[1 - con_par]], tr_id_sel[con_par])
                # save input wires
                if row_cnt == 0:
                    if col_idx == ndum:
                        inp = self.connect_to_tracks([ports_b0[1 - con_par]], tr_id_sel[1 - con_par], min_len_mode=1)
                        inn = self.connect_to_tracks([ports_t1[con_par]], tr_id_sel[1 - con_par], min_len_mode=-1)
                    elif col_idx == ndum + nseg - 1:
                        incm = self.connect_to_tracks([ports_b0[1 - con_par], ports_t1[con_par]],
                                                      tr_id_sel[1 - con_par], min_len_mode=0)
        # draw all horizontal connections
        for col_cnt in range(nseg - 1):
            col_idx = ndum + col_cnt
            base_par = (nres + 1) % 2
            if col_cnt % 2 == 0:
                row_port_list = [(ndum, base_par), (ndum + 2 * nres - 1, 1 - base_par)]
            else:
                row_port_list = [(ndum + nres - 1, 1), (ndum + nres, 0)]

            for row_idx, port_idx in row_port_list:
                ports_l = self.get_res_ports(row_idx, col_idx)
                ports_r = self.get_res_ports(row_idx, col_idx + 1)
                self.connect_wires([ports_l[port_idx], ports_r[port_idx]])

        return inp, inn, incm

    def _connect_dummies(self, direction, nx, ny, ndum):
        # type: (str, int, int, int) -> List[WireArray]
        if ndum == 0:
            return []

        # connect row dummies
        row_warrs = []
        for row_idx in chain(range(0, ndum), range(ny - ndum, ny)):
            bot_warrs, top_warrs = [], []
            for col_idx in range(nx):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            row_warrs.extend(self.connect_wires(bot_warrs))
            row_warrs.extend(self.connect_wires(top_warrs))

        # connect left and right dummies
        left_warrs, right_warrs = [], []
        for row_idx in range(ny):
            bot_warrs, top_warrs = [], []
            for col_idx in range(0, ndum):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            left_warrs.extend(self.connect_wires(bot_warrs))
            left_warrs.extend(self.connect_wires(top_warrs))
            bot_warrs, top_warrs = [], []
            for col_idx in range(nx - ndum, nx):
                bot_port, top_port = self.get_res_ports(row_idx, col_idx)
                bot_warrs.append(bot_port)
                top_warrs.append(top_port)
            right_warrs.extend(self.connect_wires(bot_warrs))
            right_warrs.extend(self.connect_wires(top_warrs))

        vm_layer = self.bot_layer_id + 1
        # short left and right dummies to dummy rows
        if direction == 'x':
            test_port = self.get_res_ports(0, ndum - 1)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=-1)
            tid = TrackID(vm_layer, tidx)
            wleft = self.connect_to_tracks(left_warrs + row_warrs, tid)
            test_port = self.get_res_ports(0, nx - ndum)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=1)
            tid = TrackID(vm_layer, tidx)
            wright = self.connect_to_tracks(right_warrs + row_warrs, tid)
            # return vertical wires
            return [wleft, wright]
        else:

            test_port = self.get_res_ports(0, 0)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=-1)
            tid = TrackID(vm_layer, tidx)
            self.connect_to_tracks(left_warrs + row_warrs, tid)
            test_port = self.get_res_ports(0, nx - 1)[0]
            tidx = self.grid.coord_to_nearest_track(vm_layer, test_port.middle,
                                                    half_track=True, mode=1)
            tid = TrackID(vm_layer, tidx)
            self.connect_to_tracks(right_warrs + row_warrs, tid)
            # return horizontal row wires
            return row_warrs

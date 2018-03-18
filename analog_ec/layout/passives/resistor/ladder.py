# -*- coding: utf-8 -*-

"""This module defines resistor ladder layout generators.
"""

from typing import TYPE_CHECKING, Dict, Set, Any
from itertools import chain

from abs_templates_ec.resistor.core import ResArrayBase

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class ResLadderCore(ResArrayBase):
    """An template for creating a resistor ladder from VDD to VSS.

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
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nx='number of resistors in a row.  Must be even.',
            ny='number of resistors in a column.',
            ndum='number of dummy resistors.',
            show_pins='True to show pins.',
            res_options='Configuration dictionary for ResArrayBase.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            show_pins=True,
            res_options=None,
        )

    def draw_layout(self):
        # type: () -> None
        l = self.params['l']
        w = self.params['w']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        nx = self.params['nx']
        ny = self.params['ny']
        ndum = self.params['ndum']
        res_options = self.params['res_options']

        # error checking
        if nx % 2 != 0 or nx <= 0:
            raise ValueError('number of resistors in a row must be even and positive.')
        if ny % 2 != 0 or ny <= 0:
            raise ValueError('number of resistors in a column must be even and positive.')

        # compute draw_array parameters
        if res_options is None:
            res_options = {}
        elif 'min_tracks' in res_options:
            res_options = res_options.copy()
            res_options.pop('min_tracks')

        # compute min tracks
        hcon_space = 0
        vcon_space = 0
        min_tracks = (4 + 2 * hcon_space, 7 + vcon_space, nx, 1)
        top_layer = self.bot_layer_id + 3
        self.draw_array(l, w, sub_type, threshold, nx=nx + 2 * ndum, ny=ny + 2 * ndum,
                        min_tracks=min_tracks, top_layer=top_layer, connect_up=True, **res_options)

        # export supplies and recompute array_box/size
        tmp = self._draw_metal_tracks(nx, ny, ndum, hcon_space)
        hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup = tmp
        self._connect_ladder(nx, ny, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup)

        # set schematic parameters
        res_type = res_options.get('res_type', 'standard')
        self._sch_params = dict(
            l=l,
            w=w,
            intent=res_type,
            nser=nx,
            npar=ny,
            ndum=ndum,
            sub_name='',
        )

    def _connect_ladder(self, nx, ny, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup):
        tp_idx = self.top_port_idx
        bp_idx = self.bot_port_idx
        # connect main ladder
        for row_idx in range(ndum, ny + ndum):
            rmod = row_idx - ndum
            for col_idx in range(ndum, nx + ndum):
                if ((col_idx == ndum and rmod % 2 == 1) or
                        (col_idx == nx - 1 + ndum and rmod % 2 == 0)):
                    mode = 1 if row_idx == ny + ndum - 1 else 0
                    self._connect_tb(row_idx, col_idx, ndum, tp_idx, hcon_idx_list,
                                     vcon_idx_list, xm_bot_idx, mode=mode)
                if col_idx != nx - 1 + ndum:
                    self._connect_lr(row_idx, col_idx, nx, ndum, tp_idx, bp_idx, hcon_idx_list,
                                     vcon_idx_list, xm_bot_idx)

        # connect to ground
        self._connect_tb(ndum - 1, ndum, ndum, tp_idx, hcon_idx_list,
                         vcon_idx_list, xm_bot_idx, mode=-1)
        # connect to supplies
        self._connect_ground(nx, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup)
        self._connect_power(ny, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup)

        # connect horizontal dummies
        for row_idx in range(ny + 2 * ndum):
            if row_idx < ndum or row_idx >= ny + ndum:
                col_iter = range(nx + 2 * ndum)
            else:
                col_iter = chain(range(ndum), range(nx + ndum, nx + 2 * ndum))
            for col_idx in col_iter:
                conn_tb = col_idx < ndum or col_idx >= nx + ndum
                self._connect_dummy(row_idx, col_idx, conn_tb, tp_idx, bp_idx,
                                    hcon_idx_list, vcon_idx_list)

    def _connect_power(self, ny, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup):
        hm_off, vm_off, xm_off = self.get_track_offsets(ny + ndum, ndum)[:3]
        vm_prev = self.get_track_offsets(ndum, ndum - 1)[1]
        hm_layer = self.bot_layer_id
        vm_layer = hm_layer + 1
        hconn = hcon_idx_list[0]
        vm_idx_list = [vm_off + vcon_idx_list[2], vm_prev + vcon_idx_list[-3],
                       vm_prev + vcon_idx_list[-2]]
        xm_idx_list = [xm_off + xm_bot_idx + idx for idx in range(num_xm_sup)]
        for vm_idx in vm_idx_list:
            # connect supply to vm layer
            self.add_via_on_grid(hm_layer, hm_off + hconn, vm_idx)
            # connect supply to xm layer
            for xm_idx in xm_idx_list:
                self.add_via_on_grid(vm_layer, vm_idx, xm_idx)

    def _connect_ground(self, nx, ndum, hcon_idx_list, vcon_idx_list, xm_bot_idx, num_xm_sup):
        xm_prev = self.get_track_offsets(ndum - 1, ndum)[2]
        hm_off, vm_off, xm_off = self.get_track_offsets(ndum, ndum)[:3]
        vm_prev = self.get_track_offsets(ndum, ndum - 1)[1]
        hm_layer = self.bot_layer_id
        vm_layer = hm_layer + 1
        hconn = hcon_idx_list[0]

        # connect all dummies to ground
        self.add_via_on_grid(hm_layer, hm_off + hconn, vm_prev + vcon_idx_list[-4])

        vm_idx_list = [vm_off + vcon_idx_list[1], vm_off + vcon_idx_list[2],
                       vm_prev + vcon_idx_list[-3], vm_prev + vcon_idx_list[-2]]
        xm_idx_list = [xm_prev + xm_bot_idx + idx for idx in range(nx - num_xm_sup, nx)]
        xm_idx_list.append(xm_off + xm_bot_idx)
        for vm_idx in vm_idx_list:
            # connect supply to vm layer
            self.add_via_on_grid(hm_layer, hm_off + hconn, vm_idx)
            # connect supply to xm layer
            for xm_idx in xm_idx_list:
                self.add_via_on_grid(vm_layer, vm_idx, xm_idx)

    def _connect_dummy(self, row_idx, col_idx, conn_tb, tp_idx, bp_idx,
                       hcon_idx_list, vcon_idx_list):
        hm_off, vm_off = self.get_track_offsets(row_idx, col_idx)[:2]
        hm_layer = self.bot_layer_id
        self.add_via_on_grid(hm_layer, hm_off + tp_idx, vm_off + vcon_idx_list[3])
        self.add_via_on_grid(hm_layer, hm_off + tp_idx, vm_off + vcon_idx_list[-4])
        self.add_via_on_grid(hm_layer, hm_off + hcon_idx_list[1], vm_off + vcon_idx_list[3])
        self.add_via_on_grid(hm_layer, hm_off + hcon_idx_list[1], vm_off + vcon_idx_list[-4])
        self.add_via_on_grid(hm_layer, hm_off + bp_idx, vm_off + vcon_idx_list[3])
        self.add_via_on_grid(hm_layer, hm_off + bp_idx, vm_off + vcon_idx_list[-4])
        if conn_tb:
            self.add_via_on_grid(hm_layer, hm_off + tp_idx, vm_off + vcon_idx_list[1])
            self.add_via_on_grid(hm_layer, hm_off + bp_idx, vm_off + vcon_idx_list[1])

    def _connect_lr(self, row_idx, col_idx, nx, ndum, tp_idx, bp_idx, hcon_idx_list,
                    vcon_idx_list, xm_bot_idx):
        hm_off, vm_off, xm_off = self.get_track_offsets(row_idx, col_idx)[:3]
        vm_next = self.get_track_offsets(row_idx, col_idx + 1)[1]
        hm_layer = self.bot_layer_id
        col_real = col_idx - ndum
        row_real = row_idx - ndum
        if col_real % 2 == 0:
            port = bp_idx
            conn = hcon_idx_list[1]
        else:
            port = tp_idx
            conn = hcon_idx_list[0]
        self.add_via_on_grid(hm_layer, hm_off + port, vm_off + vcon_idx_list[-4])
        self.add_via_on_grid(hm_layer, hm_off + conn, vm_off + vcon_idx_list[-4])
        self.add_via_on_grid(hm_layer, hm_off + conn, vm_off + vcon_idx_list[-1])
        self.add_via_on_grid(hm_layer, hm_off + conn, vm_next + vcon_idx_list[3])
        self.add_via_on_grid(hm_layer, hm_off + port, vm_next + vcon_idx_list[3])

        # connect to output port
        vm_layer = hm_layer + 1
        if row_real % 2 == 0:
            xm_idx = xm_bot_idx + col_real + 1
        else:
            xm_idx = xm_bot_idx + (nx - 1 - col_real)
        self.add_via_on_grid(vm_layer, vm_off + vcon_idx_list[-1], xm_off + xm_idx)

    def _connect_tb(self, row_idx, col_idx, ndum, tp_idx, hcon_idx_list,
                    vcon_idx_list, xm_bot_idx, mode=0):
        # mode = 0 is normal connection, mode = 1 is vdd connection, mode = -1 is vss connection
        hm_off, vm_off = self.get_track_offsets(row_idx, col_idx)[:2]
        hm_next, _, xm_next = self.get_track_offsets(row_idx + 1, col_idx)[:3]
        hm_layer = self.bot_layer_id
        if col_idx == ndum:
            conn1 = vcon_idx_list[1]
            tap = vcon_idx_list[2]
            conn2 = vcon_idx_list[3]
        else:
            conn1 = vcon_idx_list[-2]
            tap = vcon_idx_list[-3]
            conn2 = vcon_idx_list[-4]
        if mode >= 0:
            self.add_via_on_grid(hm_layer, hm_off + tp_idx, vm_off + conn1)
            self.add_via_on_grid(hm_layer, hm_next + hcon_idx_list[0], vm_off + conn1)
        if mode == 0:
            self.add_via_on_grid(hm_layer, hm_next + hcon_idx_list[0], vm_off + tap)

            # connect to output port
            vm_layer = hm_layer + 1
            self.add_via_on_grid(vm_layer, vm_off + tap, xm_next + xm_bot_idx)
        if mode <= 0:
            self.add_via_on_grid(hm_layer, hm_next + hcon_idx_list[0], vm_off + conn2)
            self.add_via_on_grid(hm_layer, hm_next + tp_idx, vm_off + conn2)

    def _draw_metal_tracks(self, nx, ny, ndum, hcon_space):
        show_pins = self.params['show_pins']

        num_h_tracks, num_v_tracks, num_x_tracks = self.num_tracks[0:3]
        xm_bot_idx = (num_x_tracks - nx) / 2

        tp_idx = self.top_port_idx
        bp_idx = self.bot_port_idx
        hm_dtr = hcon_space + 1
        if tp_idx + hm_dtr >= num_h_tracks or bp_idx - hm_dtr < 0:
            # use inner hm tracks instead.
            hm_dtr *= -1
        bcon_idx = bp_idx - hm_dtr
        tcon_idx = tp_idx + hm_dtr

        # get via extensions
        grid = self.grid
        hm_layer = self.bot_layer_id
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        hm_ext, vm_ext = grid.get_via_extensions(hm_layer, 1, 1, unit_mode=True)
        vmx_ext, _ = grid.get_via_extensions(vm_layer, 1, 1, unit_mode=True)

        vm_tidx = [-0.5, 0.5, 1.5, 2.5, num_v_tracks - 3.5, num_v_tracks - 2.5,
                   num_v_tracks - 1.5, num_v_tracks - 0.5]

        # get unit block size
        blk_w, blk_h = self.res_unit_size

        # find top X layer track index that can be connected to supply.
        hm_off, vm_off, xm_off = self.get_track_offsets(0, 0)[:3]
        vm_y1 = max(grid.get_wire_bounds(hm_layer, hm_off + max(bp_idx, bcon_idx),
                                         unit_mode=True)[1] + vm_ext,
                    grid.get_wire_bounds(xm_layer, xm_off + xm_bot_idx,
                                         unit_mode=True)[1] + vmx_ext)
        xm_vdd_top_idx = grid.find_next_track(xm_layer, vm_y1 - vmx_ext, half_track=True,
                                              mode=-1, unit_mode=True)
        num_xm_sup = int(xm_vdd_top_idx - xm_bot_idx - xm_off + 1)

        # get lower/upper bounds of output ports.
        xm_lower = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[0], unit_mode=True)[0]
        vm_off = self.get_track_offsets(0, nx + 2 * ndum - 1)[1]
        xm_upper = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[-1], unit_mode=True)[1]

        # expand range by +/- 1 to draw metal pattern on dummies too
        for row_idx in range(ny + 2 * ndum):
            for col_idx in range(nx + 2 * ndum):
                hm_off, vm_off, xm_off = self.get_track_offsets(row_idx, col_idx)[:3]

                # extend port tracks on hm layer
                hm_lower, _ = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[1], unit_mode=True)
                _, hm_upper = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[-2], unit_mode=True)
                self.add_wires(hm_layer, hm_off + bp_idx, hm_lower - hm_ext, hm_upper + hm_ext,
                               num=2, pitch=tp_idx - bp_idx, unit_mode=True)

                # draw hm layer bridge
                hm_lower, _ = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[0], unit_mode=True)
                _, hm_upper = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[3], unit_mode=True)
                pitch = tcon_idx - bcon_idx
                self.add_wires(hm_layer, hm_off + bcon_idx, hm_lower - hm_ext, hm_upper + hm_ext,
                               num=2, pitch=pitch, unit_mode=True)
                hm_lower, _ = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[-4], unit_mode=True)
                _, hm_upper = grid.get_wire_bounds(vm_layer, vm_off + vm_tidx[-1], unit_mode=True)
                self.add_wires(hm_layer, hm_off + bcon_idx, hm_lower - hm_ext, hm_upper + hm_ext,
                               num=2, pitch=pitch, unit_mode=True)

                # draw vm layer bridges
                vm_lower = min(grid.get_wire_bounds(hm_layer, hm_off + min(bp_idx, bcon_idx),
                                                    unit_mode=True)[0] - vm_ext,
                               grid.get_wire_bounds(xm_layer, xm_off + xm_bot_idx,
                                                    unit_mode=True)[0] - vmx_ext)
                vm_upper = max(grid.get_wire_bounds(hm_layer, hm_off + max(tp_idx, tcon_idx),
                                                    unit_mode=True)[1] + vm_ext,
                               grid.get_wire_bounds(xm_layer, xm_off + xm_bot_idx + nx - 1,
                                                    unit_mode=True)[1] + vmx_ext)
                self.add_wires(vm_layer, vm_off + vm_tidx[0], vm_lower, vm_upper,
                               num=2, pitch=3, unit_mode=True)
                self.add_wires(vm_layer, vm_off + vm_tidx[-4], vm_lower, vm_upper,
                               num=2, pitch=3, unit_mode=True)

                vm_y1 = max(grid.get_wire_bounds(hm_layer, hm_off + max(bp_idx, bcon_idx),
                                                 unit_mode=True)[1] + vm_ext,
                            grid.get_wire_bounds(xm_layer, xm_off + xm_bot_idx,
                                                 unit_mode=True)[1] + vmx_ext)
                vm_y2 = min(grid.get_wire_bounds(hm_layer, hm_off + min(tp_idx, tcon_idx),
                                                 unit_mode=True)[0] - vm_ext,
                            grid.get_wire_bounds(xm_layer, xm_off + xm_bot_idx + nx - 1,
                                                 unit_mode=True)[0] - vmx_ext)
                self.add_wires(vm_layer, vm_off + vm_tidx[1], vm_y2 - blk_h, vm_y1,
                               num=2, pitch=1, unit_mode=True)
                self.add_wires(vm_layer, vm_off + vm_tidx[1], vm_y2, vm_y1 + blk_h,
                               num=2, pitch=1, unit_mode=True)
                self.add_wires(vm_layer, vm_off + vm_tidx[-3], vm_y2 - blk_h, vm_y1,
                               num=2, pitch=1, unit_mode=True)
                self.add_wires(vm_layer, vm_off + vm_tidx[-3], vm_y2, vm_y1 + blk_h,
                               num=2, pitch=1, unit_mode=True)

        # draw and export output ports
        for row in range(ny + 2 * ndum):
            tr_off = self.get_track_offsets(row, 0)[2]
            for tidx in range(nx):
                warr = self.add_wires(xm_layer, tr_off + xm_bot_idx + tidx, lower=xm_lower,
                                      upper=xm_upper, fill_type='VSS', unit_mode=True)
                if row < ndum or (row == ndum and tidx == 0):
                    net_name = 'VSS'
                elif row >= ny + ndum:
                    net_name = 'VDD'
                else:
                    net_name = 'out<%d>' % (tidx + (row - ndum) * nx)
                self.add_pin(net_name, warr, show=show_pins)

        return [bcon_idx, tcon_idx], vm_tidx, xm_bot_idx, num_xm_sup

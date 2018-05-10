# -*- coding: utf-8 -*-


"""This module defines an array of resistor ladder DACs.
"""

from typing import TYPE_CHECKING, Dict, Set, Any, List, Tuple, Optional

from bag.layout.util import BBox
from bag.layout.template import TemplateBase

from abs_templates_ec.routing.fill import PowerFill
from abs_templates_ec.routing.bias import BiasShield, join_bias_vroutes, compute_vroute_width

from .core import ResLadderDAC

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class RDACRow(TemplateBase):
    """A row of resistor ladder DACs.

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
        self._bias_layer = None
        self._bias_info = None

    @property
    def sch_params(self):
        # type: () -> Dict[str, Any]
        return self._sch_params

    @property
    def bias_layer(self):
        # type: () -> int
        return self._bias_layer

    @property
    def bias_info(self):
        # type: () -> List[int, Optional[Tuple[Any]]]
        return self._bias_info

    @classmethod
    def get_cache_properties(cls):
        # type: () -> List[str]
        """Returns a list of properties to cache."""
        return ['sch_params', 'bias_info']

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            nout_list='list of number of outputs for each DAC.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
            fill_config='Fill configuration dictionary.',
            bias_config='Bias routing configuration dictionary.',
            top_layer='top layer ID.',
            num_vdd='Number of VDD-referenced outputs.',
            fill_orient_mode='Fill block orientation mode.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            top_layer=None,
            num_vdd=0,
            fill_orient_mode=0,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        in_tr0 = 1

        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        nout_list = self.params['nout_list']
        res_params = self.params['res_params']
        mux_params = self.params['mux_params']
        fill_config = self.params['fill_config']
        bias_config = self.params['bias_config']
        top_layer = self.params['top_layer']
        num_vdd = self.params['num_vdd']
        fill_orient_mode = self.params['fill_orient_mode']
        show_pins = self.params['show_pins']

        res = self.grid.resolution

        params = dict(
            nin0=nin0,
            nin1=nin1,
            res_params=res_params,
            mux_params=mux_params,
            fill_config=fill_config,
            top_layer=top_layer,
            fill_orient_mode=fill_orient_mode,
            show_pins=False
        )
        master_list = []
        nout_tot = 0
        master_cache = {}
        nout_prev = None
        nout_arr_list = []
        for nout in nout_list:
            if nout == nout_prev:
                master_list[-1][1] += 1
                nout_arr_list[-1][1] += 1
            else:
                if nout in master_cache:
                    master = master_cache[nout]
                else:
                    params['nout'] = nout
                    master = self.new_template(params=params, temp_cls=ResLadderDAC)
                    master_cache[nout] = master
                master_list.append([master, 1])
                nout_arr_list.append([nout, 1])
            nout_tot += nout
            nout_prev = nout

        master0 = master_list[0][0]
        dac_h = master0.bound_box.height_unit
        top_layer = master0.top_layer
        io_layer = master0.get_port('code<0>').get_pins()[0].layer_id - 1

        # compute space required for input bus
        nin = nin0 + nin1
        ntot = nin * nout_tot + nout_tot + 1 + in_tr0
        in_pitch = self.grid.get_track_pitch(io_layer, unit_mode=True)
        blk_w, blk_h = self.grid.get_fill_size(top_layer, fill_config, unit_mode=True)
        ny_input = (-(-(ntot * in_pitch) // blk_h) + 1)
        in_h = ny_input * blk_h
        # compute space required for output bus
        num_vss = nout_tot - num_vdd
        vdd_h = 0 if num_vdd == 0 else BiasShield.get_block_size(self.grid, io_layer, bias_config,
                                                                 num_vdd)[1]
        vss_h = 0 if num_vss == 0 else BiasShield.get_block_size(self.grid, io_layer, bias_config,
                                                                 num_vss)[1]

        inst_list = []
        xcur = 0
        for master, nx in master_list:
            spx = master.bound_box.width_unit
            inst = self.add_instance(master, 'XDAC', loc=(xcur, in_h),
                                     nx=nx, spx=spx, unit_mode=True)
            xcur += nx * spx
            inst_list.append((inst, nx))

        out_y0 = in_h + dac_h
        out_y1 = out_y0 + vdd_h
        out_y1 = -(-out_y1 // blk_h) * blk_h
        tot_h = -(-(out_y1 + vss_h) // blk_h) * blk_h
        bnd_box = BBox(0, 0, xcur, tot_h, res, unit_mode=True)
        self.set_size_from_bound_box(top_layer, bnd_box)
        self.array_box = bnd_box
        self.add_cell_boundary(bnd_box)

        # connect inputs, gather outputs, and draw fill
        out_pins, fm = self._connect_input(inst_list, io_layer, in_tr0, nin, nout_tot,
                                           nout_arr_list, ny_input, blk_w, blk_h,
                                           fill_config, show_pins, fill_orient_mode)

        # draw output bias bus
        tmp = self._connect_output(io_layer, bias_config, out_pins, fm, num_vdd, num_vss, out_y0,
                                   out_y1, tot_h, blk_w, blk_h, show_pins, fill_orient_mode)
        self._bias_info = tmp

        self._sch_params = dict(
            nin0=nin0,
            nin1=nin1,
            nout_arr_list=nout_arr_list,
            res_params=master0.sch_params['res_params'],
            mux_params=master0.sch_params['mux_params'],
        )
        self._bias_layer = io_layer

    def _connect_output(self, io_layer, bias_config, out_pins, fill_master, num_vdd, num_vss,
                        y0, y1, ytop, blk_w, blk_h, show_pins, fill_orient_mode):
        bias_info = [None, None]
        if num_vdd > 0:
            vdd_out = out_pins[:num_vdd]
            vdd_info = BiasShield.connect_bias_shields(self, io_layer, bias_config, vdd_out, y0,
                                                       tr_lower=0, lu_end_mode=1)
            for idx, tr in enumerate(vdd_info.tracks):
                self.add_pin('out<%d>' % idx, tr, show=show_pins, edge_mode=-1)
            vdd_list = vdd_info.supplies
            bias_info[1] = (num_vdd, vdd_info.p0, vdd_info.p1[1] - vdd_info.p0[1])
        else:
            vdd_list = None

        if num_vss > 0:
            vss_out = out_pins[num_vdd:]
            vss_info = BiasShield.connect_bias_shields(self, io_layer, bias_config, vss_out, y1,
                                                       tr_lower=0, lu_end_mode=1)
            for idx, tr in enumerate(vss_info.tracks):
                self.add_pin('out<%d>' % (idx + num_vdd), tr, show=show_pins, edge_mode=-1)
            vss_list = vss_info.supplies
            bias_info[0] = (num_vss, vss_info.p0, vss_info.p1[1] - vss_info.p0[1])
        else:
            vss_list = None

        # draw fill
        nx = self.bound_box.width_unit // blk_w
        ny = (ytop - y0) // blk_h

        orient = PowerFill.get_fill_orient(fill_orient_mode)
        dx = 0 if (fill_orient_mode & 1 == 0) else 1
        dy = 0 if (fill_orient_mode & 2 == 0) else 1
        loc = (dx * blk_w, y0 + dy * blk_h)
        inst = self.add_instance(fill_master, loc=loc, orient=orient, nx=nx, ny=ny,
                                 spx=blk_w, spy=blk_h, unit_mode=True)
        if vdd_list:
            vdd_tid = inst.get_pin('VDD_b', row=0, col=0).track_id
            self.connect_to_tracks(vdd_list, vdd_tid)
        if vss_list:
            ridx = (y1 - y0) // blk_h
            vss_tid = inst.get_pin('VSS_b', row=ridx, col=0).track_id
            self.connect_to_tracks(vss_list, vss_tid)

        return bias_info

    def _connect_input(self, inst_list, in_layer, tr0, nin, nout_tot, nout_arr_list, ny_input,
                       blk_w, blk_h, fill_config, show_pins, fill_orient_mode):
        # export inputs
        cnt = tr0 + 1
        pin_cnt = 0
        fmt = 'code<%d>'
        lower = self.bound_box.xc_unit
        upper = self.bound_box.right_unit
        out_pins = []
        for (inst, nx), (nout, _) in zip(inst_list, nout_arr_list):
            for col_idx in range(nx):
                pin_off = 0
                for out_idx in range(nout):
                    # export output
                    if nout == 1:
                        out_pin = inst.get_pin('out', col=col_idx)
                    else:
                        out_pin = inst.get_pin('out<%d>' % out_idx, col=col_idx)
                    out_pins.append(out_pin)
                    # connect inputs
                    warrs = [inst.get_pin(fmt % (pin_off + in_idx), col=col_idx)
                             for in_idx in range(nin)]
                    tr_idx_list = list(range(cnt, cnt + nin))
                    warrs = self.connect_matching_tracks(warrs, in_layer, tr_idx_list,
                                                         track_upper=upper, unit_mode=True)
                    for idx, w in enumerate(warrs):
                        self.add_pin(fmt % (pin_cnt + idx), w, show=show_pins, edge_mode=1)
                        lower = min(lower, w.lower_unit)
                    cnt += nin + 1
                    pin_off += nin
                    pin_cnt += nin

        # add shield wires, and connect to fill
        sh_warr = self.add_wires(in_layer, tr0, lower, upper, num=nout_tot + 1, pitch=nin + 1,
                                 unit_mode=True)
        bnd_box = self.bound_box.with_interval('y', 0, (ny_input - 1) * blk_h, unit_mode=True)
        nx_input = bnd_box.width_unit // blk_w
        inst_list2 = PowerFill.add_fill_blocks(self, bnd_box, fill_config,
                                               in_layer + 1, in_layer + 2,
                                               orient_mode=fill_orient_mode)
        vss_warrs = [pin for inst in inst_list2[0] for pin in inst.port_pins_iter('VSS_b')]
        vss_warrs = self.connect_wires(vss_warrs)
        self.draw_vias_on_intersections(sh_warr, vss_warrs)
        params = dict(fill_config=fill_config, bot_layer=in_layer + 2, show_pins=False)
        fill_master = self.new_template(params=params, temp_cls=PowerFill)

        orient = PowerFill.get_fill_orient(fill_orient_mode)
        x0 = 0 if (fill_orient_mode & 1 == 0) else 1
        y0 = 0 if (fill_orient_mode & 2 == 0) else 1
        loc = (x0 * blk_w, y0 * blk_h)
        inst = self.add_instance(fill_master, loc=loc, orient=orient, nx=nx_input, ny=ny_input,
                                 spx=blk_w, spy=blk_h, unit_mode=True)
        self.reexport(inst.get_port('VDD', row=0, col=0), show=show_pins)
        self.reexport(inst.get_port('VSS', row=0, col=0), show=show_pins)

        return out_pins, fill_master


class RDACArray(TemplateBase):
    """An array of resistor ladder DACs.

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
        self._bias_info = None

    @property
    def sch_params(self):
        # type: () -> Dict[str, Any]
        return self._sch_params

    @property
    def bias_info(self):
        # type: () -> List[int, Optional[Tuple[Any]]]
        return self._bias_info

    @classmethod
    def get_cache_properties(cls):
        # type: () -> List[str]
        """Returns a list of properties to cache."""
        return ['sch_params', 'bias_info']

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            name_list2='The name of each voltage bias.',
            nout_list2='list of number of outputs for each DAC for each row.',
            num_vdd_list='Number of VDD-referenced outputs per row.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
            fill_config='fill configuration dictionary.',
            bias_config='bias configuration dictionary.',
            top_layer='top layer ID.',
            fill_orient_mode='Fill block orientation mode.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            top_layer=None,
            fill_orient_mode=0,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        name_list2 = self.params['name_list2']
        nout_list2 = self.params['nout_list2']
        num_vdd_list = self.params['num_vdd_list']
        fill_config = self.params['fill_config']
        bias_config = self.params['bias_config']
        fill_orient_mode = self.params['fill_orient_mode']
        show_pins = self.params['show_pins']

        # get number of VDD/VSS bias wires
        num_vdd_tot = num_tot = 0
        for num_vdd, nout_list in zip(num_vdd_list, nout_list2):
            num_vdd_tot += num_vdd
            num_tot += sum(nout_list)
        num_vss_tot = num_tot - num_vdd_tot

        ycur = 0
        inst_list = []
        nout_arr_list = []
        fill_info_list = []
        hm_bias_info_list = []
        params = self.params.copy()
        params['show_pins'] = False
        tot_box = BBox.get_invalid_bbox()
        top_layer = res_params = mux_params = blk_w = blk_h = None
        vm_layer = route_w = vdd_x = vss_x = None
        for row_idx, (num_vdd, nout_list) in enumerate(zip(num_vdd_list, nout_list2)):
            if row_idx % 2 == 0:
                orient = 'R0'
                cur_fo_mode = fill_orient_mode
            else:
                orient = 'MX'
                cur_fo_mode = fill_orient_mode ^ 2
            params['nout_list'] = nout_list
            params['num_vdd'] = num_vdd
            params['fill_orient_mode'] = cur_fo_mode
            master = self.new_template(params=params, temp_cls=RDACRow)
            nout_arr_list.extend(master.sch_params['nout_arr_list'])
            if top_layer is None:
                top_layer = master.top_layer
                vm_layer = master.bias_layer - 1
                res_params = master.sch_params['res_params']
                mux_params = master.sch_params['mux_params']
                blk_w, blk_h = self.grid.get_fill_size(top_layer, fill_config, unit_mode=True)
                tmp = compute_vroute_width(self, vm_layer, blk_w, num_vdd_tot, num_vss_tot,
                                           bias_config)
                route_w, vdd_x, vss_x = tmp

            ny = master.bound_box.height_unit // blk_h
            cur_bias_info = master.bias_info
            if row_idx % 2 == 1:
                ycur += master.bound_box.height_unit
                if cur_bias_info[0] is not None:
                    num_vss, p0, dim = cur_bias_info[0]
                    hm_bias_info_list.append((0, num_vss, ycur - p0[1] - dim))
                if cur_bias_info[1] is not None:
                    num_vdd, p0, dim = cur_bias_info[1]
                    hm_bias_info_list.append((1, num_vdd, ycur - p0[1] - dim))
            else:
                if cur_bias_info[1] is not None:
                    num_vdd, p0, dim = cur_bias_info[1]
                    hm_bias_info_list.append((1, num_vdd, p0[1] + ycur))
                if cur_bias_info[0] is not None:
                    num_vss, p0, dim = cur_bias_info[0]
                    hm_bias_info_list.append((0, num_vss, p0[1] + ycur))

            inst = self.add_instance(master, 'X%d' % row_idx, loc=(route_w, ycur),
                                     orient=orient, unit_mode=True)

            inst_box = inst.bound_box
            fill_info_list.append((inst_box.right_unit, ycur, ny, cur_fo_mode))
            tot_box = tot_box.merge(inst_box)
            ycur = tot_box.top_unit
            inst_list.append(inst)

        self.array_box = tot_box = tot_box.extend(x=0, unit_mode=True)
        self.set_size_from_bound_box(top_layer, tot_box)
        self.add_cell_boundary(tot_box)
        xr_tot = tot_box.right_unit

        nin = nin0 + nin1
        io_name_list = []
        vdd_pins = []
        vss_pins = []
        params = dict(fill_config=fill_config, bot_layer=top_layer - 1, show_pins=False)
        fill_master = self.new_template(params=params, temp_cls=PowerFill)
        for inst, (xr, yf, ny, fo_mode), name_list, num_vdd in zip(inst_list, fill_info_list,
                                                                   name_list2, num_vdd_list):
            # add fill if needed
            dx = xr_tot - xr
            if dx > 0:
                nx = dx // blk_w
                orient = PowerFill.get_fill_orient(fill_orient_mode)
                x0 = 0 if (fill_orient_mode & 1 == 0) else 1
                y0 = 0 if (fill_orient_mode & 2 == 0) else 1
                floc = (xr + x0 * blk_w, yf + y0 * blk_h)
                self.add_instance(fill_master, loc=floc, orient=orient, nx=nx, ny=ny,
                                  spx=blk_w, spy=blk_h, unit_mode=True)

            in_cnt = out_cnt = 0
            for name in name_list:
                opin_name = 'v_%s' % name
                out_pin = inst.get_pin('out<%d>' % out_cnt)
                io_name_list.append(name)
                if out_cnt < num_vdd:
                    vdd_pins.append((opin_name, out_pin))
                else:
                    vss_pins.append((opin_name, out_pin))
                for in_idx in range(nin):
                    in_pin = inst.get_pin('code<%d>' % in_cnt)
                    in_pin = self.extend_wires(in_pin, upper=xr_tot, unit_mode=True)
                    self.add_pin('bias_%s<%d>' % (name, in_idx), in_pin, show=show_pins,
                                 edge_mode=1)
                    in_cnt += 1
                out_cnt += 1

        # draw routes
        vdd_list, vss_list = join_bias_vroutes(self, vm_layer, vdd_x, vss_x, route_w,
                                               num_vdd_tot, num_vss_tot, hm_bias_info_list,
                                               bias_config, vdd_pins, vss_pins, show_pins,
                                               yt=self.bound_box.top_unit)

        # draw fill over routes
        nx = route_w // blk_w
        ny = tot_box.top_unit // blk_h

        orient = PowerFill.get_fill_orient(fill_orient_mode)
        dx = 0 if (fill_orient_mode & 1 == 0) else 1
        dy = 0 if (fill_orient_mode & 2 == 0) else 1
        loc = (dx * blk_w, dy * blk_h)
        inst = self.add_instance(fill_master, loc=loc, orient=orient, nx=nx, ny=ny,
                                 spx=blk_w, spy=blk_h, unit_mode=True)
        if vdd_list:
            self.draw_vias_on_intersections(vdd_list, inst.get_all_port_pins('VDD_b'))
        if vss_list:
            self.draw_vias_on_intersections(vss_list, inst.get_all_port_pins('VSS_b'))

        self.reexport(inst.get_port('VDD'), show=show_pins)
        self.reexport(inst.get_port('VSS'), show=show_pins)

        self._sch_params = dict(
            nin0=nin0,
            nin1=nin1,
            nout_arr_list=nout_arr_list,
            res_params=res_params,
            mux_params=mux_params,
            io_name_list=io_name_list,
        )

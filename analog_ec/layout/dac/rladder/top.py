# -*- coding: utf-8 -*-


"""This module defines an array of resistor ladder DACs.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.util import BBox
from bag.layout.template import TemplateBase

from abs_templates_ec.routing.fill import PowerFill

from .core import ResLadderDAC

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


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
        return dict(
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            nout_list='list of number of outputs for each DAC.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
            fill_config='Fill configuration dictionary.',
            top_layer='top layer ID.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            top_layer=None,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        nout_list = self.params['nout_list']
        res_params = self.params['res_params']
        mux_params = self.params['mux_params']
        fill_config = self.params['fill_config']
        top_layer = self.params['top_layer']
        show_pins = self.params['show_pins']

        res = self.grid.resolution

        params = dict(
            nin0=nin0,
            nin1=nin1,
            res_params=res_params,
            mux_params=mux_params,
            fill_config=fill_config,
            top_layer=top_layer,
            show_pins=False
        )
        master_list = []
        ngrp = 0
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
            ngrp += nout
            nout_prev = nout

        master0 = master_list[0][0]
        height = master0.bound_box.height_unit
        top_layer = master0.top_layer
        in_layer = master0.get_port('code<0>').get_pins()[0].layer_id - 1

        # compute space required for input bus
        nin = nin0 + nin1
        ntot = nin * ngrp + ngrp + 1
        in_pitch = self.grid.get_track_pitch(in_layer, unit_mode=True)
        blk_w, blk_h = self.grid.get_fill_size(top_layer, fill_config, unit_mode=True)
        ny_input = (-(-(ntot * in_pitch) // blk_h) + 1)
        in_height = ny_input * blk_h

        inst_list = []
        xcur = 0
        for master, nx in master_list:
            spx = master.bound_box.width_unit
            inst = self.add_instance(master, 'XDAC', loc=(xcur, in_height),
                                     nx=nx, spx=spx, unit_mode=True)
            xcur += nx * spx
            inst_list.append((inst, nx))

        bnd_box = BBox(0, 0, xcur, height, res, unit_mode=True)
        self.set_size_from_bound_box(top_layer, bnd_box)
        self.array_box = bnd_box

        # connect inputs/outputs
        out_pins = self.connect_io(inst_list, in_layer, nin, ngrp, nout_arr_list, ny_input,
                                   blk_w, blk_h, fill_config, show_pins)
        for idx, warr in enumerate(out_pins):
            self.add_pin('out<%d>' % idx, warr, show=show_pins)

        self._sch_params = dict(
            nin0=nin0,
            nin1=nin1,
            nout_arr_list=nout_arr_list,
            res_params=master0.sch_params['res_params'],
            mux_params=master0.sch_params['mux_params'],
        )

    def connect_io(self, inst_list, in_layer, nin, ngrp, nout_arr_list, ny_input, blk_w, blk_h,
                   fill_config, show_pins):
        # export inputs
        cnt = 1
        pin_cnt = 0
        fmt = 'code<%d>'
        lower = upper = self.bound_box.xc_unit
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
                                                         unit_mode=True)
                    for idx, w in enumerate(warrs):
                        self.add_pin(fmt % (pin_cnt + idx), w, show=show_pins)
                        lower = min(lower, w.lower_unit)
                        upper = max(upper, w.upper_unit)
                    cnt += nin + 1
                    pin_off += nin
                    pin_cnt += nin

        # add shield wires
        sh_warr = self.add_wires(in_layer, 0, lower, upper, num=ngrp + 1, pitch=nin + 1,
                                 unit_mode=True)
        bnd_box = self.bound_box.with_interval('y', 0, (ny_input - 1) * blk_h, unit_mode=True)
        nx_input = bnd_box.width_unit // blk_w
        inst_list2 = PowerFill.add_fill_blocks(self, bnd_box, fill_config,
                                               in_layer + 1, in_layer + 2)
        vss_warrs = [pin for inst in inst_list2[0] for pin in inst.port_pins_iter('VSS_b')]
        vss_warrs = self.connect_wires(vss_warrs)
        self.draw_vias_on_intersections(sh_warr, vss_warrs)
        params = dict(fill_config=fill_config, bot_layer=in_layer + 2, show_pins=False)
        fill_master = self.new_template(params=params, temp_cls=PowerFill)
        inst = self.add_instance(fill_master, loc=(0, 0), nx=nx_input, ny=ny_input,
                                 spx=blk_w, spy=blk_h, unit_mode=True)

        self.reexport(inst.get_port('VDD', row=0, col=0), show=show_pins)
        self.reexport(inst.get_port('VSS', row=0, col=0), show=show_pins)

        return out_pins

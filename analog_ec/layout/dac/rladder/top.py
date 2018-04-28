# -*- coding: utf-8 -*-


"""This module defines an array of resistor ladder DACs.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

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
        params = ResLadderDAC.get_params_info()
        params['ndac'] = 'number of DACs in a row.'
        return params

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return ResLadderDAC.get_default_param_values()

    def draw_layout(self):
        # type: () -> None
        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        fill_config = self.params['fill_config']
        nout = self.params['nout']
        ndac = self.params['ndac']
        show_pins = self.params['show_pins']

        params = self.params.copy()
        params['show_pins'] = False
        master = self.new_template(params=params, temp_cls=ResLadderDAC)

        # compute space required for input bus
        nin = nin0 + nin1
        ngrp = nout * ndac
        ntot = nin * nout * ndac + ngrp + 1
        in_layer = master.get_port('code<0>').get_pins()[0].layer_id - 1
        in_pitch = self.grid.get_track_pitch(in_layer, unit_mode=True)
        blk_w, blk_h = self.grid.get_fill_size(master.top_layer, fill_config, unit_mode=True)
        ny_input = (-(-(ntot * in_pitch) // blk_h) + 1)
        in_height = ny_input * blk_h

        bnd_box = master.bound_box
        inst = self.add_instance(master, 'XDAC', loc=(0, in_height),
                                 nx=ndac, spx=bnd_box.width_unit, unit_mode=True)

        bnd_box = inst.bound_box.extend(y=0, unit_mode=True)
        self.set_size_from_bound_box(master.top_layer, bnd_box)
        self.array_box = bnd_box

        # connect inputs
        self.connect_inputs(inst, in_layer, nin, nout, ny_input, blk_h, fill_config, show_pins)

        self._sch_params = master.sch_params.copy()

    def connect_inputs(self, inst, in_layer, nin, nout, ny_input, blk_h, fill_config, show_pins):
        # export inputs
        cnt = 1
        ndac = inst.nx
        ngrp = nout * ndac
        fmt = 'code<%d>'
        lower = upper = self.bound_box.xc_unit
        for col_idx in range(ndac):
            pin_off = 0
            for out_idx in range(nout):
                warrs = [inst.get_pin(fmt % (pin_off + in_idx), col=col_idx)
                         for in_idx in range(nin)]
                tr_idx_list = list(range(cnt, cnt + nin))
                warrs = self.connect_matching_tracks(warrs, in_layer, tr_idx_list, unit_mode=True)
                for idx, w in enumerate(warrs):
                    self.add_pin(fmt % (cnt + idx), w, show=show_pins)
                    lower = min(lower, w.lower_unit)
                    upper = max(upper, w.upper_unit)
                cnt += nin + 1
                pin_off += nin

        # add shield wires
        sh_warr = self.add_wires(in_layer, 0, lower, upper, num=ngrp + 1, pitch=nin + 1,
                                 unit_mode=True)
        bnd_box = self.bound_box.with_interval('y', 0, (ny_input - 1) * blk_h, unit_mode=True)
        fw, fsp, sp, sp_le = fill_config[in_layer + 1]
        self.do_power_fill(in_layer + 1, sp, sp_le, vss_warrs=sh_warr, bound_box=bnd_box,
                           fill_width=fw, fill_space=fsp, unit_mode=True)

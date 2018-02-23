# -*- coding: utf-8 -*-

"""This class contains top level integration classes for building a clock receiver."""

from typing import TYPE_CHECKING, Dict, Set, Any

from copy import deepcopy

from bag.layout.util import BBox
from bag.layout.template import TemplateBase

from ..passives.capacitor.momcap import MOMCapCore

from .res import ResFeedbackCore
from .amp import InvAmp, NorAmp
from .digital import ClkReset

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class ClkInvAmp(TemplateBase):
    """An AC-coupled clock receiver implemented with psuedo-differential inverters with resistor feedback.

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
        self._y_amp = None

    @property
    def sch_params(self):
        # type: () -> Dict[str, Any]
        return self._sch_params

    @property
    def y_amp(self):
        return self._y_amp

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            res_params='resistor array parameters',
            amp_params='amplifier parameters.',
            cap_params='cap parameters',
            show_pins='True to show pin labels.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            show_pins=True,
        )

    def draw_layout(self):
        res_params = self.params['res_params'].copy()
        amp_params = self.params['amp_params'].copy()
        cap_params = self.params['cap_params'].copy()
        show_pins = self.params['show_pins']

        res_options = res_params.get('res_options', None)
        if res_options is None:
            res_type = 'standard'
        else:
            res_type = res_options.get('res_type', 'standard')

        # make resistor and amplifiers
        res_params['sub_type'] = 'ntap'
        res_params['show_pins'] = False
        res_master = self.new_template(params=res_params, temp_cls=ResFeedbackCore)
        top_layer = res_master.top_layer

        amp_params['top_layer'] = top_layer
        amp_params['show_pins'] = False
        amp_master = self.new_template(params=amp_params, temp_cls=InvAmp)

        # get height, compute capacitor height
        w_res = res_master.bound_box.width_unit
        w_amp = amp_master.bound_box.width_unit
        h_res = res_master.bound_box.height_unit
        h_amp = amp_master.bound_box.height_unit

        h_atot = h_res + 2 * h_amp

        cap_params['cap_top_layer'] = top_layer
        cap_params['sub_name'] = ''
        cap_params['show_pins'] = False
        cap_params['cap_height'] = h_atot // 2 * self.grid.resolution
        cap_master = self.new_template(params=cap_params, temp_cls=MOMCapCore)

        # get overall size and placement
        w_cap = cap_master.bound_box.width_unit
        h_cap = cap_master.bound_box.height_unit

        h_tot = max(h_atot, 2 * h_cap)
        w_atot = max(w_res, w_amp)

        y_capn = h_tot // 2 - h_cap
        y_capp = y_capn + 2 * h_cap
        y_ampn = (h_tot - h_res) // 2 - h_amp
        y_ampp = (h_tot + h_res) // 2 + h_amp
        y_res = (h_tot - h_res) // 2
        x_amp = w_cap + (w_atot - w_amp) // 2
        x_res = w_cap + (w_atot - w_res) // 2
        # set size
        self.set_size_from_bound_box(top_layer, BBox(0, 0, w_atot + w_cap, h_tot, self.grid.resolution,
                                                     unit_mode=True))

        # place amplifiers
        ampn = self.add_instance(amp_master, 'XAMPN', loc=(x_amp, y_ampn), unit_mode=True)
        ampp = self.add_instance(amp_master, 'XAMPP', loc=(x_amp, y_ampp), orient='MX', unit_mode=True)
        res = self.add_instance(res_master, 'XRES', loc=(x_res, y_res), unit_mode=True)

        # merge substrate implant layers
        sub_box = amp_master.get_substrate_box(bottom=False)[0]
        if sub_box is not None:
            bot_sub_box = ampn.translate_master_box(sub_box)
            top_sub_box = ampp.translate_master_box(sub_box)
            for lay in self.grid.tech_info.get_implant_layers('ntap', res_type):
                if self.grid.tech_info.is_well_layer(lay):
                    tot_box = self.get_rect_bbox(lay)
                else:
                    res_box = res_master.get_rect_bbox(lay)
                    res_box = res.translate_master_box(res_box)
                    tot_box = res_box.merge(bot_sub_box).merge(top_sub_box)
                self.add_rect(lay, tot_box)

        # compute cap output port locations
        amp_inp = ampp.get_all_port_pins('in')[0]
        amp_inn = ampn.get_all_port_pins('in')[0]
        inn_coord = self.grid.track_to_coord(amp_inn.layer_id, amp_inn.track_id.base_index, unit_mode=True)
        cap_outn_tidx = self.grid.coord_to_nearest_track(top_layer + 1, inn_coord, half_track=True,
                                                         mode=1, unit_mode=True)
        # update MOM cap master, and add cap instances
        cap_master = cap_master.new_template_with(port_idx=(None, cap_outn_tidx))
        capn = self.add_instance(cap_master, 'XCAPN', loc=(0, y_capn), unit_mode=True)
        capp = self.add_instance(cap_master, 'XCAPP', loc=(0, y_capp), orient='MX', unit_mode=True)

        # connect wires
        res_inp = res.get_all_port_pins('inp')[0]
        res_inn = res.get_all_port_pins('inn')[0]
        res_outp = res.get_all_port_pins('outp')[0]
        res_outn = res.get_all_port_pins('outn')[0]

        amp_outp = ampp.get_all_port_pins('out')[0]
        amp_outn = ampn.get_all_port_pins('out')[0]
        cap_inp = capp.get_all_port_pins('minus')[0]
        cap_inn = capn.get_all_port_pins('minus')[0]
        cap_outp = capp.get_all_port_pins('plus')[0]
        cap_outn = capn.get_all_port_pins('plus')[0]

        self.connect_to_tracks([cap_outp, amp_inp], res_inp.track_id,
                               track_lower=res_inp.lower, track_upper=res_inp.upper)
        self.connect_to_tracks([cap_outn, amp_inn], res_inn.track_id,
                               track_lower=res_inn.lower, track_upper=res_inn.upper)
        self.connect_to_tracks(amp_outp, res_outp.track_id, track_lower=res_outp.lower, track_upper=res_outp.upper)
        self.connect_to_tracks(amp_outn, res_outn.track_id, track_lower=res_outn.lower, track_upper=res_outn.upper)

        # export pins
        self.add_pin('inp', cap_inp, show=show_pins)
        self.add_pin('inn', cap_inn, show=show_pins)
        self.add_pin('outn', amp_outp, show=show_pins)
        self.add_pin('outp', amp_outn, show=show_pins)

        for amp in (ampp, ampn):
            self.reexport(amp.get_port('VDD'), show=show_pins)
            self.reexport(amp.get_port('VSS'), show=show_pins)

        self._y_amp = y_ampn, y_ampp

        # setup schematic parameters
        self._sch_params = dict(
            cap_params=cap_master.sch_params,
            inv_params=amp_master.sch_params,
            res_params=res_master.sch_params,
        )


class ClkAmpReset(TemplateBase):
    """An AC-coupled clock receiver with reset and deterministic startup.

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
        # type: () -> Dict[str, Any]
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            amp_params='clock amplifier parameters',
            nor_params='nor amplifier parameters.',
            dig_params='digital block parameters.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            show_pins=True,
        )

    @classmethod
    def _switch_amp_io(cls, key):
        if key == 'in':
            return 'out'
        elif key == 'out':
            return 'in'
        else:
            return key

    def draw_layout(self):
        amp_params = deepcopy(self.params['amp_params'])
        nor_params = deepcopy(self.params['nor_params'])
        dig_params = self.params['dig_params'].copy()
        show_pins = self.params['show_pins']

        # get track information dictionary for amplifier
        nor_tr_widths = nor_params['tr_widths']
        nor_tr_spaces = nor_params['tr_spaces']
        amp_tr_widths = {}
        amp_tr_spaces = {}
        for key, val in nor_tr_widths.items():
            new_key = self._switch_amp_io(key)
            amp_tr_widths[new_key] = val
        for key, val in nor_tr_spaces.items():
            if isinstance(key, str):
                new_key = self._switch_amp_io(key)

            else:
                new_key = self._switch_amp_io(key[0]), self._switch_amp_io(key[1])
            amp_tr_spaces[new_key] = val

        # make masters
        amp_params['show_pins'] = False
        amp_params['amp_params']['tr_widths'] = amp_tr_widths
        amp_params['amp_params']['tr_spaces'] = amp_tr_spaces
        amp_master = self.new_template(params=amp_params, temp_cls=ClkInvAmp)
        nor_params['show_pins'] = False
        nor_master = self.new_template(params=nor_params, temp_cls=NorAmp)
        dig_params['top_layer'] = amp_master.top_layer
        dig_params['show_pins'] = False
        dig_master = self.new_template(params=dig_params, temp_cls=ClkReset)

        # place blocks
        y_ampn, y_ampp = amp_master.y_amp
        x_nor = amp_master.bound_box.right_unit
        y_dig = (amp_master.bound_box.height_unit - dig_master.bound_box.height_unit) // 2

        amp_inst = self.add_instance(amp_master, 'XAMP')
        norn = self.add_instance(nor_master, 'XNORN', loc=(x_nor, y_ampn), unit_mode=True)
        norp = self.add_instance(nor_master, 'XNORP', loc=(x_nor, y_ampp), orient='MX', unit_mode=True)
        dig = self.add_instance(dig_master, 'XDIG', loc=(x_nor, y_dig), unit_mode=True)

        # connect supplies
        vdd_list = amp_inst.get_all_port_pins('VDD')
        vss_list = amp_inst.get_all_port_pins('VSS')
        vdd_list.extend(norp.get_all_port_pins('VDD'))
        vdd_list.extend(norn.get_all_port_pins('VDD'))
        vss_list.extend(norp.get_all_port_pins('VSS'))
        vss_list.extend(norn.get_all_port_pins('VSS'))
        vdd_list = self.connect_wires(vdd_list)
        vss_list = self.connect_wires(vss_list)
        vm_vdd = dig.get_all_port_pins('VDD')[0]
        vm_vss = dig.get_all_port_pins('VSS')[0]
        self.connect_to_tracks(vdd_list, vm_vdd.track_id)
        self.connect_to_tracks(vss_list, vm_vss.track_id)
        self.add_pin('VDD', vdd_list, show=show_pins)
        self.add_pin('VSS', vss_list, show=show_pins)

        # connect clocks
        amp_outp = amp_inst.get_all_port_pins('outn')[0]
        nor_inp = norp.get_all_port_pins('in')[0]
        amp_outn = amp_inst.get_all_port_pins('outp')[0]
        nor_inn = norn.get_all_port_pins('in')[0]
        self.connect_wires([amp_outp, nor_inp])
        self.connect_wires([amp_outn, nor_inn])
        nor_outp = norp.get_all_port_pins('out')[0]
        nor_outn = norn.get_all_port_pins('out')[0]
        clkp_dig = dig.get_all_port_pins('clkp')[0]
        clkn_dig = dig.get_all_port_pins('clkn')[0]
        self.connect_to_tracks(nor_outp, clkp_dig.track_id, track_lower=clkp_dig.lower)
        self.connect_to_tracks(nor_outn, clkn_dig.track_id, track_upper=clkn_dig.upper)
        self.add_pin('clkp', nor_outp, show=show_pins)
        self.add_pin('clkn', nor_outn, show=show_pins)

        # connect enables
        rstp = norp.get_all_port_pins('enb')[0]
        rstn = norn.get_all_port_pins('enb')[0]
        rstp_dig = dig.get_all_port_pins('rstp')[0]
        rstn_dig = dig.get_all_port_pins('rstn')[0]
        self.connect_to_tracks(rstp, rstp_dig.track_id, track_lower=rstp_dig.lower)
        self.connect_to_tracks(rstn, rstn_dig.track_id, track_upper=rstn_dig.lower)

        # re-export ports
        self.reexport(dig.get_port('rst'), show=show_pins)
        self.reexport(amp_inst.get_port('inp'), show=show_pins)
        self.reexport(amp_inst.get_port('inn'), show=show_pins)

        # get schematic parameters
        self._sch_params = dict(
            amp_params=amp_master.sch_params,
            nor_params=nor_master.sch_params,
            dig_params=dig_master.sch_params,
        )

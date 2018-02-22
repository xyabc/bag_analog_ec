# -*- coding: utf-8 -*-

"""This class contains StdCellBase subclasses needed to build a clock receiver."""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.routing import TrackID, TrackManager
from bag.layout.digital import StdCellTemplate, StdCellBase

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class ClkReset(StdCellBase):
    """Clock receiver startup logic circuit.

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
        StdCellBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            config_file='Standard cell configuration file.',
            tr_widths='signal wire width dictionary.',
            tr_spaces='signal wire space dictionary.',
            top_layer='The template top layer.',
            show_pins='True to show pin labels.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        hm_sp_sig = 1

        config_file = self.params['config_file']
        tr_widths = self.params['tr_widths']
        tr_spaces = self.params['tr_spaces']
        top_layer = self.params['top_layer']
        show_pins = self.params['show_pins']

        tr_manager = TrackManager(self.grid, tr_widths, tr_spaces)

        # use standard cell routing grid
        self.update_routing_grid()

        self.set_draw_boundaries(True)

        # create masters
        tap_params = dict(cell_name='tap_pwr', config_file=config_file)
        tap_master = self.new_template(params=tap_params, temp_cls=StdCellTemplate)
        flop_params = dict(cell_name='dff_1x', config_file=config_file)
        flop_master = self.new_template(params=flop_params, temp_cls=StdCellTemplate)
        inv_params = dict(cell_name='inv_clk_16x', config_file=config_file)
        inv_master = self.new_template(params=inv_params, temp_cls=StdCellTemplate)

        # place instances
        flop_ncol = flop_master.std_size[0]
        tap_ncol = tap_master.std_size[0]
        inv_ncol = inv_master.std_size[0]
        space_ncol = 2
        tap_list = [self.add_std_instance(tap_master, 'XTAP00', loc=(0, 0)),
                    self.add_std_instance(tap_master, 'XTAP01', loc=(0, 1))]
        xcur = tap_ncol + space_ncol
        ff_bot0 = self.add_std_instance(flop_master, 'XFFB0', loc=(xcur, 0))
        ff_bot1 = self.add_std_instance(flop_master, 'XFFB1', loc=(xcur + flop_ncol, 0))
        ff_top0 = self.add_std_instance(flop_master, 'XFFT0', loc=(xcur, 1))
        ff_top1 = self.add_std_instance(flop_master, 'XFFT1', loc=(xcur + flop_ncol, 1))
        xcur += 2 * flop_ncol
        inv_bot0 = self.add_std_instance(inv_master, 'XINVB0', loc=(xcur, 0))
        inv_bot1 = self.add_std_instance(inv_master, 'XINVB1', loc=(xcur + inv_ncol, 0))
        inv_top0 = self.add_std_instance(inv_master, 'XINVT0', loc=(xcur, 1))
        inv_top1 = self.add_std_instance(inv_master, 'XINVT1', loc=(xcur + inv_ncol, 1))
        xcur += 2 * inv_ncol + space_ncol
        tap_list.append(self.add_std_instance(tap_master, 'XTAP10', loc=(xcur, 0)))
        tap_list.append(self.add_std_instance(tap_master, 'XTAP11', loc=(xcur, 1)))

        # set template size and draw space/boundaries
        self.set_std_size((xcur + tap_ncol, 2), top_layer=top_layer)
        self.fill_space()
        self.draw_boundaries()

        # connect signals
        warr_dict = {}
        for inst, name in ((ff_bot0, 'FB0'), (ff_bot1, 'FB1'), (ff_top0, 'FT0'), (ff_top1, 'FT1'),
                           (inv_bot0, 'IB0'), (inv_bot1, 'IB1'), (inv_top0, 'IT0'), (inv_top1, 'IT1')):
            warr_dict['%s%s' % (name, 'I')] = inst.get_all_port_pins('I')[0]
            warr_dict['%s%s' % (name, 'O')] = inst.get_all_port_pins('O')[0]

        port_layer = warr_dict['FB0I'].layer_id
        hm_layer = port_layer + 1
        vm_layer = hm_layer + 1
        if vm_layer < self.grid.top_private_layer + 1:
            raise ValueError('This generator assumes layer %d is public.' % vm_layer)

        mid_tidx = self.grid.coord_to_nearest_track(hm_layer, self.bound_box.height_unit // 2, half_track=True,
                                                    mode=0, unit_mode=True)
        top_tidx = mid_tidx + 1 + hm_sp_sig
        bot_tidx = mid_tidx - 1 - hm_sp_sig
        bot_tid = TrackID(hm_layer, bot_tidx)
        top_tid = TrackID(hm_layer, top_tidx)
        mid_tid = TrackID(hm_layer, mid_tidx)
        self.connect_to_tracks([warr_dict['FB0O'], warr_dict['FB1I'], warr_dict['IB0I']], bot_tid)
        self.connect_to_tracks([warr_dict['FT0O'], warr_dict['FT1I']], top_tid)
        self.connect_to_tracks([warr_dict['FT1O'], warr_dict['FB0I'], warr_dict['IT0I']], mid_tid)
        self.connect_to_tracks([warr_dict['IB0O'], warr_dict['IB1I']], bot_tid)
        self.connect_to_tracks([warr_dict['IT0O'], warr_dict['IT1I']], top_tid)

        # gather/connect supply wires on port layer
        vdd_warrs, vss_warrs = [], []
        for inst in tap_list:
            vdd_warrs.extend(inst.get_all_port_pins('VDD'))
            vss_warrs.extend(inst.get_all_port_pins('VSS'))
        vdd_warrs = self.connect_wires(vdd_warrs)
        vss_warrs = self.connect_wires(vss_warrs)

        # connect reset
        w_rst = tr_manager.get_width(hm_layer, 'reset')
        rst = warr_dict['FT0I']
        rst = self.connect_to_tracks(rst, top_tid, min_len_mode=True)
        vm_tidx = self.grid.coord_to_nearest_track(vm_layer, rst.middle, half_track=True)
        vm_tid = TrackID(vm_layer, vm_tidx, width=w_rst)
        self.add_pin('reset', self.connect_to_tracks(rst, vm_tid, min_len_mode=0), show=show_pins)
        # connect enables
        hm_w_en = tr_manager.get_width(hm_layer, 'en')
        vm_w_en = tr_manager.get_width(vm_layer, 'en')
        for name, pin in (('IT1O', 'enp'), ('IB1O', 'enn')):
            warr = warr_dict[name]
            tid = warr.track_id.base_index
            coord = self.grid.track_to_coord(port_layer, tid, unit_mode=True)
            vm_tidx = self.grid.coord_to_nearest_track(vm_layer, coord, half_track=True, mode=1, unit_mode=True)
            warrs = self.connect_with_via_stack(warr, TrackID(vm_layer, vm_tidx, width=vm_w_en),
                                                tr_w_list=[hm_w_en], min_len_mode_list=0)
            self.add_pin(pin, warrs[-1], show=show_pins)
        # connect clocks and supplies
        clkp = [ff_top0.get_all_port_pins('CLK')[0], ff_top1.get_all_port_pins('CLK')[0]]
        clkn = [ff_bot0.get_all_port_pins('CLK')[0], ff_bot1.get_all_port_pins('CLK')[0]]
        top_tidx = self.grid.coord_to_nearest_track(hm_layer, self.bound_box.height_unit,
                                                    half_track=False, unit_mode=True, mode=1)
        bot_tidx = -1
        hm_w_clk = tr_manager.get_width(hm_layer, 'clk')
        vm_w_clk = tr_manager.get_width(vm_layer, 'clk')
        ntr, ploc_list = tr_manager.place_wires(hm_layer, ['clk', 'sup', 'sup'], start_idx=top_tidx)
        _, nloc_list = tr_manager.place_wires(hm_layer, ['sup', 'sup', 'clk'], start_idx=bot_tidx - ntr)
        clk_tidx = None
        for name, warrs, tidx, wdir in [('clkp', clkp, ploc_list[0], 1), ('clkn', clkn, nloc_list[2], -1)]:
            tid = TrackID(hm_layer, tidx, width=hm_w_clk)
            warr = self.connect_to_tracks(warrs, tid, min_len_mode=0)
            if clk_tidx is None:
                clk_tidx = self.grid.coord_to_nearest_track(vm_layer, warr.middle, mode=0, half_track=True)
            tid = TrackID(vm_layer, clk_tidx, width=vm_w_clk)
            warr = self.connect_to_tracks(warr, tid, min_len_mode=wdir)
            self.add_pin(name, warr, show=show_pins)

        hm_w_sup = tr_manager.get_width(hm_layer, 'sup')
        vm_w_sup = tr_manager.get_width(vm_layer, 'sup')
        vss_list = [self.connect_to_tracks(vss_warrs, TrackID(hm_layer, ploc_list[1], width=hm_w_sup)),
                    self.connect_to_tracks(vss_warrs, TrackID(hm_layer, nloc_list[1], width=hm_w_sup))]
        vdd_list = [self.connect_to_tracks(vdd_warrs, TrackID(hm_layer, ploc_list[2], width=hm_w_sup)),
                    self.connect_to_tracks(vdd_warrs, TrackID(hm_layer, nloc_list[0], width=hm_w_sup))]

        _, sup_loc_list = tr_manager.place_wires(vm_layer, ['clk', 'sup', 'sup'])
        vdd_idx = sup_loc_list[2] + clk_tidx - sup_loc_list[0]
        vss_idx = sup_loc_list[1] + clk_tidx - sup_loc_list[0]
        vss = self.connect_to_tracks(vss_list, TrackID(vm_layer, vss_idx, width=vm_w_sup))
        vdd = self.connect_to_tracks(vdd_list, TrackID(vm_layer, vdd_idx, width=vm_w_sup))

        # export pins
        self.add_pin('VDD', vdd, show=show_pins)
        self.add_pin('VSS', vss, show=show_pins)

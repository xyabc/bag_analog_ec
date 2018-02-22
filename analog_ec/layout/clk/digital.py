# -*- coding: utf-8 -*-

"""This class contains StdCellBase subclasses needed to build a clock receiver."""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.routing import TrackID
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

        config_file = self.params['config_file']
        top_layer = self.params['top_layer']
        show_pins = self.params['show_pins']

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
        mid_tidx = self.grid.coord_to_nearest_track(hm_layer, self.bound_box.height_unit // 2, half_track=True,
                                                    mode=0, unit_mode=True)
        top_tidx = mid_tidx + 2
        bot_tidx = mid_tidx - 2
        bot_tid = TrackID(hm_layer, bot_tidx)
        top_tid = TrackID(hm_layer, top_tidx)
        mid_tid = TrackID(hm_layer, mid_tidx)
        self.connect_to_tracks([warr_dict['FB0O'], warr_dict['FB1I'], warr_dict['IB0I']], bot_tid)
        self.connect_to_tracks([warr_dict['FT0O'], warr_dict['FT1I']], top_tid)
        self.connect_to_tracks([warr_dict['FT1O'], warr_dict['FB0I'], warr_dict['IT0I']], mid_tid)
        self.connect_to_tracks([warr_dict['IB0O'], warr_dict['IB1I']], bot_tid)
        self.connect_to_tracks([warr_dict['IT0O'], warr_dict['IT1I']], top_tid)

        # gather/connect supply wires
        vdd_warrs, vss_warrs = [], []
        for inst in tap_list:
            vdd_warrs.extend(inst.get_all_port_pins('VDD'))
            vss_warrs.extend(inst.get_all_port_pins('VSS'))
        vdd_warrs = self.connect_wires(vdd_warrs)
        vss_warrs = self.connect_wires(vss_warrs)

        # export pins
        self.add_pin('VDD', vdd_warrs, show=show_pins)
        self.add_pin('VSS', vss_warrs, show=show_pins)

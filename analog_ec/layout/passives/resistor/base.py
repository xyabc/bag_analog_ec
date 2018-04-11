# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Dict, Any, Set

import importlib

from bag.layout.template import TemplateBase

from abs_templates_ec.analog_core.substrate import SubstrateContact

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class ResSubstrateWrapper(TemplateBase):
    """A class that appended substrate contacts on top and bottom of a ResArrayBase.

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
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return {
            'module': 'resistor module name.',
            'class': 'resistor class name.',
            'params': 'resistor layout parameters.',
            'sub_w': 'substrate contact width. Set to 0 to disable drawing substrate contact.',
            'sub_lch': 'substrate contact channel length.',
            'sub_tr_w': 'substrate track width in number of tracks.  None for default.',
            'show_pins': 'True to show pins.',
        }

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_tr_w=None,
            show_pins=True,
        )

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        mod = self.params['module']
        cls = self.params['class']
        sub_lch = self.params['sub_lch']
        sub_w = self.params['sub_w']
        sub_tr_w = self.params['sub_tr_w']
        show_pins = self.params['show_pins']
        params = self.params['params'].copy()
        sub_type = params['sub_type']

        cls_mod = importlib.import_module(mod)
        temp_cls = getattr(cls_mod, cls)

        self.draw_layout_helper(temp_cls, params, sub_lch, sub_w, sub_tr_w, sub_type, show_pins)

    def draw_layout_helper(self, temp_cls, params, sub_lch, sub_w, sub_tr_w, sub_type, show_pins):

        params['show_pins'] = False
        res_master = self.new_template(params=params, temp_cls=temp_cls)
        self._sch_params = res_master.sch_params.copy()

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
                threshold=params['threshold'],
                port_width=sub_tr_w,
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

            bot_inst = self.add_instance(sub_master, inst_name='XBSUB', loc=(sub_x, 0),
                                         unit_mode=True)
            res_inst = self.add_instance(res_master, inst_name='XRES',
                                         loc=(0, ny_shift * h_pitch), unit_mode=True)
            top_yo = (ny_arr + 2 * ny_shift) * h_pitch
            top_inst = self.add_instance(sub_master, inst_name='XTSUB', loc=(sub_x, top_yo),
                                         orient='MX', unit_mode=True)

            # connect implant layers of resistor array and substrate contact together
            for lay in self.grid.tech_info.get_well_layers(sub_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            sub_port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            self.reexport(bot_inst.get_port(sub_port_name), show=show_pins)
            self.reexport(top_inst.get_port(sub_port_name), show=show_pins)
            self.size = top_layer, nx_arr, ny_arr + 2 * ny_shift
            self.array_box = bot_inst.array_box.merge(top_inst.array_box)
            self.add_cell_boundary(self.bound_box)

            for port_name in res_inst.port_names_iter():
                self.reexport(res_inst.get_port(port_name), show=show_pins)

            self._sch_params['sub_name'] = sub_port_name

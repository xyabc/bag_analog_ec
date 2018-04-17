# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Dict, Any, Set

import importlib

from bag.layout.util import BBox
from bag.layout.template import TemplateBase

from abs_templates_ec.analog_core.substrate import SubstrateContact

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class SubstrateWrapper(TemplateBase):
    """A class that appended substrate contacts on top and bottom of a given block.

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
        threshold = params['threshold']

        cls_mod = importlib.import_module(mod)
        temp_cls = getattr(cls_mod, cls)

        sch_params, sub_name = self.draw_layout_helper(temp_cls, params, sub_lch, sub_w, sub_tr_w,
                                                       sub_type, threshold, show_pins,
                                                       is_passive=True)

        self._sch_params = sch_params.copy()
        self._sch_params['sub_name'] = sub_name

    def draw_layout_helper(self, temp_cls, params, sub_lch, sub_w, sub_tr_w, sub_type, threshold,
                           show_pins, is_passive=True):
        params['show_pins'] = False

        if sub_w == 0:
            master = self.new_template(params=params, temp_cls=temp_cls)
            top_layer = master.top_layer
            master_box = master.bound_box

            # do not draw substrate contact.
            inst = self.add_instance(master, inst_name='XDEV', loc=(0, 0), unit_mode=True)
            for port_name in inst.port_names_iter():
                self.reexport(inst.get_port(port_name), show=show_pins)
            self.array_box = inst.array_box
            self.set_size_from_bound_box(top_layer, master_box)

            sub_port_name = ''
        else:
            # to center substrate with respect to master, master must have a middle X coordinate
            if 'half_blk_x' not in temp_cls.get_params_info():
                raise ValueError('Layout template %s must have half_blk_x '
                                 'parameter.' % temp_cls.__name__)
            params['half_blk_x'] = False

            master = self.new_template(params=params, temp_cls=temp_cls)
            top_layer = master.top_layer
            master_box = master.bound_box

            res = self.grid.resolution
            blkw, blkh = self.grid.get_block_size(top_layer, unit_mode=True)

            # draw contact and move array up
            if hasattr(master, 'get_well_width'):
                well_width = master.get_well_width()
            else:
                well_width = master_box.width
            sub_params = dict(
                top_layer=top_layer,
                lch=sub_lch,
                w=sub_w,
                sub_type=sub_type,
                threshold=threshold,
                port_width=sub_tr_w,
                well_width=well_width,
                max_nxblk=master_box.width_unit // blkw,
                show_pins=False,
                is_passive=is_passive,
            )
            sub_master = self.new_template(params=sub_params, temp_cls=SubstrateContact)
            sub_box = sub_master.bound_box
            sub_x = (master_box.width_unit - sub_box.width_unit) // 2

            # compute substrate X coordinate so substrate is on its own private horizontal pitch
            bot_inst = self.add_instance(sub_master, inst_name='XBSUB', loc=(sub_x, 0),
                                         unit_mode=True)
            inst = self.add_instance(master, inst_name='XDEV', loc=(0, sub_box.height_unit),
                                     unit_mode=True)
            top_yo = sub_box.height_unit * 2 + master_box.height_unit
            top_inst = self.add_instance(sub_master, inst_name='XTSUB', loc=(sub_x, top_yo),
                                         orient='MX', unit_mode=True)

            # connect implant layers of substrate contact and device together
            for lay in self.grid.tech_info.get_well_layers(sub_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            sub_port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            label = sub_port_name + ':'
            self.reexport(bot_inst.get_port(sub_port_name), label=label, show=show_pins)
            self.reexport(top_inst.get_port(sub_port_name), label=label, show=show_pins)
            arr_box = BBox(0, bot_inst.array_box.bottom_unit, inst.bound_box.right_unit,
                           top_inst.array_box.top_unit, res, unit_mode=True)
            bnd_box = arr_box.extend(y=0, unit_mode=True).extend(y=top_yo, unit_mode=True)
            self.array_box = arr_box
            self.set_size_from_bound_box(top_layer, bnd_box)
            self.add_cell_boundary(bnd_box)

            for port_name in inst.port_names_iter():
                self.reexport(inst.get_port(port_name), show=show_pins)

        return master.sch_params, sub_port_name

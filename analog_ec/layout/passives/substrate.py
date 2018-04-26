# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Dict, Any, Set, Union

import importlib

from bag.layout.util import BBox
from bag.layout.template import TemplateBase

from abs_templates_ec.analog_core.base import AnalogBase
from abs_templates_ec.analog_core.substrate import SubstrateContact

if TYPE_CHECKING:
    from bag.layout.routing import RoutingGrid
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
        self._fg_sub = None

    @property
    def sch_params(self):
        # type: () -> Dict[str, Any]
        return self._sch_params

    @property
    def fg_sub(self):
        # type: () -> int
        return self._fg_sub

    @classmethod
    def get_substrate_height(cls, grid, top_layer, lch, w, sub_type, threshold,
                             end_mode=15, **kwargs):
        # type: (RoutingGrid, int, float, Union[int, float], str, str, int, **kwargs) -> int
        """Compute height of the substrate contact block, given parameters."""
        return SubstrateContact.get_substrate_height(grid, top_layer, lch, w, sub_type, threshold,
                                                     end_mode=end_mode, **kwargs)

    @classmethod
    def get_sub_end_modes(cls, end_mode):
        bot_end_mode = end_mode | 0b0010
        top_end_mode = ((end_mode | 0b0011) & 0b1110) | ((end_mode & 0b0010) >> 1)
        return bot_end_mode, top_end_mode

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
            'end_mode': 'The substrate end_mode.',
            'show_pins': 'True to show pins.',
        }

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            sub_tr_w=None,
            end_mode=15,
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
        end_mode = self.params['end_mode']
        show_pins = self.params['show_pins']
        params = self.params['params'].copy()
        sub_type = params['sub_type']
        threshold = params['threshold']

        cls_mod = importlib.import_module(mod)
        temp_cls = getattr(cls_mod, cls)

        self.draw_layout_helper(temp_cls, params, sub_lch, sub_w, sub_tr_w, sub_type, threshold,
                                show_pins, end_mode=end_mode, is_passive=True)

    def draw_layout_helper(self, temp_cls, params, sub_lch, sub_w, sub_tr_w, sub_type, threshold,
                           show_pins, end_mode=15, is_passive=True, sub_tids=None):
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

            fg_sub = 0
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
            bot_end_mode, top_end_mode = self.get_sub_end_modes(end_mode)
            if sub_tids is not None:
                bot_tid, top_tid = sub_tids
                subb_h = self.get_substrate_height(self.grid, top_layer, sub_lch, sub_w, sub_type,
                                                   threshold, end_mode=bot_end_mode,
                                                   is_passive=is_passive)
                subt_h = self.get_substrate_height(self.grid, top_layer, sub_lch, sub_w, sub_type,
                                                   threshold, end_mode=top_end_mode,
                                                   is_passive=is_passive)
                ytop = subb_h + subt_h + master.bound_box.height_unit

                hm_layer = AnalogBase.get_mos_conn_layer(self.grid.tech_info) + 1
                tr_off = self.grid.find_next_track(hm_layer, ytop, half_track=True, mode=-1,
                                                   unit_mode=True)
                top_tid = (tr_off - top_tid[0], top_tid[1])
            else:
                bot_tid = top_tid = None
            sub_params = dict(
                top_layer=top_layer,
                lch=sub_lch,
                w=sub_w,
                sub_type=sub_type,
                threshold=threshold,
                port_width=sub_tr_w,
                well_width=well_width,
                end_mode=bot_end_mode,
                is_passive=is_passive,
                max_nxblk=master_box.width_unit // blkw,
                port_tid=bot_tid,
                show_pins=False,
            )
            bsub_master = self.new_template(params=sub_params, temp_cls=SubstrateContact)
            tsub_master = bsub_master.new_template_with(end_mode=top_end_mode, port_tid=top_tid)
            bsub_box = bsub_master.bound_box
            sub_x = (master_box.width_unit - bsub_box.width_unit) // 2

            # compute substrate X coordinate so substrate is on its own private horizontal pitch
            bot_inst = self.add_instance(bsub_master, inst_name='XBSUB', loc=(sub_x, 0),
                                         unit_mode=True)
            ycur = bot_inst.bound_box.top_unit
            inst = self.add_instance(master, inst_name='XDEV', loc=(0, ycur),
                                     unit_mode=True)
            ycur = inst.bound_box.top_unit + tsub_master.bound_box.height_unit
            top_inst = self.add_instance(tsub_master, inst_name='XTSUB', loc=(sub_x, ycur),
                                         orient='MX', unit_mode=True)

            # connect implant layers of substrate contact and device together
            for lay in self.grid.tech_info.get_well_layers(sub_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            sub_port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            label = sub_port_name + ':'
            self.reexport(bot_inst.get_port(sub_port_name), label=label, show=show_pins)
            self.reexport(top_inst.get_port(sub_port_name), label=label, show=show_pins)
            arr_yb, arr_yt = bot_inst.array_box.bottom_unit, top_inst.array_box.top_unit
            arr_box = BBox(0, arr_yb, inst.bound_box.right_unit, arr_yt, res, unit_mode=True)
            bnd_box = arr_box.extend(y=0, unit_mode=True).extend(y=ycur, unit_mode=True)
            self.array_box = arr_box
            self.set_size_from_bound_box(top_layer, bnd_box)
            self.add_cell_boundary(bnd_box)

            for port_name in inst.port_names_iter():
                cur_label = label if port_name == sub_port_name else ''
                self.reexport(inst.get_port(port_name), label=cur_label, show=show_pins)

            fg_sub = bsub_master.fg_tot

        self._sch_params = master.sch_params.copy()
        self._sch_params['sub_name'] = sub_port_name
        self._fg_sub = fg_sub

        return inst

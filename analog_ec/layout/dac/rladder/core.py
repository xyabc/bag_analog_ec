# -*- coding: utf-8 -*-

"""This module defines the resistor ladder DAC template.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.template import TemplateBase
from bag.layout.util import BBox

from abs_templates_ec.routing.fill import PowerFill

from ...passives.resistor.ladder import ResLadderTop
from .mux_stdcell import RLadderMuxArray

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class ResLadderDAC(TemplateBase):
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
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
            fill_config='Fill configuration dictionary.',
            nout='number of outputs.',
            top_layer='top layer ID.',
            fill_orient_mode='Fill block orientation mode.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            nout=1,
            top_layer=None,
            fill_orient_mode=0,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        res_params = self.params['res_params']
        mux_params = self.params['mux_params']
        fill_config = self.params['fill_config']
        nout = self.params['nout']
        top_layer = self.params['top_layer']
        fill_orient_mode = self.params['fill_orient_mode']
        show_pins = self.params['show_pins']

        if nout <= 0:
            raise ValueError('nout must be positive.')

        res = self.grid.resolution
        num_mux_left = nout // 2
        num_mux_right = nout - num_mux_left
        num_col = 2 ** nin0
        num_row = 2 ** nin1
        nbits_tot = nin0 + nin1

        # make masters
        r_params = res_params.copy()
        r_params['nx'] = num_col
        r_params['ny'] = num_row
        r_params['show_pins'] = False
        res_master = self.new_template(params=r_params, temp_cls=ResLadderTop)
        sup_layer = res_master.top_layer + 1
        if top_layer is None:
            top_layer = res_master.top_layer + 1
        elif top_layer < sup_layer:
            raise ValueError('top_layer must be >= %d' % sup_layer)

        m_params = mux_params.copy()
        m_params['col_nbits'] = nin0
        m_params['row_nbits'] = nin1
        m_params['top_layer'] = res_master.top_layer
        m_params['show_pins'] = False
        if num_mux_left > 0:
            m_params['num_mux'] = num_mux_left
            lmux_master = self.new_template(params=m_params, temp_cls=RLadderMuxArray)
        else:
            lmux_master = None

        m_params['num_mux'] = num_mux_right
        rmux_master = self.new_template(params=m_params, temp_cls=RLadderMuxArray)

        # figure out Y coordinates
        mux_warr = rmux_master.get_port('in<1>').get_pins()[0]
        pin_layer = mux_warr.layer_id
        tr_pitch = self.grid.get_track_pitch(pin_layer, unit_mode=True)
        mux_tr = mux_warr.track_id.base_index
        res_tr = res_master.get_port('out<1>').get_pins()[0].track_id.base_index
        res_yo = int(round(max(mux_tr - res_tr, 0))) * tr_pitch
        mux_yo = int(round(max(res_tr - mux_tr, 0))) * tr_pitch

        # place left mux
        sup_table = {'VDD': [], 'VSS': []}
        if lmux_master is not None:
            blk_w, blk_h = self.grid.get_size_dimension(lmux_master.size, unit_mode=True)
            lmux_inst = self.add_instance(lmux_master, loc=(blk_w, mux_yo), orient='MY',
                                          unit_mode=True)

            # gather supply and re-export inputs
            for port_name, port_list in sup_table.items():
                port_list.extend(lmux_inst.port_pins_iter(port_name))
            for mux_idx in range(num_mux_left):
                self.reexport(lmux_inst.get_port('out<%d>' % mux_idx), show=show_pins)
                for bit_idx in range(nbits_tot):
                    self.reexport(lmux_inst.get_port('code<%d>' % (bit_idx + mux_idx * nbits_tot)),
                                  show=show_pins)

            vref_left = int(round(lmux_inst.get_port('in<1>').get_pins()[0].lower / res))
            xo = blk_w
            self.array_box = lmux_inst.array_box
        else:
            xo = 0
            vref_left = -1
            self.array_box = BBox.get_invalid_bbox()

        # place resistor ladder
        res_inst = self.add_instance(res_master, loc=(xo, res_yo), unit_mode=True)
        for port_name, port_list in sup_table.items():
            port_list.extend(res_inst.port_pins_iter(port_name))
        if vref_left < 0:
            vref_left = int(round(res_inst.get_port('out<1>').get_pins()[0].lower / res))

        res_w, res_h = self.grid.get_size_dimension(res_master.size, unit_mode=True)
        xo += res_w
        # place right mux
        rmux_inst = self.add_instance(rmux_master, loc=(xo, mux_yo), unit_mode=True)
        rmux_w, rmux_h = self.grid.get_size_dimension(rmux_master.size, unit_mode=True)
        xo += rmux_w
        out_off = num_mux_left
        in_off = num_mux_left * nbits_tot
        for port_name, port_list in sup_table.items():
            port_list.extend(rmux_inst.port_pins_iter(port_name))
        for mux_idx in range(num_mux_right):
            old_name = 'out<%d>' % mux_idx
            new_name = 'out' if nout == 1 else 'out<%d>' % (mux_idx + out_off)
            self.reexport(rmux_inst.get_port(old_name), net_name=new_name, show=show_pins)
            for bit_idx in range(nbits_tot):
                old_name = 'code<%d>' % (bit_idx + mux_idx * nbits_tot)
                new_name = 'code<%d>' % (bit_idx + mux_idx * nbits_tot + in_off)
                self.reexport(rmux_inst.get_port(old_name), net_name=new_name, show=show_pins)
        vref_right = int(round(rmux_inst.get_port('in<1>').get_pins()[0].upper / res))

        for vref_idx in range(2 ** nbits_tot):
            vref_warr = rmux_inst.get_port('in<%d>' % vref_idx).get_pins()[0]
            vref_tr = vref_warr.track_id.base_index
            vref_layer = vref_warr.track_id.layer_id
            self.add_wires(vref_layer, vref_tr, vref_left, vref_right, unit_mode=True)

        # set size
        yo = max(mux_yo + rmux_h, res_yo + res_h)
        blk_w, blk_h = self.grid.get_fill_size(top_layer, fill_config, unit_mode=True)
        nfill_x = -(-xo // blk_w)  # type: int
        nfill_y = -(-yo // blk_h)
        bnd_box = BBox(0, 0, nfill_x * blk_w, nfill_y * blk_h, res, unit_mode=True)
        self.set_size_from_bound_box(top_layer, bnd_box)
        self.array_box = bnd_box
        self.add_cell_boundary(bnd_box)

        # connect supplies
        vdd_list = sup_table['VDD']
        vss_list = sup_table['VSS']
        flip_fill = (fill_orient_mode & 2 != 0)
        fill_width, fill_space, space, space_le = fill_config[sup_layer]
        vdd_list, vss_list = self.do_power_fill(sup_layer, space, space_le, vdd_warrs=vdd_list,
                                                vss_warrs=vss_list, fill_width=fill_width,
                                                fill_space=fill_space, flip=flip_fill,
                                                unit_mode=True)
        # add fill cells
        if top_layer > sup_layer:
            fill_params = dict(
                fill_config=fill_config,
                bot_layer=sup_layer,
                top_layer=top_layer,
                show_pins=False,
            )
            orient = PowerFill.get_fill_orient(fill_orient_mode)
            x0 = 0 if (fill_orient_mode & 1 == 0) else 1
            y0 = 0 if (fill_orient_mode & 2 == 0) else 1
            loc = (x0 * blk_w, y0 * blk_h)
            fill_master = self.new_template(params=fill_params, temp_cls=PowerFill)
            fill_inst = self.add_instance(fill_master, 'XFILL', loc=loc, orient=orient, nx=nfill_x,
                                          ny=nfill_y, spx=blk_w, spy=blk_h, unit_mode=True)
            vdd_list = fill_inst.get_all_port_pins('VDD')
            vss_list = fill_inst.get_all_port_pins('VSS')

        self.add_pin('VDD', self.connect_wires(vdd_list), show=show_pins)
        self.add_pin('VSS', self.connect_wires(vss_list), show=show_pins)

        res_sch_params = res_master.sch_params.copy()
        mux_sch_params = rmux_master.mux_params.copy()
        del res_sch_params['nout']
        del mux_sch_params['nin0']
        del mux_sch_params['nin1']
        self._sch_params = dict(
            nin0=nin0,
            nin1=nin1,
            nout=nout,
            res_params=res_sch_params,
            mux_params=mux_sch_params,
        )

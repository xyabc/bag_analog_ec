# -*- coding: utf-8 -*-

"""This module defines termination resistor layout generators.
"""

from typing import Dict, Set, Any

from bag.layout.routing import TrackID
from bag.layout.template import TemplateBase, TemplateDB

from abs_templates_ec.resistor.core import ResArrayBase
from abs_templates_ec.analog_core.substrate import SubstrateContact


class TerminationCore(ResArrayBase):
    """An template for creating termination resistors.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    **kwargs :
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(TerminationCore, self).__init__(temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : Dict[str, Any]
            dictionary of default parameter values.
        """
        return dict(
            nx=2,
            ny=1,
            res_type='reference',
            grid_type='standard',
            em_specs={},
            ext_dir='',
            show_pins=True,
            top_layer=None,
        )

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nx='number of resistors in a row.  Must be even.',
            ny='number of resistors in a column.',
            res_type='the resistor type.',
            grid_type='the resistor routing grid type.',
            em_specs='EM specifications for the termination network.',
            ext_dir='resistor core extension direction.',
            show_pins='True to show pins.',
            top_layer='The top level metal layer.  None for primitive template.',
        )

    def draw_layout(self):
        # type: () -> None

        # draw array
        nx = self.params['nx']
        ny = self.params['ny']
        em_specs = self.params.pop('em_specs')
        show_pins = self.params.pop('show_pins')

        if nx % 2 != 0 or nx <= 0:
            raise ValueError('number of resistors in a row must be even and positive.')

        div_em_specs = em_specs.copy()
        for key in ('idc', 'iac_rms', 'iac_peak'):
            if key in div_em_specs:
                div_em_specs[key] = div_em_specs[key] / ny
            else:
                div_em_specs[key] = 0.0

        self.draw_array(em_specs=div_em_specs, **self.params)

        # connect row resistors
        port_wires = [[], [], []]
        for row_idx in range(ny):
            for col_idx in range(nx - 1):
                ports_l = self.get_res_ports(row_idx, col_idx)
                ports_r = self.get_res_ports(row_idx, col_idx + 1)
                con_par = (col_idx + row_idx) % 2
                mid_wire = self.connect_wires([ports_l[con_par], ports_r[con_par]])
                if col_idx == 0:
                    port_wires[0].append(ports_l[1 - con_par])
                if col_idx == nx - 2:
                    port_wires[2].append(ports_r[1 - con_par])
                if col_idx == (nx // 2) - 1:
                    port_wires[1].append(mid_wire[0])

        lay_offset = self.bot_layer_id
        last_dir = 'x'
        for lay_idx in range(1, len(self.w_tracks)):
            cur_lay = lay_idx + lay_offset
            cur_w = self.w_tracks[lay_idx]
            cur_dir = self.grid.get_direction(cur_lay)
            if cur_dir != last_dir:
                # layer direction is orthogonal
                if cur_dir == 'y':
                    # connect all horizontal wires in last layer to one vertical wire
                    for warrs_idx in range(3):
                        cur_warrs = port_wires[warrs_idx]
                        tidx = self.grid.coord_to_nearest_track(cur_lay, cur_warrs[0].middle, half_track=True)
                        tid = TrackID(cur_lay, tidx, width=cur_w)
                        port_wires[warrs_idx] = [self.connect_to_tracks(cur_warrs, tid)]
                else:
                    # draw one horizontal wire in middle of each row, then connect last vertical wire to it
                    # this way we distribute currents evenly.
                    cur_p = self.num_tracks[lay_idx]
                    # relative base index.  Round down if we have half-integer number of tracks
                    base_idx_rel = (int(round(cur_p * 2)) // 2 - 1) / 2
                    base_idx = self.get_abs_track_index(cur_lay, 0, base_idx_rel)
                    tid = TrackID(cur_lay, base_idx, width=cur_w, num=ny, pitch=cur_p)
                    for warrs_idx in range(3):
                        port_wires[warrs_idx] = self.connect_to_tracks(port_wires[warrs_idx], tid, min_len_mode=0)
            else:
                # layer direction is the same.  Strap wires to current layer.
                for warrs_idx in range(3):
                    cur_warrs = port_wires[warrs_idx]
                    new_warrs = [self.strap_wires(warr, cur_lay, tr_w_list=[cur_w], min_len_mode_list=[0])
                                 for warr in cur_warrs]
                    port_wires[warrs_idx] = new_warrs

            last_dir = cur_dir

        self.add_pin('inp', port_wires[0], show=show_pins)
        self.add_pin('inn', port_wires[2], show=show_pins)
        self.add_pin('incm', port_wires[1], show=show_pins)


class Termination(TemplateBase):
    """An template for creating termination resistors.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    **kwargs :
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(Termination, self).__init__(temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : Dict[str, Any]
            dictionary of default parameter values.
        """
        return dict(
            nx=2,
            ny=1,
            ext_dir='',
            res_type='reference',
            grid_type='standard',
            em_specs={},
            show_pins=True,
        )

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            l='unit resistor length, in meters.',
            w='unit resistor width, in meters.',
            sub_lch='substrate contact channel length.',
            sub_w='substrate contact width. Set to 0 to disable drawing substrate contact.',
            sub_type='the substrate type.',
            threshold='the substrate threshold flavor.',
            nx='number of resistors in a row.  Must be even.',
            ny='number of resistors in a column.',
            res_type='the resistor type.',
            grid_type='the resistor routing grid type.',
            em_specs='EM specifications for the termination network.',
            ext_dir='resistor core extension direction.',
            show_pins='True to show pins.',
        )

    def draw_layout(self):
        # type: () -> None

        res_params = self.params.copy()
        res_type = res_params['res_type']
        grid_type = self.params['grid_type']
        sub_lch = res_params.pop('sub_lch')
        sub_w = res_params.pop('sub_w')
        sub_type = self.params['sub_type']
        show_pins = self.params['show_pins']

        # force TerminationCore to be quantized
        top_layer = ResArrayBase.get_top_layer(self.grid.tech_info, grid_type=grid_type) + 1
        res_params['top_layer'] = top_layer

        res_master = self.new_template(params=res_params, temp_cls=TerminationCore)
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
                threshold=self.params['threshold'],
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

            bot_inst = self.add_instance(sub_master, inst_name='XBSUB', loc=(sub_x, 0), unit_mode=True)
            res_inst = self.add_instance(res_master, inst_name='XRES', loc=(0, ny_shift * h_pitch), unit_mode=True)
            top_yo = (ny_arr + 2 * ny_shift) * h_pitch
            top_inst = self.add_instance(sub_master, inst_name='XTSUB', loc=(sub_x, top_yo),
                                         orient='MX', unit_mode=True)

            # connect implant layers of resistor array and substrate contact together
            for lay in self.grid.tech_info.get_implant_layers(sub_type, res_type=res_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            self.reexport(bot_inst.get_port(port_name), show=show_pins)
            self.reexport(top_inst.get_port(port_name), show=show_pins)
            self.size = top_layer, nx_arr, ny_arr + 2 * ny_shift
            self.array_box = bot_inst.array_box.merge(top_inst.array_box)
            self.add_cell_boundary(self.bound_box)

            for port_name in res_inst.port_names_iter():
                self.reexport(res_inst.get_port(port_name), show=show_pins)

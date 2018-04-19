# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Dict, Any, Set

import yaml

from bag.core import BagProject
from bag.layout.routing import TrackManager

from abs_templates_ec.analog_core.base import AnalogBase, AnalogBaseInfo

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class VCOCore(AnalogBase):
    """A VCO Core.

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
        AnalogBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        # type: () -> Dict[str, Any]
        return self._sch_params

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            top_layer=None,
            end_mode=15,
            guard_ring_nf=0,
            options=None,
            show_pins=True,
        )

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            seg_dict='number of segments dictionary.',
            stack_dict='stack number dictionary.',
            fg_duml='Number of left edge dummy fingers.',
            fg_dumr='Number of right edge dummy fingers.',
            tr_widths='Track width dictionary.',
            tr_spaces='Track spacing dictionary.',
            top_layer='Top layer ID',
            end_mode='The AnalogBase end_mode flag.',
            guard_ring_nf='Number of guard ring fingers.',
            options='other AnalogBase options',
            show_pins='True to create pin labels.',
        )

    def draw_layout(self):
        lch = self.params['lch']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        w_dict = self.params['w_dict']
        th_dict = self.params['th_dict']
        seg_dict = self.params['seg_dict']
        stack_dict = self.params['stack_dict']
        fg_duml = self.params['fg_duml']
        fg_dumr = self.params['fg_dumr']
        tr_widths = self.params['tr_widths']
        tr_spaces = self.params['tr_spaces']
        top_layer = self.params['top_layer']
        end_mode = self.params['end_mode']
        guard_ring_nf = self.params['guard_ring_nf']
        options = self.params['options']
        show_pins = self.params['show_pins']

        if options is None:
            options = {}

        seg_gm = seg_dict['gm']
        seg_tail = seg_dict['tail']
        stack_gm = stack_dict['gm']
        stack_tail = stack_dict['tail']

        if seg_gm % 2 != 0 or seg_tail % 2 != 0:
            raise ValueError('seg_gm and seg_tail must be even')

        fg_gm = seg_gm * stack_gm
        fg_tail = seg_tail * stack_tail

        # get fg_sep, make sure it is even
        info = AnalogBaseInfo(self.grid, lch, guard_ring_nf, top_layer=top_layer, end_mode=end_mode)
        fg_sep = info.min_fg_sep
        fg_sep = -(-fg_sep // 2) * 2

        # get number of fingers
        fg_single = max(fg_gm, fg_tail)
        fg_tot = fg_duml + fg_dumr + 2 * fg_single + fg_sep

        # get row information
        nw_list = [w_dict['tail'], w_dict['gm']]
        nth_list = [th_dict['tail'], th_dict['gm']]
        n_orientations = ['R0', 'R0']
        pw_list = pth_list = p_orientations = []

        # get track manager and wire names
        tr_manager = TrackManager(self.grid, tr_widths, tr_spaces, half_space=True)
        wire_names = dict(
            nch=[
                dict(g=['bias'],
                     ds2=['tail']),
                dict(g2=['out', 'out'],
                     ds2=['out', 'out']),
            ],
            pch=[],
        )
        # draw base
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list, nth_list, pw_list, pth_list,
                       tr_manager=tr_manager, wire_names=wire_names,
                       n_orientations=n_orientations, p_orientations=p_orientations,
                       guard_ring_nf=guard_ring_nf, top_layer=top_layer, options=options)

        # draw transistors
        col_taill = fg_duml + fg_single - fg_tail
        col_gml = fg_duml + fg_single - fg_gm
        col_gmr = col_tailr = fg_duml + fg_single + fg_sep
        taill = self.draw_mos_conn('nch', 0, col_taill, fg_tail, 2, 0,
                                   s_net='tail', d_net='', stack=stack_tail)
        tailr = self.draw_mos_conn('nch', 0, col_tailr, fg_tail, 2, 0,
                                   s_net='tail', d_net='', stack=stack_tail)
        gml = self.draw_mos_conn('nch', 1, col_gml, fg_gm, 0, 2,
                                 s_net='tail', d_net='outp', stack=stack_gm)
        gmr = self.draw_mos_conn('nch', 1, col_gmr, fg_gm, 0, 2,
                                 s_net='tail', d_net='outn', stack=stack_gm)

        # draw connections
        # VSS
        self.connect_to_substrate('ptap', [taill['d'], tailr['d']])
        # tail
        tail_tid = self.get_wire_id('nch', 0, 'ds2', wire_name='tail')
        self.connect_to_tracks([taill['s'], tailr['s'], gml['s'], gmr['s']], tail_tid)
        # bias
        bias_tid = self.get_wire_id('nch', 0, 'g', wire_name='bias')
        bias = self.connect_to_tracks([taill['g'], tailr['g']], bias_tid)
        # input differential pair
        outn_tid = self.get_wire_id('nch', 1, 'g2', wire_name='out', wire_idx=0)
        outp_tid = self.get_wire_id('nch', 1, 'g2', wire_name='out', wire_idx=1)
        outp_g, outn_g = self.connect_differential_tracks(gmr['g'], gml['g'], outn_tid.layer_id,
                                                          outp_tid.base_index, outn_tid.base_index,
                                                          width=outp_tid.width)
        # output differential pair
        outn_tid = self.get_wire_id('nch', 1, 'ds2', wire_name='out', wire_idx=0)
        outp_tid = self.get_wire_id('nch', 1, 'ds2', wire_name='out', wire_idx=1)
        outp_d, outn_d = self.connect_differential_tracks(gml['d'], gmr['d'], outn_tid.layer_id,
                                                          outp_tid.base_index, outn_tid.base_index,
                                                          width=outp_tid.width)

        # fill dummies
        vss, vdd = self.fill_dummy()

        # add pins
        self.add_pin('VSS', vss, show=show_pins)
        self.add_pin('bias', bias, show=show_pins)
        self.add_pin('outp', outp_g, label='outp:', show=show_pins)
        self.add_pin('outn', outn_g, label='outn:', show=show_pins)
        self.add_pin('outp', outp_d, label='outp:', show=show_pins)
        self.add_pin('outn', outn_d, label='outn:', show=show_pins)

        # compute schematic parameters
        self._sch_params = dict(
            lch=lch,
            w_dict=w_dict,
            th_dict=th_dict,
            seg_dict=seg_dict,
            stack_dict=stack_dict,
            dum_info=self.get_sch_dummy_info(),
        )


if __name__ == '__main__':
    with open('specs_test/vco_core.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    bprj.generate_cell(block_specs, VCOCore, gen_sch=False, run_lvs=False, use_cybagoa=True)
    # bprj.generate_cell(block_specs, VCOCore, gen_sch=True, run_lvs=False, use_cybagoa=True)

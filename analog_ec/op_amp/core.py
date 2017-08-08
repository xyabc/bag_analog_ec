# -*- coding: utf-8 -*-

"""This package contain layout classes for differential amplifiers."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from typing import Dict, Any, Set

from bag.layout.template import TemplateDB
from bag.layout.routing import TrackID, TrackManager

from abs_templates_ec.analog_core import AnalogBase


class OpAmpTwoStage(AnalogBase):
    """A differential amplifier with diode load/positive feedback.

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
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(OpAmpTwoStage, self).__init__(temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            seg_dict='NMOS/PMOS number of segments dictionary.',
            stack_dict='NMOS/PMOS stack parameter dictionary.',
            ndum='Number of left/right dummy fingers.',
            min_fg_sep='number of fingers that separate transistors.',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            show_pins='True to create pin labels.',
            tr_widths='signal wire width dictionary.',
            tr_spaces='signal wire space dictionary.',
        )

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        # type: () -> None

        lch = self.params['lch']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        w_dict = self.params['w_dict']
        th_dict = self.params['th_dict']
        seg_dict = self.params['seg_dict']
        stack_dict = self.params['stack_dict']
        ndum = self.params['ndum']
        tr_widths = self.params['tr_widths']
        tr_spaces = self.params['tr_spaces']
        show_pins = self.params['show_pins']
        guard_ring_nf = self.params['guard_ring_nf']
        min_fg_sep = self.params['min_fg_sep']

        # calculate total number of fingers
        seg_tail1 = seg_dict['tail1']
        seg_tail2 = seg_dict['tail2']
        seg_tailcm = seg_dict['tailcm']
        seg_in = seg_dict['in']
        seg_ref = seg_dict['ref']
        seg_diode1 = seg_dict['diode1']
        seg_ngm1 = seg_dict['ngm1']
        seg_diode2 = seg_dict['diode2']
        seg_ngm2 = seg_dict['ngm2']

        stack_tail = stack_dict['tail']
        stack_in = stack_dict['in']
        stack_diode = stack_dict['diode']
        stack_ngm = stack_dict['ngm']

        fg_tail1 = seg_tail1 * stack_tail
        fg_tail2 = seg_tail2 * stack_tail
        fg_tailcm = seg_tailcm * stack_tail
        fg_in = seg_in * stack_in
        fg_diode1 = seg_diode1 * stack_diode
        fg_ngm1 = seg_ngm1 * stack_ngm
        fg_diode2 = seg_diode2 * stack_diode
        fg_ngm2 = seg_ngm2 * stack_ngm
        fg_ref = seg_ref * stack_in

        fg_load = fg_diode1 + fg_ngm1
        fg_in2 = fg_diode2 + fg_ngm2
        fg_bias2 = fg_tail2 + fg_tailcm

        # error checking
        if fg_tail1 != fg_in:
            raise ValueError('This template assumes fg_tail = fg_in')
        if stack_tail % stack_in != 0 and stack_in % stack_tail != 0:
            raise ValueError('one of stack_tail/stack_in must divide the other.')
        if stack_ngm % stack_in != 0 and stack_in % stack_ngm != 0:
            raise ValueError('one of stack_ngm/stack_in must divide the other.')

        fg_single1 = max(fg_in, fg_load)
        fg_single2 = max(fg_bias2, fg_in2)
        fg_tot = 2 * (fg_single1 + fg_single2 + ndum) + 4 * min_fg_sep + fg_ref
        ndum_tail = fg_tot - 2 * fg_in - 2 * fg_bias2 - fg_ref
        ndum_in = fg_tot - 2 * fg_in - fg_ref - 6
        ndum_load = fg_tot - 2 * fg_load - 2 * fg_in2 - 4

        # get width/threshold/orientation info
        nw_list = [w_dict['load']]
        nth_list = [th_dict['load']]
        n_orientations = ['MX']
        pw_list = [w_dict['in'], w_dict['tail']]
        pth_list = [th_dict['in'], th_dict['tail']]
        p_orientations = ['MX', 'MX']

        # get tracks information
        tr_manager = TrackManager(self.grid, tr_widths, tr_spaces)
        pg_tracks, pds_tracks, ng_tracks = [], [], []
        hm_layer = self.get_mos_conn_layer(self.grid.tech_info) + 1
        vm_layer = hm_layer + 1

        # allocate tracks for outputs
        offset = tr_manager.get_space(hm_layer, ('bias', 'out'))
        num_ng, ng_loc = tr_manager.place_wires(hm_layer, ['out', 'out'], start_idx=offset)
        ng_tracks.append(offset + num_ng)
        nds_tracks = [0]
        # allocate tracks for gm tail + bias
        offset = tr_manager.get_space(hm_layer, ('in', 'tail'))
        num_nout, nout_loc = tr_manager.place_wires(hm_layer, ['tail', 'bias'], start_idx=offset)
        pds_tracks.append(offset + num_nout)
        # allocate tracks for inputs
        num_in, in_loc = tr_manager.place_wires(hm_layer, ['in'] * 4)
        pg_tracks.append(num_in)
        # allocate tracks for tail + tail/input space
        num_tail, tail_loc = tr_manager.place_wires(hm_layer, ['tail'])
        sp_tail_in = tr_manager.get_space(hm_layer, ('tail', 'in'))
        pds_tracks.append(num_tail + sp_tail_in)
        # allocate tracks for bias + bias/tail space
        num_bias, bias_loc = tr_manager.place_wires(hm_layer, ['bias', 'bias'])
        sp_bias_tail = tr_manager.get_space(hm_layer, ('bias', 'tail'))
        pg_tracks.append(num_bias + sp_bias_tail)

        # draw base
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list, nth_list, pw_list, pth_list,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks, pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       n_orientations=n_orientations, p_orientations=p_orientations, guard_ring_nf=guard_ring_nf)

        # draw stage1 transistors
        col_left = ndum + fg_single2 + fg_single1 + min_fg_sep
        col_right = col_left + 2 * min_fg_sep + fg_ref
        diode1l = self.draw_mos_conn('nch', 0, col_left - fg_load, fg_diode1, 2, 0, stack=stack_diode)
        ngm1l = self.draw_mos_conn('nch', 0, col_left - fg_ngm1, fg_ngm1, 2, 0, stack=stack_ngm)
        ngm1r = self.draw_mos_conn('nch', 0, col_right, fg_ngm1, 2, 0, stack=stack_ngm)
        diode1r = self.draw_mos_conn('nch', 0, col_right + fg_ngm1, fg_diode1, 2, 0, stack=stack_diode)
        inl = self.draw_mos_conn('pch', 0, col_left - fg_in, fg_in, 0, 2, stack=stack_in)
        inm = self.draw_mos_conn('pch', 0, col_left + min_fg_sep, fg_ref, 0, 2, stack=stack_in)
        inr = self.draw_mos_conn('pch', 0, col_right, fg_in, 0, 2, stack=stack_in)
        bias1l = self.draw_mos_conn('pch', 1, col_left - fg_tail1, fg_tail1, 2, 0, stack=stack_tail)
        biasm = self.draw_mos_conn('pch', 1, col_left + min_fg_sep, fg_ref, 2, 0, stack=stack_tail)
        bias1r = self.draw_mos_conn('pch', 1, col_right, fg_tail1, 2, 0, stack=stack_tail)
        # draw stage2 transistors
        col_left = ndum + fg_single2
        col_right += fg_single1 + min_fg_sep
        diode2l = self.draw_mos_conn('nch', 0, col_left - fg_in2, fg_diode2, 0, 2, stack=stack_diode)
        ngm2l = self.draw_mos_conn('nch', 0, col_left - fg_ngm2, fg_ngm2, 0, 2, stack=stack_ngm)
        ngm2r = self.draw_mos_conn('nch', 0, col_right, fg_ngm2, 0, 2, stack=stack_ngm)
        diode2r = self.draw_mos_conn('nch', 0, col_right + fg_ngm2, fg_diode2, 0, 2, stack=stack_diode)
        cm2l = self.draw_mos_conn('pch', 1, col_left - fg_bias2, fg_tailcm, 2, 0, stack=stack_tail)
        bias2l = self.draw_mos_conn('pch', 1, col_left - fg_tail2, fg_tail2, 2, 0, stack=stack_tail)
        bias2r = self.draw_mos_conn('pch', 1, col_right, fg_tail2, 2, 0, stack=stack_tail)
        cm2r = self.draw_mos_conn('pch', 1, col_right + fg_tail2, fg_tailcm, 2, 0, stack=stack_tail)

        # draw connections
        # connect VDD/VSS
        self.connect_to_substrate('ntap', [bias1l['s'], biasm['s'], bias1r['s'], cm2l['s'], cm2r['s'],
                                           bias2l['s'], bias2r['s']])
        self.connect_to_substrate('ptap', [diode1l['d'], ngm1l['d'], ngm1r['d'], diode1r['d'],
                                           diode2l['s'], ngm2l['s'], ngm2r['s'], diode2r['s']])

        # connect bias/tail wires
        w_bias = tr_manager.get_width(hm_layer, 'bias')
        w_tail = tr_manager.get_width(hm_layer, 'tail')
        cm_tidx = self.get_track_index('pch', 1, 'g', bias_loc[0])
        bias1_tidx = self.get_track_index('pch', 1, 'g', bias_loc[1])
        tail1_tidx = self.get_track_index('pch', 1, 'ds', tail_loc[0])
        tail2_tidx = self.get_track_index('pch', 0, 'ds', nout_loc[0])
        bias2_tid = self.make_track_id('pch', 0, 'ds', nout_loc[1], width=w_bias)

        self.connect_differential_tracks([inl['d'], inr['d'], bias1l['d'], bias1r['d']], [biasm['d'], inm['d']],
                                         hm_layer, tail2_tidx, tail1_tidx, width=w_tail)
        bias2 = self.connect_to_tracks(inm['s'], bias2_tid)

        bias1_warrs = [bias1l['g'], biasm['g'], bias1r['g'], bias2l['g'], bias2r['g']]
        cm_warrs = [cm2l['g'], cm2r['g']]
        bias1, cmbias = self.connect_differential_tracks(bias1_warrs, cm_warrs, hm_layer, bias1_tidx, cm_tidx,
                                                         width=w_bias)
        mid_tid = self.grid.coord_to_nearest_track(vm_layer, bias1.middle)
        bias_vtid = TrackID(vm_layer, mid_tid, width=tr_manager.get_width(vm_layer, 'bias'))
        bias = self.connect_to_tracks([bias1, bias2], bias_vtid)

        # connect middle wires
        w_out = tr_manager.get_width(hm_layer, 'out')
        midp_tidx = self.get_track_index('nch', 0, 'g', ng_loc[0])
        midn_tidx = self.get_track_index('nch', 0, 'g', ng_loc[1])
        midp_warrs = [inr['s'], ngm1r['s'], diode1r['s'], diode1r['g'], ngm1l['g'], diode2r['g'], ngm2r['g']]
        midn_warrs = [inl['s'], ngm1l['s'], diode1l['s'], diode1l['g'], ngm1r['g'], diode2l['g'], ngm2l['g']]
        midp, midn = self.connect_differential_tracks(midp_warrs, midn_warrs, hm_layer,
                                                      midp_tidx, midn_tidx, width=w_out)

        # connect inputs
        w_in = tr_manager.get_width(hm_layer, 'in')
        inc1_tidx = self.get_track_index('pch', 0, 'g', in_loc[0])
        inp_tidx = self.get_track_index('pch', 0, 'g', in_loc[1])
        inn_tidx = self.get_track_index('pch', 0, 'g', in_loc[2])
        inc2_tidx = self.get_track_index('pch', 0, 'g', in_loc[3])
        inc1_warrs = inc2_warrs = inm['g']
        inp_warrs = inl['g']
        inn_warrs = inr['g']
        inc1, inp, inn, inc2 = self.connect_matching_tracks([inc1_warrs, inp_warrs, inn_warrs, inc2_warrs],
                                                            hm_layer, [inc1_tidx, inp_tidx, inn_tidx, inc2_tidx],
                                                            width=w_in)

        # connect outputs
        out_tidx = (int((inp_tidx + inn_tidx) * 2) // 2) / 2
        outp = self.connect_to_tracks([diode2l['d'], ngm2l['d'], bias2l['d'], cm2l['d']],
                                      TrackID(hm_layer, out_tidx, width=w_out))
        outn = self.connect_to_tracks([diode2r['d'], ngm2r['d'], bias2r['d'], cm2r['d']],
                                      TrackID(hm_layer, out_tidx, width=w_out))

        # fill dummies
        vss_warrs, vdd_warrs = self.fill_dummy()

        # add pins
        self.add_pin('ref', [inc1, inc2], show=show_pins)
        self.add_pin('inp', inp, show=show_pins)
        self.add_pin('inn', inn, show=show_pins)
        self.add_pin('bias', bias, show=show_pins)
        self.add_pin('cmbias', cmbias, show=show_pins)
        self.add_pin('midp', midp, show=show_pins)
        self.add_pin('midn', midn, show=show_pins)
        self.add_pin('outp', outp, show=show_pins)
        self.add_pin('outn', outn, show=show_pins)
        self.add_pin('VSS', vss_warrs, show=show_pins)
        self.add_pin('VDD', vdd_warrs, show=show_pins)

        # compute schematic parameters
        self._sch_params = dict(
            lch=lch,
            w_dict=w_dict,
            th_dict=th_dict,
            seg_dict=seg_dict,
            stack_dict=stack_dict,
            dum_dict={'tail': ndum_tail, 'in': ndum_in, 'load': ndum_load},
        )

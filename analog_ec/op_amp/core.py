# -*- coding: utf-8 -*-

"""This package contain layout classes for differential amplifiers."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from typing import Dict, Any, Set

from bag.layout.template import TemplateDB
from bag.layout.routing import TrackManager

from abs_templates_ec.analog_core import AnalogBase


class DiffAmpDiodeLoadPFB(AnalogBase):
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
        super(DiffAmpDiodeLoadPFB, self).__init__(temp_db, lib_name, params, used_names, **kwargs)

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
            tr_widths='signal wire width dictionary.',
            tr_spaces='signal wire space dictionary.',
            show_pins='True to create pin labels.',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            min_fg_sep='number of fingers that separate transistors.'
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
        seg_tail = seg_dict['tail']
        seg_in = seg_dict['in']
        seg_ref = seg_dict['ref']
        seg_diode = seg_dict['diode']
        seg_ngm = seg_dict['ngm']

        stack_tail = stack_dict['tail']
        stack_in = stack_dict['in']
        stack_diode = stack_dict['diode']
        stack_ngm = stack_dict['ngm']

        fg_tail = seg_tail * stack_tail
        fg_in = seg_in * stack_in
        fg_diode = seg_diode * stack_diode
        fg_ngm = seg_ngm * stack_ngm
        fg_load = fg_diode + fg_ngm
        fg_ref = seg_ref * stack_in

        # error checking
        if fg_tail != fg_in:
            raise ValueError('This template assumes fg_tail = fg_in')
        if stack_tail % stack_in != 0 and stack_in % stack_tail != 0:
            raise ValueError('one of stack_tail/stack_in must divide the other.')
        if stack_ngm % stack_in != 0 and stack_in % stack_ngm != 0:
            raise ValueError('one of stack_ngm/stack_in must divide the other.')

        fg_single = max(fg_in, fg_load)
        fg_tot = 2 * (fg_single + ndum) + 2 * min_fg_sep + fg_ref

        # get width/threshold/orientation info
        nw_list = [w_dict['load']]
        nth_list = [th_dict['load']]
        n_orientations = ['MX']
        pw_list = [w_dict['in'], w_dict['tail']]
        pth_list = [th_dict['in'], th_dict['tail']]
        p_orientations = ['MX', 'MX']

        # get tracks information
        tr_manager = TrackManager(tr_widths, tr_spaces)
        pg_tracks, pds_tracks, ng_tracks = [], [], []
        hm_layer = self.get_mos_conn_layer(self.grid.tech_info) + 1

        # allocate tracks for outputs
        offset = tr_manager.get_space(hm_layer, ('bias', 'out'))
        num_pg, pg_loc = tr_manager.place_wires(hm_layer, ['outp', 'outn'], start_idx=offset)
        ng_tracks.append(offset + num_pg)
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
        num_bias, bias_loc = tr_manager.place_wires(hm_layer, ['bias'])
        sp_bias_tail = tr_manager.get_space(hm_layer, ('bias', 'tail'))
        pg_tracks.append(num_bias + sp_bias_tail)

        # draw base
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list, nth_list, pw_list, pth_list,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks, pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       n_orientations=n_orientations, p_orientations=p_orientations, guard_ring_nf=guard_ring_nf)

        # draw transistors
        col_right = ndum + fg_single + 2 * min_fg_sep + fg_in
        load_start = ndum + fg_single - fg_load
        diodel = self.draw_mos_conn('nch', 0, load_start, fg_diode, 2, 0, stack=stack_diode)
        ngml = self.draw_mos_conn('nch', 0, load_start + fg_diode, fg_ngm, 2, 0, stack=stack_ngm)
        ngmr = self.draw_mos_conn('nch', 0, col_right, fg_ngm, 2, 0, stack=stack_ngm)
        diodel = self.draw_mos_conn('nch', 0, col_right + fg_ngm, fg_diode, 2, 0, stack=stack_diode)
        inl = self.draw_mos_conn('pch', 0, ndum + fg_single - fg_in, fg_in, 0, 2, stack=stack_in)
        inm = self.draw_mos_conn('pch', 0, ndum + fg_single + min_fg_sep, fg_ref, 0, 2, stack=stack_in)
        inr = self.draw_mos_conn('pch', 0, col_right, fg_in, 0, 2, stack=stack_in)
        biasl = self.draw_mos_conn('pch', 1, ndum + fg_single - fg_tail, fg_tail, 2, 0, stack=stack_tail)
        biasm = self.draw_mos_conn('pch', 1, ndum + fg_single + min_fg_sep, fg_ref, 2, 0, stack=stack_tail)
        biasr = self.draw_mos_conn('pch', 1, col_right, fg_tail, 2, 0, stack=stack_tail)

        # fill dummies
        vss_warrs, vdd_warrs = self.fill_dummy()

        self.add_pin('VSS', vss_warrs, show=show_pins)
        self.add_pin('VDD', vdd_warrs, show=show_pins)

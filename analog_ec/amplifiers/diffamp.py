# -*- coding: utf-8 -*-

"""This package contain layout classes for differential amplifiers."""

from typing import Dict, Any, Set

from bag.layout.template import TemplateDB
from bag.layout.routing import TrackID, TrackManager

from abs_templates_ec.analog_core import AnalogBaseInfo, AnalogBase


class DiffAmpSelfBiased(AnalogBase):
    """A self-biased differential amplifier.

    This block has single-ended output.

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
        AnalogBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
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
            ndum='Number of left/right dummy fingers.',
            tr_widths='signal wire width dictionary.',
            tr_spaces='signal wire space dictionary.',
            show_pins='True to create pin labels.',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            top_layer='The AnalogBase top layer.',
        )

    @classmethod
    def get_default_param_values(cls):
        return dict(
            show_pins=True,
            guard_ring_nf=0,
            top_layer=None,
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
        ndum = self.params['ndum']
        tr_widths = self.params['tr_widths']
        tr_spaces = self.params['tr_spaces']
        show_pins = self.params['show_pins']
        guard_ring_nf = self.params['guard_ring_nf']
        top_layer = self.params['top_layer']

        ana_info = AnalogBaseInfo(self.grid, lch, guard_ring_nf, top_layer=top_layer)
        min_fg_sep = ana_info.min_fg_sep

        # calculate total number of fingers
        seg_ptail = seg_dict['ptail']
        seg_ntail = seg_dict['ntail']
        seg_pin = seg_dict['pin']
        seg_nin = seg_dict['nin']

        fg_ptail = seg_ptail
        fg_ntail = seg_ntail
        fg_pin = seg_pin
        fg_nin = seg_nin

        # error checking
        if fg_pin % 2 != 0 or fg_nin % 2 != 0 or fg_ptail % 2 != 0 or fg_ntail % 2 != 0:
            raise ValueError('Only even number of fingers are supported.')

        fg_single_in = max(fg_pin, fg_nin)
        fg_single = max(fg_ptail, fg_ntail, fg_pin, fg_nin)
        in_mid_idx = ndum + fg_single - fg_single_in // 2
        fg_tot = 2 * (fg_single + ndum) + min_fg_sep
        ndum_ptail = ndum + fg_single - fg_ptail
        ndum_ntail = ndum + fg_single - fg_ntail
        ndum_pin = in_mid_idx - fg_pin // 2
        ndum_nin = in_mid_idx - fg_nin // 2

        # get width/threshold/orientation info
        nw_list = [w_dict['ntail'], w_dict['nin']]
        nth_list = [th_dict['ntail'], th_dict['nin']]
        n_orientations = ['MX', 'MX']
        pw_list = [w_dict['pin'], w_dict['ptail']]
        pth_list = [th_dict['pin'], th_dict['ptail']]
        p_orientations = ['R0', 'R0']

        # get tracks information
        tr_manager = TrackManager(self.grid, tr_widths, tr_spaces)
        hm_layer = self.mos_conn_layer + 1
        vm_layer = hm_layer + 1

        # allocate tracks for outputs
        ntr_io, _ = tr_manager.place_wires(hm_layer, ['out', 'in', 'in', 'out'])
        if isinstance(ntr_io, float):
            ntr_io = int(round(ntr_io + 0.5))
        tr_w_bias = tr_manager.get_width(hm_layer, 'bias')
        ng_tracks = [tr_w_bias, ntr_io // 2]
        pg_tracks = [ntr_io // 2, tr_w_bias]
        nds_tracks = [tr_w_bias, 0]
        pds_tracks = [0, tr_w_bias]
        # draw base
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list, nth_list, pw_list, pth_list,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks, pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       n_orientations=n_orientations, p_orientations=p_orientations, guard_ring_nf=guard_ring_nf,
                       top_layer=top_layer)

        # draw transistors
        ntaill = self.draw_mos_conn('nch', 0, ndum_ntail, fg_ntail, 0, 2,
                                    s_net='VSS', d_net='tailn')
        ntailr = self.draw_mos_conn('nch', 0, fg_tot - ndum_ntail - fg_ntail, fg_ntail, 0, 2,
                                    s_net='VSS', d_net='tailn')
        ptaill = self.draw_mos_conn('pch', 1, ndum_ptail, fg_ptail, 2, 0,
                                    s_net='VDD', d_net='tailp')
        ptailr = self.draw_mos_conn('pch', 1, fg_tot - ndum_ptail - fg_ptail, fg_ptail, 2, 0,
                                    s_net='VDD', d_net='tailp')
        if (ndum_nin - ndum_ntail) % 2 == 1:
            tail_nin_port, out_nin_port = 'd', 's'
            sdir, ddir = 2, 0
            s_netl, s_netr, d_netl, d_netr = 'outn', 'outp', 'tailn', 'tailn'
        else:
            tail_nin_port, out_nin_port = 's', 'd'
            sdir, ddir = 0, 2
            s_netl, s_netr, d_netl, d_netr = 'tailn', 'tailn', 'outn', 'outp'
        ninl = self.draw_mos_conn('nch', 1, ndum_nin, fg_nin, sdir, ddir,
                                  s_net=s_netl, d_net=d_netl)
        ninr = self.draw_mos_conn('nch', 1, fg_tot - ndum_nin - fg_nin, fg_nin, sdir, ddir,
                                  s_net=s_netr, d_net=d_netr)
        if (ndum_pin - ndum_ntail) % 2 == 1:
            tail_pin_port, out_pin_port = 'd', 's'
            sdir, ddir = 0, 2
            s_netl, s_netr, d_netl, d_netr = 'outn', 'outp', 'tailp', 'tailp'
        else:
            tail_pin_port, out_pin_port = 's', 'd'
            sdir, ddir = 2, 0
            s_netl, s_netr, d_netl, d_netr = 'tailp', 'tailp', 'outn', 'outp'
        pinl = self.draw_mos_conn('pch', 0, ndum_pin, fg_pin, sdir, ddir,
                                  s_net=s_netl, d_net=d_netl)
        pinr = self.draw_mos_conn('pch', 0, fg_tot - ndum_pin - fg_pin, fg_pin, sdir, ddir,
                                  s_net=s_netr, d_net=d_netr)

        # fill dummies
        vss_warrs, vdd_warrs = self.fill_dummy()

        """
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
        """
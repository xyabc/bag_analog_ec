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
            guard_ring_nf='Width of the guard ring, in number of fingers.  '
                          '0 to disable guard ring.',
            top_layer='The AnalogBase top layer.',
            tech_cls_name='Technology class name.',
        )

    @classmethod
    def get_default_param_values(cls):
        return dict(
            show_pins=True,
            guard_ring_nf=0,
            top_layer=None,
            tech_cls_name=None,
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
        tech_cls_name = self.params['tech_cls_name']

        if tech_cls_name is not None:
            self.set_tech_class(tech_cls_name)

        ana_info = AnalogBaseInfo(self.grid, lch, guard_ring_nf, top_layer=top_layer,
                                  tech_cls_name=tech_cls_name)
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
        if (fg_pin - fg_nin) % 4 != 0:
            raise ValueError('This code now only works if fg_pin and fg_nin differ by '
                             'multiples of 4.')

        fg_single_in = max(fg_pin, fg_nin)
        fg_single = max(fg_ptail, fg_ntail, fg_pin, fg_nin)
        in_mid_idx = ndum + fg_single - fg_single_in // 2
        fg_tot = 2 * (fg_single + ndum) + min_fg_sep
        ndum_pin = in_mid_idx - fg_pin // 2
        ndum_nin = in_mid_idx - fg_nin // 2
        if fg_ntail <= fg_nin:
            ndum_ntail = ndum_nin + fg_nin - fg_ntail
        else:
            ndum_ntail = min(ndum_nin, ndum + fg_single - fg_ntail)
        if fg_ptail <= fg_pin:
            ndum_ptail = ndum_pin + fg_pin - fg_ptail
        else:
            ndum_ptail = min(ndum_pin, ndum + fg_single - fg_ptail)

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

        # allocate tracks
        wire_names = dict(
            nch=[
                dict(g=['bias'],
                     ds=['tail']),
                dict(g=['in', 'out'],
                     ds=[]),
            ],
            pch=[
                dict(g=['in'],
                     ds=[]),
                dict(g=['bias'],
                     ds=['tail']),
            ],
        )

        # draw base
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list, nth_list, pw_list, pth_list,
                       tr_manager=tr_manager, wire_names=wire_names,
                       n_orientations=n_orientations, p_orientations=p_orientations,
                       guard_ring_nf=guard_ring_nf, top_layer=top_layer)

        # draw transistors
        ntaill = self.draw_mos_conn('nch', 0, ndum_ntail, fg_ntail, 2, 0,
                                    s_net='ntail', d_net='')
        ntailr = self.draw_mos_conn('nch', 0, fg_tot - ndum_ntail - fg_ntail, fg_ntail, 2, 0,
                                    s_net='ntail', d_net='')
        ptaill = self.draw_mos_conn('pch', 1, ndum_ptail, fg_ptail, 0, 2,
                                    s_net='ptail', d_net='')
        ptailr = self.draw_mos_conn('pch', 1, fg_tot - ndum_ptail - fg_ptail, fg_ptail, 0, 2,
                                    s_net='ptail', d_net='')
        if (ndum_nin - ndum_ntail) % 2 == 1:
            tail_nin_port, out_nin_port = 'd', 's'
            sdir, ddir = 2, 0
            s_netl, s_netr, d_netl, d_netr = 'outn', 'outp', 'ntail', 'ntail'
        else:
            tail_nin_port, out_nin_port = 's', 'd'
            sdir, ddir = 0, 2
            s_netl, s_netr, d_netl, d_netr = 'ntail', 'ntail', 'outn', 'outp'
        ninl = self.draw_mos_conn('nch', 1, ndum_nin, fg_nin, sdir, ddir,
                                  s_net=s_netl, d_net=d_netl)
        ninr = self.draw_mos_conn('nch', 1, fg_tot - ndum_nin - fg_nin, fg_nin, sdir, ddir,
                                  s_net=s_netr, d_net=d_netr)
        if (ndum_pin - ndum_ptail) % 2 == 1:
            tail_pin_port, out_pin_port = 'd', 's'
            sdir, ddir = 0, 2
            s_netl, s_netr, d_netl, d_netr = 'outn', 'outp', 'ptail', 'ptail'
        else:
            tail_pin_port, out_pin_port = 's', 'd'
            sdir, ddir = 2, 0
            s_netl, s_netr, d_netl, d_netr = 'ptail', 'ptail', 'outn', 'outp'
        pinl = self.draw_mos_conn('pch', 0, ndum_pin, fg_pin, sdir, ddir,
                                  s_net=s_netl, d_net=d_netl)
        pinr = self.draw_mos_conn('pch', 0, fg_tot - ndum_pin - fg_pin, fg_pin, sdir, ddir,
                                  s_net=s_netr, d_net=d_netr)

        # draw connections
        # VDD/VSS
        self.connect_to_substrate('ptap', [ntaill['d'], ntailr['d']])
        self.connect_to_substrate('ntap', [ptaill['d'], ptailr['d']])
        # NMOS/PMOS tail
        tail_tid = self.get_wire_id('nch', 0, 'ds', wire_name='tail')
        self.connect_to_tracks([ntaill['s'], ntailr['s'], ninl[tail_nin_port],
                                ninr[tail_nin_port]], tail_tid)
        tail_tid = self.get_wire_id('pch', 1, 'ds', wire_name='tail')
        self.connect_to_tracks([ptaill['s'], ptailr['s'], pinl[tail_pin_port],
                                pinr[tail_pin_port]], tail_tid)
        # NMOS/PMOS tail bias
        bn_tid = self.get_wire_id('nch', 0, 'g', wire_name='bias')
        bp_tid = self.get_wire_id('pch', 1, 'g', wire_name='bias')
        self.connect_to_tracks([ntaill['g'], ntailr['g'], ninl['d'], pinl['d']], bn_tid)
        self.connect_to_tracks([ptaill['g'], ptailr['g'], ninl['d'], pinl['d']], bp_tid)
        # input/output
        inn_tid = self.get_wire_id('nch', 1, 'g', wire_name='in')
        inp_tid = self.get_wire_id('pch', 0, 'g', wire_name='in')
        inp_idx = inp_tid.base_index
        inn_idx = inn_tid.base_index
        in_sum2 = int(round(2 * (inp_idx + inn_idx)))
        if in_sum2 % 2 == 1:
            # move inp_idx down so output is centered wrt inputs
            inp_idx -= 0.5
            in_sum2 -= 1
        out_tid = TrackID(hm_layer, in_sum2 / 4, width=tr_manager.get_width(hm_layer, 'out'))
        # connect input/output
        inp, inn = self.connect_differential_tracks([ninl['g'], pinl['g']], [ninr['g'], pinr['g']],
                                                    hm_layer, inp_idx, inn_idx, width=inn_tid.width)
        out = self.connect_to_tracks([ninr[out_nin_port], pinr[out_pin_port]],
                                     out_tid, min_len_mode=0)

        # fill dummies
        tr_w = tr_manager.get_width(hm_layer, 'sup')
        vss_warrs, vdd_warrs = self.fill_dummy(vdd_width=tr_w, vss_width=tr_w)

        # add pins
        self.add_pin('inp', inp, show=show_pins)
        self.add_pin('inn', inn, show=show_pins)
        self.add_pin('out', out, show=show_pins)
        self.add_pin('VSS', vss_warrs, show=show_pins)
        self.add_pin('VDD', vdd_warrs, show=show_pins)

        # compute schematic parameters
        self._sch_params = dict(
            lch=lch,
            w_dict=w_dict,
            th_dict=th_dict,
            seg_dict=seg_dict,
            dum_info=self.get_sch_dummy_info(),
        )

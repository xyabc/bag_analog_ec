# -*- coding: utf-8 -*-


import pprint

from bag.io import read_yaml

from ckt_dsn_ec.mos.core import MOSDBDiscrete
from ckt_dsn_ec.analog.amplifier.opamp_two_stage import OpAmpTwoStage


def run_main():
    interp_method = 'spline'
    w_list = [2]
    nch_conf_list = ['data/mos_char_nch_stack_w2_vbs/specs.yaml',
                     # 'data/mos_char_nch_stack/specs.yaml',
                     ]
    pch_conf_list = ['data/mos_char_pch_stack_w2_vbs/specs.yaml',
                     # 'data/mos_char_pch_stack/specs.yaml',
                     ]
    amp_specs_fname = 'dsn_specs/opamp_two_stage.yaml'

    amp_specs = read_yaml(amp_specs_fname)

    print('create transistor database')
    nch_db = MOSDBDiscrete(w_list, nch_conf_list, 1, method=interp_method, cfit_method='average')
    pch_db = MOSDBDiscrete(w_list, pch_conf_list, 1, method=interp_method, cfit_method='average')

    print('create design')
    dsn = OpAmpTwoStage(nch_db, pch_db)
    print('run design')
    dsn.design(**amp_specs)

    print('corners: ', nch_db.env_list)
    pprint.pprint(dsn.get_dsn_info(), width=120)


def run_test(method='linear'):
    w_list = [2]
    nch_conf_list = ['data/mos_char_nch_stack_w2_vbs/specs.yaml',
                     # 'data/mos_char_nch_stack/specs.yaml',
                     ]
    pch_conf_list = ['data/mos_char_pch_stack_w2_vbs/specs.yaml',
                     # 'data/mos_char_pch_stack/specs.yaml',
                     ]

    print('create transistor database')
    nch_db = MOSDBDiscrete(w_list, nch_conf_list, 1, method=method)
    pch_db = MOSDBDiscrete(w_list, pch_conf_list, 1, method=method)

    nch_db.env_list = ['ff_hot']
    pch_db.env_list = ['ff_hot']

    vdd = 0.9
    vin = vout = 0.45
    vtail = 0.6393
    vmid = 0.2617
    vbias = 0.6498
    vcm = 0.6486
    segi = 4
    segd = 2
    segn = 4
    segt = 2
    segc = 2

    pch_db.set_dsn_params(w=2, intent='ulvt', stack=4)
    in_params = pch_db.query(vbs=vdd-vtail, vds=vmid-vtail, vgs=vin-vtail)
    nch_db.set_dsn_params(w=2, intent='svt', stack=2)
    diode_params = nch_db.query(vbs=0, vds=vmid, vgs=vmid)
    nch_db.set_dsn_params(w=2, intent='svt', stack=4)
    ngm_params = nch_db.query(vbs=0, vds=vmid, vgs=vmid)

    pprint.pprint(in_params)

    gmi = in_params['gm']
    gdsi = in_params['gds']
    gmd = diode_params['gm']
    gdsd = diode_params['gds']
    gmn = ngm_params['gm']
    gdsn = ngm_params['gds']
    print('gmi = %.4g' % gmi)
    print('gdsi = %.4g' % gdsi)
    print('gmd = %.4g' % gmd)
    print('gdsd = %.4g' % gdsd)
    print('gmn = %.4g' % gmn)
    print('gdsn = %.4g' % gdsn)

    gain1 = segi * gmi / (segi * gdsi + segd * gdsd + segn * gdsn + segd * gmd - segn * gmn)
    print(gain1)

    nch_db.set_dsn_params(w=2, intent='svt', stack=2)
    diode_params = nch_db.query(vbs=0, vds=vout, vgs=vmid)
    nch_db.set_dsn_params(w=2, intent='svt', stack=4)
    ngm_params = nch_db.query(vbs=0, vds=vout, vgs=vmid)

    pch_db.set_dsn_params(w=2, intent='lvt', stack=4)
    tail_params = pch_db.query(vbs=0, vds=vout-vdd, vgs=vbias-vdd)
    cm_params = pch_db.query(vbs=0, vds=vout-vdd, vgs=vcm-vdd)

    gmd = diode_params['gm']
    gdsd = diode_params['gds']
    gmn = ngm_params['gm']
    gdsn = ngm_params['gds']
    gdst = tail_params['gds']
    gdsc = cm_params['gds']

    gain2_0 = (segn * gmn + segd * gmd) / (segn * gdsn + segd * gdsd + (segt + segc) * gdst)
    gain2_1 = (segn * gmn + segd * gmd) / (segn * gdsn + segd * gdsd + segt * gdst + segc * gdsc)

    print(gain2_0, gain2_1)
    print(gain1 * gain2_0, gain1 * gain2_1)

    return nch_db.get_function('ibias', 'ff_hot')

if __name__ == '__main__':
    run_main()
    # ibf = run_test(method='spline')

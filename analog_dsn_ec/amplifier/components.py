# -*- coding: utf-8 -*-

"""This package contain design methods/classes for components of an amplifier."""


class LoadDiodePFB(object):
    """A class that designs differential diode load with positive feedback."""

    def __init__(self, db_specs):
        self._specs = db_specs

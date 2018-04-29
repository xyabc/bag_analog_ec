# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject
from bag.layout.template import TemplateBase, CachedTemplate


class CacheTest(TemplateBase):
    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @classmethod
    def get_params_info(cls):
        return dict(
            cache_fname='the cache file name.',
        )

    def draw_layout(self):
        master = self.new_template(self.params, temp_cls=CachedTemplate)

        self.add_instance(master)
        self.set_size_from_bound_box(master.top_layer, master.bound_box)
        self.array_box = master.array_box

        for bbox in self.blockage_iter(4, self.bound_box):
            self.add_rect('M8', bbox, unit_mode=True)


if __name__ == '__main__':
    with open('specs_test/cache_test.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    bprj.generate_cell(block_specs, CacheTest, debug=True)

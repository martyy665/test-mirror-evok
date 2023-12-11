#!/usr/bin/python3
import sys
from typing import List, Union

import yaml

sys.path.append("/opt/unipi/os-configurator")
os_configurator = __import__("os-configurator")

BRAIN = "B1000"
E14DI14RO = "E14DI14RO"
E30DI = "E30DI"
E4AI4AO = "E4AI4AO"
E6DI8RO = "E6DI8RO"
E16DI14RO = "E16DI14RO"
E30RO = "E30RO"
E4AI4AO6DI = "E4AI4AO6DI"
E8DI8DO = ""
UNIPI11 = "UNIPI11"
UNIPI11LITE = "UNIPI11LITE"

E4AI4AO4DI5RO = E4AI4AO
E4AI4AO6DI5RO = E4AI4AO6DI


hw_data = {
    0x0103: [BRAIN],  # S103
    0x1103: [BRAIN],  # S103_E
    0x1203: [BRAIN],  # S103_I
    0x0203: [BRAIN, E8DI8DO],  # M103
    0x0303: [BRAIN, E16DI14RO],  # M203
    0x0403: [BRAIN, E30DI],  # M303
    0x0503: [BRAIN, E4AI4AO4DI5RO],  # M523
    0x0603: [BRAIN, E16DI14RO, E16DI14RO],  # L203
    0x0703: [BRAIN, E30RO, E30RO],  # L403
    0x0803: [BRAIN, E4AI4AO4DI5RO, E16DI14RO],  # L523
    0x0903: [BRAIN, E4AI4AO4DI5RO, E4AI4AO4DI5RO],  # L533
    0x0a03: [BRAIN],  # S103_G
    0x0b03: [BRAIN, E30RO],  # M403
    0x0c03: [BRAIN, E4AI4AO6DI5RO],  # M503
    # 0x0d03: [BRAIN],  # M603
    0x0e03: [BRAIN, E30DI, E30DI],  # L303
    0x0F03: [BRAIN, E4AI4AO6DI5RO, E14DI14RO],  # L503
    0x1003: [BRAIN, E4AI4AO6DI5RO, E4AI4AO6DI5RO],  # L513

    0x0107: [BRAIN],  # S107
    0x0707: [BRAIN],  # S117
    0x0a07: [BRAIN],  # S167
    0x0207: [E8DI8DO],  # S207
    0x0b07: [E8DI8DO],  # S227
    0x0307: [BRAIN, E16DI14RO],  # M207
    0x0407: [BRAIN, E4AI4AO4DI5RO],  # M527
    0x0507: [BRAIN, E16DI14RO, E16DI14RO],  # L207
    0x0607: [BRAIN, E4AI4AO4DI5RO, E16DI14RO],  # L527
    0x0807: [BRAIN, E16DI14RO],  # M267
    0x0907: [BRAIN, E4AI4AO4DI5RO],  # M567

    0x0001: [UNIPI11],  # UNIPI10
    0x0101: [UNIPI11],  # UNIPI11
    0x1101: [UNIPI11LITE],  # UNIPI11LITE
}


def generate_config(boards: List[str], defaults: Union[None, dict] = None):
    defaults = defaults if defaults is not None else dict()
    port = defaults.get('port', 502)
    hostname = defaults.get('hostname', '127.0.0.1')
    names = defaults.get('names', [i for i in range(1, len(boards)+1)])
    slave_ids = defaults.get('slave-ids', [i for i in range(1, len(boards)+1)])

    ret = {
        'hw_tree': {
            'LOCAL_TCP': {
                'type': 'MODBUSTCP',
                'hostname': hostname,
                'port': port,
                'devices': {},
            }
        }
    }

    for i in range(len(boards)):
        ret['hw_tree']['LOCAL_TCP']['devices'][names[i]] = {
            'slave-id': slave_ids[i],
            'model': boards[i]
        }
    return ret


def run():
    product_data = os_configurator.get_product_info()
    platform_id = int(os_configurator.get_product_info().id)
    model_name = product_data.name
    boards: List[str] = hw_data.get(platform_id, [])

    print(f"Detect device {model_name} ({hex(platform_id)}) with boards {boards}")

    defaults = dict()

    if platform_id in [0x0001, 0x0101, 0x1101]:
        defaults['port'] = 503
        defaults['names'] = ['UNIPI1']
        defaults['slave-ids'] = [0]

    autogen_conf = generate_config(boards, defaults=defaults)

    with open('/etc/evok/autogen.yaml', 'w') as f:
        yaml.dump(data=autogen_conf, stream=f)


if __name__ == '__main__':
    run()
#!/usr/bin/env python
#
# (c) 2018, Red Hat, Inc.
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import sys
import json
import argparse

from ansible.parsing.dataloader import DataLoader
from ansible.module_utils.six import iteritems, raise_from
from ansible.module_utils._text import to_text
try:
    from ansible_collections.community.general.plugins.module_utils.net_tools.nios.api import WapiInventory
    from ansible_collections.community.general.plugins.module_utils.net_tools.nios.api import normalize_extattrs, flatten_extattrs
except ImportError as exc:
    try:
        # Fallback for Ansible 2.9
        from ansible.module_utils.net_tools.nios.api import WapiInventory
        from ansible.module_utils.net_tools.nios.api import normalize_extattrs, flatten_extattrs
    except ImportError:
        raise_from(
            Exception(
                'This inventory plugin only works with Ansible 2.9, 2.10, 3, or 4,'
                ' or when community.general < 4.0.0 is installed correctly in PYTHONPATH.'
                ' Try using the inventory plugin from infoblox.nios_modules instead.'),
            exc)


CONFIG_FILES = [
    os.environ.get('INFOBLOX_CONFIG_FILE', ''),
    '/etc/ansible/infoblox.yaml',
    '/etc/ansible/infoblox.yml'
]


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--list', action='store_true',
                        help='List host records from NIOS for use in Ansible')

    parser.add_argument('--host',
                        help='List meta data about single host (not used)')

    return parser.parse_args()


def main():
    args = parse_args()

    for config_file in CONFIG_FILES:
        if os.path.exists(config_file):
            break
    else:
        sys.stderr.write('unable to locate config file at /etc/ansible/infoblox.yaml\n')
        sys.exit(-1)

    try:
        loader = DataLoader()
        config = loader.load_from_file(config_file)
        provider = config.get('provider') or {}
        wapi = WapiInventory(provider)
    except Exception as exc:
        sys.stderr.write(to_text(exc))
        sys.exit(-1)

    if args.host:
        host_filter = {'name': args.host}
    else:
        host_filter = {}

    config_filters = config.get('filters')

    if config_filters.get('view') is not None:
        host_filter['view'] = config_filters['view']

    if config_filters.get('extattrs'):
        extattrs = normalize_extattrs(config_filters['extattrs'])
    else:
        extattrs = {}

    hostvars = {}
    inventory = {
        '_meta': {
            'hostvars': hostvars
        }
    }

    return_fields = ['name', 'view', 'extattrs', 'ipv4addrs']

    hosts = wapi.get_object('record:host',
                            host_filter,
                            extattrs=extattrs,
                            return_fields=return_fields)

    if hosts:
        for item in hosts:
            view = item['view']
            name = item['name']

            if view not in inventory:
                inventory[view] = {'hosts': []}

            inventory[view]['hosts'].append(name)

            hostvars[name] = {
                'view': view
            }

            if item.get('extattrs'):
                for key, value in iteritems(flatten_extattrs(item['extattrs'])):
                    if key.startswith('ansible_'):
                        hostvars[name][key] = value
                    else:
                        if 'extattrs' not in hostvars[name]:
                            hostvars[name]['extattrs'] = {}
                        hostvars[name]['extattrs'][key] = value

    sys.stdout.write(json.dumps(inventory, indent=4))
    sys.exit(0)


if __name__ == '__main__':
    main()

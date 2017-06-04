#!/usr/bin/python
#encoding: utf-8 -*-

DOCUMENTATION = '''
---
module: bigv-vm
version_added: "1.4.3"
short_description: Create/Delete VMs from BigV
description:
   - Create or Remove virtual machines from BigV.
options:
   login_username:
     description:
        - login username to authenticate to BigV
     required: true
     default: admin
   login_password:
     description:
        - Password for user to login with
     required: true
     default: 'yes'
   login_yubikey:
     description:
        - Yubikey OTP
     required: false
   vm_name:
     description:
        - Full of the VM to operate on, e.g. test.default.joebloggs.uk0.bigv.io
    required: true
   vm_distribution:
     description:
        - Operating system to image the machine with (only when creating a new machine)
     required: false
     default: 'squeeze'
   vm_cores:
     description:
        - Cores to provision the new machine with (as a string, like the CLI)
     required: false
     default: '1'
   vm_memory:
     description:
        - GB Memory to provision the new machine with (as a string, like the CLI)
     required: false
     default: '1'
   vm_discs:
     description:
        - Discs to provision the new machine with (as a string, like the CLI)
     required: false
     default: 'sata:25GB'
   vm_rdns:
     description:
        - RDNS record for the Virtual Machine's primary IPv6 and IPv4 addresses
   vm_root_password:
     required: false
     description:
       - Root password for the created VM
   vm_zone:
     required: false
     default: 'york'
     description:
        - Zone to deploy the VM in
   purge:
     description:
        - Whether or not to purge the disc when deleting.
     default: false
     required: false

reguirements: ["bigv","requests"]

'''

EXAMPLES = '''
# Creates a new VM
- bigv-vm: state: present
        login_username: alice
        login_password: test123
        vm_name: status.default.foo.uk0.bigv.io
        vm_rdns: 
'''

RETURN= '''
an explanation of the json output returned from this module
'''

import json
import time
import sys
import os

from ansible.module_utils.basic import AnsibleModule

try:
    # symlink this files directory into your playbook directory if it isn't
    # under the same directory as your playbook
    sys.path.append(".")
    import bytemark_auth_client
    import bytemark_client
    HAS_BYTEMARK_CLIENT = True
except:
    HAS_BYTEMARK_CLIENT = False

def main():      
    module = AnsibleModule(
        argument_spec = dict(
            login_username = dict(required = True),
            login_password = dict(required = True),
            login_yubikey = dict(default = None),
            vm_name = dict(required = True),
            vm_group = dict(required = True),
            vm_account = dict(required = True),
            vm_location = dict(default = "https://uk0.bigv.io"),
            vm_distribution = dict(default = ""),
            vm_cores = dict(default = 1),
            vm_memory = dict(default = 1),
            vm_storage_grade = dict(default = "sata"),
            vm_disc_size = dict(default = 25)
            vm_root_password  = dict(required = False),
            vm_rdns = dict(default = None),
            vm_zone = dict(default = "york"),
            vm_hardware_profile = dict(default = "virtio2013"),
            vm_power_on = dict(default = True),
            vm_cdrom_url = dict(default = ""),
            wait = dict(default = "yes", choices = ["yes", "no"]),
            group_create = dict(default = 'no', choices = ['yes', 'no']),
            purge = dict(default = False, choices = [True, False]),
            state = dict(default = 'present', choices = ['absent', 'present', 'running', 'stopped'])
        )
    )

    if HAS_BYTEMARK_CLIENT = False:
        module.fail_json(msg = "Requires Bytemark Client")

    # Authenticate user and setup bytemark service client
    session_id = authenticate_user(username = module.params["login_username"],
                                   password = module.params["login_password"],
                                   yubikey = module.params["login_yubikey"])
    bm_client = get_bytemark_client(session_id)

    # Get the account for the user
    account = get_by_name(bm_client.get_accounts(), name = module.params["login_username"])
    if account is None:
        module.fail_json(msg = "Unable to find account for logged in user: %" % module.params["login_username"])
    
    # Check if the group exists
    group = get_by_name(bm_client.get_groups(), name = module.params["vm_group"])
    if group is None:
        if module.params["group_create"]:
            bm_client.create_group(account_id = account.id,
                                   group = bm_client.Group(name = module.params["vm_group"]))
        else:
            module.fail_json(msg = "Group: %s doesn't exist and group_create is false" % vm_group)

    # Check if the VM already exists
    virtual_machines = bm_client.get_virtual_machines(group_id = group.group_id, include_deleted = True)
    target = get_by_name(virtual_machines, name = module.params["vm_name"])

    if target is None:
        if module.params["state"] == "absent":
            module.exit_json(changed = False)
        elif module.params["state"] == "present":
            createVirtualMachine(bm_client, module.params)
            module.exit_json(changed = True, vm = machine.info())
    else:
        if module.params['state'] == "absent":
            bm_client.delete_virtual_machine(purge = module.params["purge"])
            if module.params['purge']:
                module.exit_json(changed = True, msg = "%s was PURGED FOREVER" % target.hostname())
            else:
                module.exit_json(changed = True, msg = "%s was deleted" % target.hostname())
        else:                
            if target.state() == "on" and module.params['state'] == "stopped":
                #target.stop()
                module.exit_json(changed = True, bigv_vm = target.info())
            elif target.state() == "off" and module.params['state'] == "running":
                #target.start()
                module.exit_json(changed = True, bigv_vm = target.info())
            else:
                # everything matches what we specified
                #module.exit_json(changed=False, bigv_vm=target.info())

    module.fail_json(msg="Shouldn't reach here")

except bigv.BigVProblem as e:
    module.fail_json(msg=e.msg, http_status=e.http_status, http_method=e.http_method, url=e.url)

def authenticate_user(self, username, password, yubikey):
    # Authenticate with the Bytemark authorization service
    user = bytemark_auth_client.User(username = module.params["login_username"],
                                     password = module.params["login_password"],
                                     yubikey = module.params["login_yubikey"])

    auth_client = bytemark_auth_client.DefaultApi()
    session_id = auth_client.authenticate_user(user = user)

    return session_id
                             
def get_bytemark_client(self, session_id):
    # Setup bytemark service client
    bm_client = bytemark_client.DefaultApi()

    authorization_name = "Authorization"
    config = bm_client.configuration
    config.api_key_prefix[authorization_name] = "Bearer"
    config.api_key[authorization_name] = session_id

    return bm_client
                             
def create_virtual_machine(self, bytemark_client, account_id, group_id, module_params):
    vm_combined = bytemark_client.VirtualMachineCombined(
        virtual_machine = bytemark_client.VirtualMachine(
            name = module_params["vm_name"],
            zone_name = module_params["vm_zone"],
            cores = module_params["vm_cores"],
            memory = module_params["vm_memory"],
            hardware_profile = module_params["vm_hardware_profile"],
            cdrom_url = module_params["vm_cdrom_url"],
            power_on = module_params["vm_power_on"],
        ),
        discs = [bytemark_client.Disc(
            storage_grade = module_params["vm_storage_grade"],
            size = module_params["vm_disc_size"] * 1024
        )],
        reimage = bytemark_client.Reimage(
            distribution = module_params["vm_distribution"],
            root_password = module_params["vm_root_password"]
        ),
        ips = bytemark_client.IPS()
    )

    vm = bm_client.create_virtual_machine(account_id = account_id,
                                          group_id = group_id,
                                          virtual_machine = vm_combined)

    # Wait for the machine to power up
    if module.params["vm_power_on"] = True:        
        for i in xrange(25):
            get_by_name(bm_client.get_virtual_machines, name=vm.name)
            if target.state() == "on":
                break
                         
def get_by_name(self, seq, name):
    for el in seq:
        if el.name == name: return el

if __name__ == '__main__':
    main()

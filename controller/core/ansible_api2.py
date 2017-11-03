# ~*~ coding: utf-8 ~*~

from ansible.plugins.callback import CallbackBase
from ansible.inventory import Inventory, Host, Group
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader

from __future__ import unicode_literals

import os
from collections import namedtuple, defaultdict
import sys

sys.path.append('hostinfo/ansible_runner/')

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.playbook.play import Play
import ansible.constants as C
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars

from inventory import JMSInventory
#from callback import AdHocResultCallback, PlaybookResultCallBack, CommandResultCallback


class CommandResultCallback(CallbackBase):
    def __init__(self, display=None):
        self.result_q = dict(contacted={}, dark={})
        super(CommandResultCallback, self).__init__(display)

    def gather_result(self, n, res):
        self.result_q[n][res._host.name] = {}
        self.result_q[n][res._host.name]['cmd'] = res._result.get('cmd')
        self.result_q[n][res._host.name]['stderr'] = res._result.get('stderr')
        self.result_q[n][res._host.name]['stdout'] = res._result.get('stdout')
        self.result_q[n][res._host.name]['rc'] = res._result.get('rc')

    def v2_runner_on_ok(self, result):
        self.gather_result("contacted", result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.gather_result("dark", result)

    def v2_runner_on_unreachable(self, result):
        self.gather_result("dark", result)

    def v2_runner_on_skipped(self, result):
        self.gather_result("dark", result)


class AdHocResultCallback(CallbackBase):
    """
    AdHoc result Callback
    """

    def __init__(self, display=None):
        self.result_q = dict(contacted={}, dark={})
        super(AdHocResultCallback, self).__init__(display)

    def gather_result(self, n, res):
        if res._host.name in self.result_q[n]:
            self.result_q[n][res._host.name].append(res._result)
        else:
            self.result_q[n][res._host.name] = [res._result]

    def v2_runner_on_ok(self, result):
        self.gather_result("contacted", result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.gather_result("dark", result)

    def v2_runner_on_unreachable(self, result):
        self.gather_result("dark", result)

    def v2_runner_on_skipped(self, result):
        self.gather_result("dark", result)

    def v2_playbook_on_task_start(self, task, is_conditional):
        pass

    def v2_playbook_on_play_start(self, play):
        pass


class PlaybookResultCallBack(CallbackBase):
    """
    Custom callback model for handlering the output data of
    execute playbook file,
    Base on the build-in callback plugins of ansible which named `json`.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'Dict'

    def __init__(self, display=None):
        super(PlaybookResultCallBack, self).__init__(display)
        self.results = []
        self.output = ""
        self.item_results = {}  # {"host": []}

    def _new_play(self, play):
        return {
            'play': {
                'name': play.name,
                'id': str(play._uuid)
            },
            'tasks': []
        }

    def _new_task(self, task):
        return {
            'task': {
                'name': task.get_name(),
            },
            'hosts': {}
        }

    def v2_playbook_on_no_hosts_matched(self):
        self.output = "skipping: No match hosts."

    def v2_playbook_on_no_hosts_remaining(self):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))

    def v2_playbook_on_play_start(self, play):
        self.results.append(self._new_play(play))

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        summary = {}
        for h in hosts:
            s = stats.summarize(h)
            summary[h] = s

        if self.output:
            pass
        else:
            self.output = {
                'plays': self.results,
                'stats': summary
            }

    def gather_result(self, res):
        if res._task.loop and "results" in res._result and res._host.name in self.item_results:
            res._result.update({"results": self.item_results[res._host.name]})
            del self.item_results[res._host.name]

        self.results[-1]['tasks'][-1]['hosts'][res._host.name] = res._result

    def v2_runner_on_ok(self, res, **kwargs):
        if "ansible_facts" in res._result:
            del res._result["ansible_facts"]

        self.gather_result(res)

    def v2_runner_on_failed(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_unreachable(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_skipped(self, res, **kwargs):
        self.gather_result(res)

    def gather_item_result(self, res):
        self.item_results.setdefault(res._host.name, []).append(res._result)

    def v2_runner_item_on_ok(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_failed(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_skipped(self, res):
        self.gather_item_result(res)


class JMSHost(Host):
    def __init__(self, asset):
        self.asset = asset
        self.name = name = asset.get('hostname') or asset.get('ip')
        self.port = port = asset.get('port') or 22
        super(JMSHost, self).__init__(name, port)
        self.set_all_variable()

    def set_all_variable(self):
        asset = self.asset
        self.set_variable('ansible_host', asset['ip'])
        self.set_variable('ansible_port', asset['port'])
        self.set_variable('ansible_user', asset['username'])

        # 添加密码和秘钥
        if asset.get('password'):
            self.set_variable('ansible_ssh_pass', asset['password'])
        if asset.get('private_key'):
            self.set_variable('ansible_ssh_private_key_file', asset['private_key'])

        # 添加become支持
        become = asset.get("become", False)
        if become:
            self.set_variable("ansible_become", True)
            self.set_variable("ansible_become_method", become.get('method', 'sudo'))
            self.set_variable("ansible_become_user", become.get('user', 'root'))
            self.set_variable("ansible_become_pass", become.get('pass', ''))
        else:
            self.set_variable("ansible_become", False)


class JMSInventory(Inventory):
    """
    提供生成Ansible inventory对象的方法
    """

    def __init__(self, host_list=None):
        if host_list is None:
            host_list = []
        assert isinstance(host_list, list)
        self.host_list = host_list
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        super(JMSInventory, self).__init__(self.loader, self.variable_manager,
                                           host_list=host_list)

    def parse_inventory(self, host_list):
        """用于生成动态构建Ansible Inventory.
        self.host_list: [
            {"name": "asset_name",
             "ip": <ip>,
             "port": <port>,
             "user": <user>,
             "pass": <pass>,
             "key": <sshKey>,
             "groups": ['group1', 'group2'],
             "other_host_var": <other>},
             {...},
        ]

        :return: 返回一个Ansible的inventory对象
        """

        # TODO: 验证输入
        # 创建Ansible Group,如果没有则创建default组
        ungrouped = Group('ungrouped')
        all = Group('all')
        all.add_child_group(ungrouped)
        self.groups = dict(all=all, ungrouped=ungrouped)

        for asset in host_list:
            host = JMSHost(asset=asset)
            asset_groups = asset.get('groups')
            if asset_groups:
                for group_name in asset_groups:
                    if group_name not in self.groups:
                        group = Group(group_name)
                        self.groups[group_name] = group
                    else:
                        group = self.groups[group_name]
                    group.add_host(host)
            else:
                ungrouped.add_host(host)
            all.add_host(host)


__all__ = ["AdHocRunner", "PlayBookRunner"]

C.HOST_KEY_CHECKING = False


# logger = get_logger(__name__)


# Jumpserver not use playbook
class PlayBookRunner(object):
    """
    用于执行AnsiblePlaybook的接口.简化Playbook对象的使用.
    """
    Options = namedtuple('Options', [
        'listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
        'module_path', 'forks', 'remote_user', 'private_key_file', 'timeout',
        'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
        'scp_extra_args', 'become', 'become_method', 'become_user',
        'verbosity', 'check', 'extra_vars'])

    def __init__(self,
                 hosts=None,
                 playbook_path=None,
                 forks=C.DEFAULT_FORKS,
                 listtags=False,
                 listtasks=False,
                 listhosts=False,
                 syntax=False,
                 module_path=None,
                 remote_user='root',
                 timeout=C.DEFAULT_TIMEOUT,
                 ssh_common_args=None,
                 ssh_extra_args=None,
                 sftp_extra_args=None,
                 scp_extra_args=None,
                 become=True,
                 become_method=None,
                 become_user="root",
                 verbosity=None,
                 extra_vars=None,
                 connection_type="ssh",
                 passwords=None,
                 private_key_file=None,
                 check=False):

        C.RETRY_FILES_ENABLED = False
        self.callbackmodule = PlaybookResultCallBack()
        if playbook_path is None or not os.path.exists(playbook_path):
            raise AnsibleError(
                "Not Found the playbook file: %s." % playbook_path)
        self.playbook_path = playbook_path
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        self.passwords = passwords or {}
        self.inventory = JMSInventory(hosts)

        self.options = self.Options(
            listtags=listtags,
            listtasks=listtasks,
            listhosts=listhosts,
            syntax=syntax,
            timeout=timeout,
            connection=connection_type,
            module_path=module_path,
            forks=forks,
            remote_user=remote_user,
            private_key_file=private_key_file,
            ssh_common_args=ssh_common_args or "",
            ssh_extra_args=ssh_extra_args or "",
            sftp_extra_args=sftp_extra_args,
            scp_extra_args=scp_extra_args,
            become=become,
            become_method=become_method,
            become_user=become_user,
            verbosity=verbosity,
            extra_vars=extra_vars or [],
            check=check
        )

        self.variable_manager.extra_vars = load_extra_vars(loader=self.loader,
                                                           options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options)

        self.variable_manager.set_inventory(self.inventory)

        # 初始化playbook的executor
        self.runner = PlaybookExecutor(
            playbooks=[self.playbook_path],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords)

        if self.runner._tqm:
            self.runner._tqm._stdout_callback = self.callbackmodule

    def run(self):
        if not self.inventory.list_hosts('all'):
            raise AnsibleError('Inventory is empty')
        self.runner.run()
        self.runner._tqm.cleanup()
        return self.callbackmodule.output


class AdHocRunner(object):
    """
    ADHoc接口
    """
    Options = namedtuple("Options", [
        'connection', 'module_path', 'private_key_file', "remote_user",
        'timeout', 'forks', 'become', 'become_method', 'become_user',
        'check', 'extra_vars',
    ]
                         )

    results_callback_class = AdHocResultCallback

    def __init__(self,
                 hosts=C.DEFAULT_HOST_LIST,
                 forks=C.DEFAULT_FORKS,  # 5
                 timeout=C.DEFAULT_TIMEOUT,  # SSH timeout = 10s
                 remote_user=C.DEFAULT_REMOTE_USER,  # root
                 module_path=None,  # dirs of custome modules
                 connection_type="smart",
                 become=None,
                 become_method=None,
                 become_user=None,
                 check=False,
                 passwords=None,
                 extra_vars=None,
                 private_key_file=None,
                 gather_facts='no'):

        self.pattern = ''
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.gather_facts = gather_facts
        self.results_callback = AdHocRunner.results_callback_class()
        self.options = self.Options(
            connection=connection_type,
            timeout=timeout,
            module_path=module_path,
            forks=forks,
            become=become,
            become_method=become_method,
            become_user=become_user,
            check=check,
            remote_user=remote_user,
            extra_vars=extra_vars or [],
            private_key_file=private_key_file,
        )

        self.variable_manager.extra_vars = load_extra_vars(self.loader,
                                                           options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options)
        self.passwords = passwords or {}
        self.inventory = JMSInventory(hosts)
        self.variable_manager.set_inventory(self.inventory)
        self.tasks = []
        self.play_source = None
        self.play = None
        self.runner = None

    @staticmethod
    def check_module_args(module_name, module_args=''):
        if module_name in C.MODULE_REQUIRE_ARGS and not module_args:
            err = "No argument passed to '%s' module." % module_name
            print(err)
            return False
        return True

    def run(self, task_tuple, pattern='all', task_name='Ansible Ad-hoc'):
        """
        :param task_tuple:  (('shell', 'ls'), ('ping', ''))
        :param pattern:
        :param task_name:
        :return:
        """
        for module, args in task_tuple:
            if not self.check_module_args(module, args):
                return
            self.tasks.append(
                dict(action=dict(
                    module=module,
                    args=args,
                ))
            )

        self.play_source = dict(
            name=task_name,
            hosts=pattern,
            gather_facts=self.gather_facts,
            tasks=self.tasks
        )

        self.play = Play().load(
            self.play_source,
            variable_manager=self.variable_manager,
            loader=self.loader,
        )

        self.runner = TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords,
            stdout_callback=self.results_callback,
        )

        if not self.inventory.list_hosts("all"):
            raise AnsibleError("Inventory is empty.")

        if not self.inventory.list_hosts(self.pattern):
            raise AnsibleError(
                "pattern: %s  dose not match any hosts." % self.pattern)

        try:
            self.runner.run(self.play)
        except Exception as e:
            logger.warning(e)
        else:
            # logger.debug(self.results_callback.result_q)
            return self.results_callback.result_q
        finally:
            if self.runner:
                self.runner.cleanup()
            if self.loader:
                self.loader.cleanup_all_tmp_files()

    def clean_result(self):
        """
        :return: {
            "success": ['hostname',],
            "failed": [('hostname', 'msg'), {}],
        }
        """
        result = {'success': [], 'failed': []}
        for host in self.results_callback.result_q['contacted']:
            result['success'].append(host)

        for host, msgs in self.results_callback.result_q['dark'].items():
            msg = '\n'.join(['{} {}: {}'.format(
                msg.get('module_stdout', ''),
                msg.get('invocation', {}).get('module_name'),
                msg.get('msg', '')) for msg in msgs])
            result['failed'].append((host, msg))
        return result


def test_run():
    assets = [
        {
            "hostname": "192.168.244.129",
            "ip": "192.168.244.129",
            "port": 22,
            "username": "root",
            "password": "redhat",
        },
    ]
    task_tuple = (('shell', 'ls'),)  ##例子，调用普通的模块命令
    hoc = AdHocRunner(hosts=assets)
    hoc.results_callback = CommandResultCallback()
    ret = hoc.run(task_tuple)
    print(ret)

    task_tuple = (('setup', ''),)  ##例子，调用setup，获取资产信息
    runner = AdHocRunner(assets)
    result = runner.run(task_tuple=task_tuple, pattern='all', task_name='Ansible Ad-hoc')
    print(result)

    # play = PlayBookRunner(assets, playbook_path='/tmp/some.yml')  ##yml
    """
    # /tmp/some.yml
    ---
    - name: Test the plabybook API.
      hosts: all
      remote_user: root
      gather_facts: yes
      tasks:
       - name: exec uptime
         shell: uptime
    """
    # play.run()


if __name__ == "__main__":
    test_run()
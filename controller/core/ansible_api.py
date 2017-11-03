# -*- coding: UTF-8 -*-

from controller.core.ansible_api2.runner import AdHocRunner


def get_info(assets):
    data = {}
    #runner = runner.Runner(module_name='setup', module_args='', pattern='all', forks=2)
    task_tuple = (('setup', ''),)
    runner = AdHocRunner(assets)
    task = runner.run(task_tuple=task_tuple, pattern='all', task_name='Ansible Ad-hoc')

    try:
        status = task['dark']['host'][0]['unreachable']
    except:
        status = False

    if status:
        return False
    else:
        data = task['contacted']['host'][0]['ansible_facts']
        # datastructure = task
        sn = data['ansible_product_serial']
        host_name = data['ansible_hostname']

        #description = datastructure['contacted'][ip][0]['ansible_facts']['ansible_lsb']['description']
        ansible_machine = data['ansible_machine']
        #sysinfo = '%s %s' % (description, ansible_machine)
        sysinfo = '%s' % (ansible_machine)

        os_kernel = data['ansible_kernel']

        cpu = data['ansible_processor'][1]
        cpu_count = data['ansible_processor_count']
        cpu_cores = data['ansible_processor_cores']
        mem = data['ansible_memtotal_mb']

        ipadd_in = data['ansible_all_ipv4_addresses'][0]
        disk = data['ansible_devices']['sda']['size']
        # print sysinfo
        data['sn'] = sn
        data['sysinfo'] = sysinfo
        data['cpu'] = cpu
        data['cpu_count'] = cpu_count
        data['cpu_cores'] = cpu_cores
        data['mem'] = mem
        data['disk'] = disk
        data['ipadd_in'] = ipadd_in
        data['os_kernel'] = os_kernel
        data['host_name'] = host_name

        return data


def get_ulimit(assets):
    # 最大文件打开数
    #runner = ansible.runner.Runner(module_name='shell', module_args='ulimit -n', pattern='all', forks=2)
    task_tuple = (('shell', 'ulimit -n'),)
    runner = AdHocRunner(assets)
    task = runner.run(task_tuple=task_tuple, pattern='all', task_name='Ansible Ad-hoc')
    data = task['contacted']['host'][0]
    result = data['stdout']

    return result


def get_uptime(assets):
    # 运行时间
    #runner = ansible.runner.Runner(module_name='shell', module_args='uptime', pattern='all', forks=2)
    task_tuple = (('shell', 'uptime'),)
    runner = AdHocRunner(assets)
    task = runner.run(task_tuple=task_tuple, pattern='all', task_name='Ansible Ad-hoc')
    data = task['contacted']['host'][0]
    result = data['stdout']
    try:
        result = result.split('up')[1].split('days')[0]
        result = int(result)
    except:
        result = 0
    return result


def get_service_port(assets):
    # 获取服务端口信息
    # 数据结构 {服务名:[端口], ...}
    #runner = ansible.runner.Runner(module_name='shell', module_args='netstat -nptl', pattern='all', forks=2)
    task_tuple = (('shell', 'netstat -nptl'),)
    runner = AdHocRunner(assets)
    task = runner.run(task_tuple=task_tuple, pattern='all', task_name='Ansible Ad-hoc')
    data1 = task['contacted']['host'][0]
    data = data1['stdout']
    data = data.split('\n')

    result = {}
    for dt in data[2:]:
        dt = dt.split()
        if dt[3].count(':') == 1:
            port = dt[3].split(':')[1]
            service = dt[6].split('/')[1]
            if service not in result:
                result[service] = [port]
            else:
                result[service].append(port)
    return result

if __name__ == '__main__':
    data = get_info('192.168.242.128')
    print(data)

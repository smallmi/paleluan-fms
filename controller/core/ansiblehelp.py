# -*- coding: UTF-8 -*-

from controller.core.ansible_api2 import runner


def get_info(ip):
    data = {}
    #runner = runner.Runner(module_name='setup', module_args='', pattern='all', forks=2)
    task_tuple = (('setup', ''),)
    runnering = runner.AdHocRunner()
    task = runnering.run(task_tuple=task_tuple, pattern=ip, task_name='Ansible Ad-hoc')
    datastructure = task
    sn = datastructure['contacted'][ip][0]['ansible_facts']['ansible_product_serial']
    host_name = datastructure['contacted'][ip][0]['ansible_facts']['ansible_hostname']

    #description = datastructure['contacted'][ip][0]['ansible_facts']['ansible_lsb']['description']
    ansible_machine = datastructure['contacted'][ip][0]['ansible_facts']['ansible_machine']
    #sysinfo = '%s %s' % (description, ansible_machine)
    sysinfo = '%s' % (ansible_machine)

    os_kernel = datastructure['contacted'][ip][0]['ansible_facts']['ansible_kernel']

    cpu = datastructure['contacted'][ip][0]['ansible_facts']['ansible_processor'][1]
    cpu_count = datastructure['contacted'][ip][0]['ansible_facts']['ansible_processor_count']
    cpu_cores = datastructure['contacted'][ip][0]['ansible_facts']['ansible_processor_cores']
    mem = datastructure['contacted'][ip][0]['ansible_facts']['ansible_memtotal_mb']

    ipadd_in = datastructure['contacted'][ip][0]['ansible_facts']['ansible_all_ipv4_addresses'][0]
    disk = datastructure['contacted'][ip][0]['ansible_facts']['ansible_devices']['sda']['size']
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


def get_ulimit(ip):
    # 最大文件打开数
    #runner = ansible.runner.Runner(module_name='shell', module_args='ulimit -n', pattern='all', forks=2)
    task_tuple = (('shell', 'ulimit -n'),)
    runnering = runner.AdHocRunner()
    task = runnering.run(task_tuple=task_tuple, pattern=ip, task_name='Ansible Ad-hoc')
    datastructure = task
    result = datastructure['contacted'][ip][0]['stdout']

    return result


def get_uptime(ip):
    # 运行时间
    #runner = ansible.runner.Runner(module_name='shell', module_args='uptime', pattern='all', forks=2)
    task_tuple = (('shell', 'uptime'),)
    runnering = runner.AdHocRunner()
    task = runnering.run(task_tuple=task_tuple, pattern=ip, task_name='Ansible Ad-hoc')
    datastructure = task
    result = datastructure['contacted'][ip][0]['stdout']
    try:
        result = result.split('up')[1].split('days')[0]
        result = int(result)
    except:
        result = 0
    return result


def get_service_port(ip):
    # 获取服务端口信息
    # 数据结构 {服务名:[端口], ...}
    #runner = ansible.runner.Runner(module_name='shell', module_args='netstat -nptl', pattern='all', forks=2)
    task_tuple = (('shell', 'netstat -nptl'),)
    runnering = runner.AdHocRunner()
    task = runnering.run(task_tuple=task_tuple, pattern=ip, task_name='Ansible Ad-hoc')
    datastructure = task
    data = datastructure['contacted'][ip][0]['stdout']
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

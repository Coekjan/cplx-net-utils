import concurrent.futures
import ipaddress
import sys
import time
from ipaddress import ip_address, ip_network
from telnetlib import Telnet

from pysh import main


SKIP_SUBMIT = 0
SAVE_ALL = 1


buf = []
dev_name: str | None = None
dev_nets = []
ospf_depth = 0
mypre = '186'
telnet_port = None
dev_open_mode = 'w'
asn = 1
is_rt = False
dev_addrs = set()

dev_ctxs = {}


def parse_id(dev_name) -> str:
    sub_id = dev_name[-1]  # XXX: only support 0-9
    if is_rt:
        if 'ce' in dev_name:
            id = 0
        elif 'pe' in dev_name:
            id = 1
        elif 'rr' in dev_name:
            id = 2
        elif 'br' in dev_name:
            id = 3
        else:
            raise NotImplementedError()
        return f'{asn}.0.{id}.{sub_id}'
    else:
        return f'{asn}.1.0.{sub_id}'


def parse_cidr(cidr: str) -> str:
    return cidr.replace('@', mypre)


def parse_net(cidr: str):
    return ip_network(cidr, strict=False)


def push(*args):
    buf.extend(args)


def cdev(name, port=None):
    global dev_name, telnet_port, ospf_depth, is_rt, dev_open_mode, dev_nets, dev_addrs, buf
    if dev_name:
        dev_ctxs[dev_name] = {
            'dev_nets': dev_nets,
            'dev_addrs': dev_addrs,
            'buf': buf,
            'port': telnet_port,
        }

    dev_name = name
    ospf_depth = 0
    is_rt = name.startswith('rt')
    if not is_rt:
        assert name.startswith('ls')

    try:
        ctx = dev_ctxs[name]
    except KeyError:
        dev_open_mode = 'w'
        dev_nets = []
        dev_addrs = set()
        telnet_port = port
        buf = []
        push('   sys', 'sysn ' + name)
    else:
        dev_open_mode = 'a'
        dev_nets = ctx['dev_nets']
        dev_addrs = ctx['dev_addrs']
        buf = ctx['buf']
        telnet_port = ctx['port']


def cdev_rtce(no):
    cdev(f'rtce{no}', 2000 + int(no))


def cdev_ls(no):
    cdev(f'ls{no}', 2100 + int(no))


def cdev_rtrr(no):
    cdev(f'rtrr{no}', 2200 + int(no))


def cdev_rtbr(no):
    cdev(f'rtbr{no}', 2300 + int(no))


def cdev_rtpe(no):
    cdev(f'rtpe{no}', 2400 + int(no))


def cdev_lsce(no):
    cdev(f'lsce{no}', 2500 + int(no))


def ints(*cidrs):
    vlan_id = 2

    for cidr in cidrs:
        cidr, ports = parse_cidr(cidr).split(':')
        ports = ports.split(',')

        if is_rt:
            assert len(ports) == 1
            port: str = ports[0]
            assert not port[0].isnumeric()
            push(f'int {port}')
        else:
            push(f'vlan {vlan_id}', 'quit')
            for port in ports:
                push(f'int {port}', 'port link-type access',
                     f'port default vlan {vlan_id}')
                push('quit')
            push(f'inter vlan{vlan_id}')

        n = parse_net(cidr)
        dev_nets.append(n)
        ip = cidr.split('/')[0]
        dev_addrs.add(ip)
        push(f'ip addr {ip} {n.prefixlen}')
        push('quit')

        vlan_id += 1
    
    id = parse_id(dev_name)
    push('int loopback 1', f'ip addr {id} 32', 'quit')


def asno(no):
    global asn
    asn = int(no)


def extern(*devs):
    extern_dev.update(devs)


def rtce(no, *cidrs):
    cdev_rtce(no)
    basic_conf(*cidrs)


def ls(no, *cidrs):
    cdev_ls(no)
    basic_conf(*cidrs)


def rtrr(no, *cidrs):
    cdev_rtrr(no)
    basic_conf(*cidrs)


def rtbr(no, *cidrs):
    cdev_rtbr(no)
    basic_conf(*cidrs)


def rtpe(no, *cidrs):
    cdev_rtpe(no)
    basic_conf(*cidrs)


def lsce(no, *cidrs):
    cdev_lsce(no)
    basic_conf(*cidrs)


def basic_conf(*cidrs):
    ints(*cidrs)
    push('undo ospf 1', 'y')
    push('undo mpls', 'y')


def ospf_rtrr(nos, *cidrs):
    for no in nos.split(','):
        cdev_rtrr(no)
        ospf(*cidrs)


def ospf_rtbr(nos, *cidrs):
    for no in nos.split(','):
        cdev_rtbr(no)
        ospf(*cidrs)


def ospf_rtpe(nos, *cidrs):
    for no in nos.split(','):
        cdev_rtpe(no)
        ospf(*cidrs)


def ospf(*cidrs):
    nets = dev_nets.copy()
    for cidr in cidrs:
        cidr = parse_cidr(cidr)
        if cidr.startswith('^'):
            nets = [n for n in nets if not n.subnet_of(ip_network(cidr[1:]))]

    push('ospf 1', 'area 0')

    for n in nets:
        n: ipaddress.IPv4Network
        ip = str(n.network_address)
        mask = str(n.hostmask)
        push(f'network {ip} {mask}')
    
    id = parse_id(dev_name)
    push(f'network {id} 0.0.0.0')

    push('quit', 'quit', 'quit', 'reset ospf 1 pro', 'y', 'sys')


def mpls_rtrr(nos, *ints):
    for no in nos.split(','):
        cdev_rtrr(no)
        mpls(*ints)


def mpls_rtbr(nos, *ints):
    for no in nos.split(','):
        cdev_rtbr(no)
        mpls(*ints)


def mpls_rtpe(nos, *ints):
    for no in nos.split(','):
        cdev_rtpe(no)
        mpls(*ints)


def mpls(*ints):
    id = parse_id(dev_name)
    
    push(f'mpls lsr-id {id}')
    push('mpls', 'lsp-trigger all', 'mpls ldp', 'q')

    for int in ints:
        push(f'int {int}', 'mpls', 'mpls ldp', 'q')
    
    push('quit', 'reset mpls ldp all', 'sys')


def dump(write_file=True):
    s = '\n'.join(buf) + '\n'
    if write_file:
        with open(f'cfgs/as{asn}/{dev_name}.in', 'w', encoding='utf-8') as fp:
            fp.write(s)
    buf.clear()
    return s


extern_dev = set()
done_vis = set()


def subm(pool, write_file=True):
    def worker(s, name, port):
        if name in extern_dev:
            return
        print(f'connecting to {name} (:{port})')
        if SKIP_SUBMIT:
            return
        t = Telnet('127.0.0.1', port)
        print(f'writing to {name} ({t.host}:{port})')
        t.write(b'\n' * 10 + s.encode('utf-8'))
        # print(t.read_eager())
        t.write(b'subm' * 3)
        ts = time.time()
        out = t.read_until(b'subm', timeout=10)
        if write_file:
            with open(f'outs/as{asn}/' + name + '.out', 'wb') as fp:
                fp.write(out)
        if time.time() - ts >= 9:
            t.close()
            raise RuntimeError(f'{name} (:{port}) timed out')
        t.write(b'\b' * 15)
        # print(out.decode('utf-8', errors='ignore'))
        t.close()
        done_vis.add(name)

    return pool.submit(worker, dump(write_file), dev_name, telnet_port)


if __name__ == '__main__':
    main(fn_map=globals() | {
        'asn': asno,
    })

    if len(sys.argv) > 2 and sys.argv[2] == '-c':
        try:
            with open(f'dev_vis-as{asn}', encoding='utf-8') as fp:
                done_vis.update(fp.read().split())
        except FileNotFoundError:
            pass

    devs = set(dev_ctxs.keys())
    devs.add(dev_name)
    devs.difference_update(done_vis)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(devs)) as pool:
            futs = []
            for dev in sorted(devs):
                cdev(dev)
                if SAVE_ALL:
                    if SAVE_ALL == 2:
                        buf.clear()
                        push('   sys', 'q', 'reset saved', 'y')
                    else:
                        push('   sys', 'q', 'save', 'y')
                futs.append(subm(pool))
            for fut in futs:
                fut.result()
    finally:
        with open(f'dev_vis-as{asn}', 'w', encoding='utf-8') as fp:
            fp.write('\n'.join(done_vis))

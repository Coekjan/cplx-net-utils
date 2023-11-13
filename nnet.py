import concurrent.futures
import ipaddress
import re
import sys
import time
from ipaddress import ip_network
from telnetlib import Telnet

from pysh import main


SKIP_SUBMIT = 0
SAVE_ALL = 1


buf = []
dev_name: str | None = None
dev_nets = []
ospf_depth = 0
bgp_peers: set[str] = set()
mypre = '186'
telnet_port = None
dev_open_mode = 'w'
asn = 1
is_rt = False
dev_addrs = set()

dev_ctxs = {}


def parse_id(dev_name, /, asno=None) -> str:
    if asno is None:
        asno = asn
    sub_id = dev_name[-1]  # XXX: only support 0-9
    is_rt = dev_name.startswith('rt')
    if not is_rt:
        assert dev_name.startswith('ls')
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
            raise NotImplementedError(dev_name)
        return f'{asno}.0.{id}.{sub_id}'
    else:
        return f'{asno}.1.0.{sub_id}'


def parse_cidr(cidr: str) -> str:
    return cidr.replace('@', mypre)


def parse_id_or_cidr(any: str, *args, **kwargs) -> str:
    try:
        return parse_id(any, *args, **kwargs)
    except (AssertionError, NotImplementedError):
        return parse_cidr(any)


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
    push('undo bgp', 'y')


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


def bgp_rtrr(nos, *cmds):
    bgp_no = f'{asn * 100}'
    for no in nos.split(','):
        cdev_rtrr(no)
        bgp_peers.add(f'rtrr{no}')
        push(f'bgp {bgp_no}')
        for cmd in cmds:
            obj, args = cmd.split('=')
            if obj == 'pe':  # config provider edge
                pe_nos = args.split(',')
                group_name = f'PE{asn}'
                push(f'group {group_name} internal')
                push(f'peer {group_name} connect-interface loopback 1')
                for pe_no in pe_nos:
                    pe_name = f'rtpe{pe_no}'
                    pe_id = parse_id(pe_name)
                    push(f'peer {pe_id} as-number {bgp_no}')
                    push(f'peer {pe_id} group {group_name}')
                push('ipv4-family unicast')
                push('undo synchronization')
                push(f'peer {group_name} enable')
                push(f'peer {group_name} route-policy rr export')
                push(f'peer {group_name} reflect-client')
                push(f'peer {group_name} label-route-capability')
                push(f'peer {group_name} advertise-community')
                for pe_no in pe_nos:
                    pe_name = f'rtpe{pe_no}'
                    pe_id = parse_id(pe_name)
                    push(f'peer {pe_id} enable')
                    push(f'peer {pe_id} group {group_name}')
                push('quit')
            elif obj == 'br':  # config direct-connected asbr
                br_nos = args.split(',')
                group_name = f'ASBR{asn}'
                push(f'group {group_name} internal')
                push(f'peer {group_name} connect-interface loopback 1')
                for br_no in br_nos:
                    br_name = f'rtbr{br_no}'
                    br_id = parse_id(br_name)
                    push(f'peer {br_id} as-number {bgp_no}')
                    push(f'peer {br_id} group {group_name}')
                push('ipv4-family unicast')
                push('undo synchronization')
                push(f'peer {group_name} enable')
                push(f'peer {group_name} label-route-capability')
                for br_no in br_nos:
                    br_name = f'rtbr{br_no}'
                    br_name = parse_id(br_name)
                    push(f'peer {br_name} enable')
                    push(f'peer {br_name} group {group_name}')
                push('quit')
            elif obj == 'ex':  # config external route reflector
                as_rrs = args.split(':')
                for as_rr in as_rrs:
                    pattern = re.match(r'(\d+)\{([\w,]+)\}', as_rr)
                    ex_asno = pattern.group(1)
                    ex_rrs = pattern.group(2).split(',')
                    group_name = f'EXRR{ex_asno}'
                    push(f'group {group_name} external')
                    push(f'peer {group_name} as-number {ex_asno}00')
                    push(f'peer {group_name} connect-interface loopback 1')
                    push(f'peer {group_name} ebgp-max-hop 255')
                    for ex_rr in ex_rrs:
                        rr_id = parse_id_or_cidr(ex_rr, asno=ex_asno)
                        push(f'peer {rr_id} group {group_name}')
                        push(f'peer {rr_id} as-number {ex_asno}00')
                    push('ipv4-family unicast')
                    push('undo synchronization')
                    push(f'peer {group_name} enable')
                    push(f'peer {group_name} next-hop-invariable')
                    for ex_rr in ex_rrs:
                        rr_id = parse_id_or_cidr(ex_rr, asno=ex_asno)
                        push(f'peer {rr_id} enable')
                        push(f'peer {rr_id} group {group_name}')
                    push('quit')
            else:
                raise ValueError(obj, args)
        push('quit')


def bgp_rtrr_done(nos):
    for no in nos.split(','):
        cdev_rtrr(no)
        push('quit', 'reset bgp all', 'sys')


def bgp_rtbr(nos, *cmds):
    bgp_no = f'{asn * 100}'
    for no in nos.split(','):
        cdev_rtbr(no)
        bgp_peers.add(f'rtbr{no}')
        push(f'bgp {bgp_no}')
        for cmd in cmds:
            obj, args = cmd.split('=')
            if obj == 'rr':
                rrs = args.split(',')
                group_name = f'RR{asn}'
                push(f'group {group_name} internal')
                push(f'peer {group_name} connect-interface loopback 1')
                for rr in rrs:
                    rr_id = parse_id(f'rtrr{rr}')
                    push(f'peer {rr_id} as-number {bgp_no}')
                    push(f'peer {rr_id} group {group_name}')
                push('ipv4-family unicast')
                push('undo synchronization')
                push(f'peer {group_name} enable')
                push(f'peer {group_name} route-policy rr export')
                push(f'peer {group_name} next-hop-local')
                push(f'peer {group_name} label-route-capability')
                for rr in rrs:
                    rr_id = parse_id(f'rtrr{rr}')
                    push(f'peer {rr_id} enable')
                    push(f'peer {rr_id} group {group_name}')
                push('quit')
            elif obj == 'ex':
                as_brs = args.split(':')
                for as_br in as_brs:
                    pattern = re.match(r'(\d+)\{([\w@\.,]+)\}', as_br)
                    ex_asno = pattern.group(1)
                    ex_brs = pattern.group(2).split(',')
                    group_name = f'EXBR{ex_asno}'
                    push(f'group {group_name} external')
                    push(f'peer {group_name} as-number {ex_asno}00')
                    for ex_br in ex_brs:
                        br_id = parse_id_or_cidr(ex_br, asno=ex_asno)
                        push(f'peer {br_id} as-number {ex_asno}00')
                        push(f'peer {br_id} group {group_name}')
                    push('ipv4-family unicast')
                    push('undo synchronization')
                    push(f'peer {group_name} enable')
                    push(f'peer {group_name} route-policy asbr export')
                    push(f'peer {group_name} label-route-capability')
                    for ex_br in ex_brs:
                        br_id = parse_id_or_cidr(ex_br, asno=ex_asno)
                        push(f'peer {br_id} enable')
                        push(f'peer {br_id} group {group_name}')
                    push('quit')
            else:
                raise ValueError(obj, args)
        push('quit')
        push(
            'undo route-policy rr node 10',
            'route-policy rr permit node 10',
            'if-match mpls-label',
            'apply mpls-label',
            'quit',
        )


def bgp_rtbr_done(nos):
    bgp_no = f'{asn * 100}'
    for no in nos.split(','):
        cdev_rtbr(no)
        push(f'bgp {bgp_no}')
        push('ipv4-family unicast')
        for peer in bgp_peers:
            n = parse_id(peer)
            push(f'network {n} 255.255.255.255')
        push('quit', 'quit')
        push('undo acl number 2000', 'acl number 2000')
        for (i, peer) in enumerate(bgp_peers):
            n = parse_id(peer)
            push(f'rule {i} permit source {n} 0')
        push('quit')
        push(
            'undo route-policy asbr node 10',
            'route-policy asbr permit node 10',
            'if-match acl 2000',
            'apply mpls-label',
            'quit',
        )
        push('quit', 'reset bgp all', 'sys')


def bgp_rtpe(nos, *cmds):
    bgp_no = f'{asn * 100}'
    for no in nos.split(','):
        cdev_rtpe(no)
        bgp_peers.add(f'rtpe{no}')
        push(f'bgp {bgp_no}')
        for cmd in cmds:
            obj, args = cmd.split('=')
            if obj == 'rr':
                rrs = args.split(',')
                group_name = f'RR{asn}'
                push(f'group {group_name} internal')
                push(f'peer {group_name} connect-interface loopback 1')
                for rr in rrs:
                    rr_id = parse_id(f'rtrr{rr}')
                    push(f'peer {rr_id} as-number {bgp_no}')
                    push(f'peer {rr_id} group {group_name}')
                push('ipv4-family unicast')
                push('undo synchronization')
                push(f'peer {group_name} enable')
                push(f'peer {group_name} label-route-capability')
                for rr in rrs:
                    rr_id = parse_id(f'rtrr{rr}')
                    push(f'peer {rr_id} enable')
                    push(f'peer {rr_id} group {group_name}')
                push('quit')
            else:
                raise ValueError(obj, args)
        push('quit')


def bgp_rtpe_done(nos):
    for no in nos.split(','):
        cdev_rtpe(no)
        push('quit', 'reset bgp all', 'sys')


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
        out = t.read_until(b'subm', timeout=20)
        if write_file:
            with open(f'outs/as{asn}/' + name + '.out', 'wb') as fp:
                fp.write(out)
        if time.time() - ts >= 25:
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

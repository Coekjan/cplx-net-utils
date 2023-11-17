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
vpn_no = 0
vpn_name = ''
is_rt = False
port_cidr = dict()
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


def parse_vpn_bgp_no() -> str:
    return f'{asn * 10000 + int(vpn_no) * 100}'


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
    global dev_name, telnet_port, ospf_depth, port_cidr, is_rt, dev_open_mode, dev_nets, dev_addrs, buf
    if dev_name:
        dev_ctxs[dev_name] = {
            'dev_nets': dev_nets,
            'dev_addrs': dev_addrs,
            'buf': buf,
            'port': telnet_port,
            'port_cidr': port_cidr,
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
        port_cidr = dict()
        buf = []
        push('   sys', 'sysn ' + name)
    else:
        dev_open_mode = 'a'
        dev_nets = ctx['dev_nets']
        dev_addrs = ctx['dev_addrs']
        buf = ctx['buf']
        port_cidr = ctx['port_cidr']
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
            prefer = False
            if port[-1] == '!':
                prefer = True
                port = port[:-1]
            push(f'int {port}')
            if prefer:
                push('ospf cost 10')
            else:
                push('ospf cost 1000')
        else:
            push(f'vlan {vlan_id}', 'quit')
            for port in ports:
                prefer = False
                if port[-1] == '!':
                    prefer = True
                    port = port[:-1]
                push(f'int {port}', 'port link-type access',
                     f'port default vlan {vlan_id}')
                if prefer:
                    push('ospf cost 10')
                else:
                    push('ospf cost 1000')
                push('quit')
            push(f'inter vlan{vlan_id}')

        n = parse_net(cidr)
        dev_nets.append(n)
        ip = cidr.split('/')[0]
        dev_addrs.add(ip)
        push(f'ip addr {ip} {n.prefixlen}')
        push('quit')

        for port in ports:
            port_cidr[port] = cidr

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


def nat_rtce(no, addr_group_if, permit):
    cdev_rtce(no)
    addr_group, interface = addr_group_if.split(':')
    addr_st, addr_ed = addr_group.split('-')
    permit_n = ip_network(parse_cidr(permit))
    push(f'inter {interface}',
         'undo nat outbound 2001 address-group 1', 'quit')

    push('undo acl number 2001', 'acl number 2001')
    push(f'rule permit source {permit_n.network_address} {permit_n.netmask}')
    push('rule deny source any', 'quit')

    push('undo nat address-group 1',
         f'nat address-group 1 {addr_st} {addr_ed}')
    push(f'inter {interface}', 'nat outbound 2001 address-group 1', 'quit')


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

    push('ospf 1')
    push('import-route bgp')
    push('area 0')

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
                push('ipv4-family vpnv4')
                push('policy vpn-target')
                push(f'peer {group_name} enable')
                push(f'peer {group_name} reflect-client')
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
                    push('ipv4-family vpnv4')
                    push('policy vpn-target')
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
        push(
            'undo route-policy rr node 10',
            'route-policy rr permit node 10',
            'if-match mpls-label',
            'apply mpls-label',
            'quit',
        )


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
            elif obj == 'prefer':
                if args == 'true':
                    push('default med 20')
                    push('default local-preference 400')
                else:
                    push('default med 40')
                    push('default local-preference 200')
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
                push('ipv4-family vpnv4')
                push('policy vpn-target')
                push(f'peer {group_name} enable')
                for rr in rrs:
                    rr_id = parse_id(f'rtrr{rr}')
                    push(f'peer {rr_id} enable')
                    push(f'peer {rr_id} group {group_name}')
            else:
                raise ValueError(obj, args)
        push('quit')


def bgp_rtpe_done(nos):
    for no in nos.split(','):
        cdev_rtpe(no)
        push('quit', 'reset bgp all', 'sys')


def vpn(asno, vpnno):
    global vpn_no, vpn_name
    vpn_no = vpnno
    vpn_name = f'as{asno}-vpn{vpnno}'


def vpn_rtrr(nos, rd, *cmds):
    for no in nos.split(','):
        cdev_rtrr(no)
        vpn_inst(rd, *cmds)


def vpn_rtpe(nos, rd, *cmds):
    for no in nos.split(','):
        cdev_rtpe(no)
        vpn_inst(rd, *cmds)


def vpn_inst(rd, *cmds):
    rd_imports = tuple(filter(
        lambda cmd: cmd.split('=')[0] == 'import',
        cmds
    ))[0].split('=')[1].split(',')
    rd_exports = tuple(filter(
        lambda cmd: cmd.split('=')[0] == 'export',
        cmds
    ))[0].split('=')[1].split(',')

    push(f'undo ip vpn-instance {vpn_name}')
    push(f'ip vpn-instance {vpn_name}')
    push(f'route-distinguisher {rd}')
    for imp in rd_imports:
        push(f'vpn-target {imp} import')
    for exp in rd_exports:
        push(f'vpn-target {exp} export')
    push('quit', 'quit')


def vpn_rtpe_bgp(nos, peer):
    for no in nos.split(','):
        cdev_rtpe(no)
        vpn_bgp(peer)


def vpn_rtrr_bgp(nos, peer):
    for no in nos.split(','):
        cdev_rtrr(no)
        vpn_bgp(peer)


def vpn_rtpe_bind(nos, interface):
    for no in nos.split(','):
        cdev_rtpe(no)
        vpn_bind(interface)


def vpn_rtrr_bind(nos, interface):
    for no in nos.split(','):
        cdev_rtrr(no)
        vpn_bind(interface)


def vpn_bgp(peer):
    bgp_no = f'{asn * 100}'
    push(f'bgp {bgp_no}')
    push(f'ipv4-family vpn-instance {vpn_name}')
    push('import direct')
    ex_asno = parse_vpn_bgp_no()
    group_name = f'EXVPN{ex_asno}'
    push(f'group {group_name} external')
    push(f'peer {group_name} as-number {ex_asno}')
    push(f'peer {peer} as-number {ex_asno}')
    push(f'peer {peer} group {group_name}')
    push('quit', 'quit')


def vpn_bind(interface):
    push(f'inter {interface}')
    push(f'ip binding vpn-instance {vpn_name}')
    cidr = port_cidr[interface]
    n = parse_net(cidr)
    ip = cidr.split('/')[0]
    push(f'ip addr {ip} {n.netmask}')
    push('quit')


def vpn_rtce_bgp(no, peers, *nets):
    cdev_rtce(no)
    vpn_ce_bgp(peers, *nets)


def vpn_lsce_bgp(no, peers, *nets):
    cdev_lsce(no)
    vpn_ce_bgp(peers, *nets)


def vpn_ce_bgp(peers, *nets):
    bgp_no = parse_vpn_bgp_no()
    push(f'bgp {bgp_no}')
    for net in nets:
        net = ip_network(parse_cidr(net))
        push(f'network {net.network_address} {net.netmask}')
    for peer in peers.split(','):
        push(f'peer {peer} as-number {asn * 100}')
    push('quit')


DELAY_CMDS = {
    'undo bgp': (5, 1),
    'undo ip vpn-instance': 40,
}


def dump(write_file=True):
    s = '\n'.join(buf) + '\n'
    if write_file:
        with open(f'cfgs/as{asn}/{dev_name}.in', 'w', encoding='utf-8') as fp:
            fp.write(s)
    telnet_buf = []
    delay: [int, int] | None = None
    for line in buf:
        telnet_buf.append(line)
        for k in DELAY_CMDS.keys():
            if line.startswith(k):
                if type(DELAY_CMDS[k]) is int:
                    telnet_buf.append(DELAY_CMDS[k])
                else:
                    delay = list(DELAY_CMDS[k])
        if delay is not None:
            if delay[1] == 0:
                telnet_buf.append(delay[0])
            delay[1] -= 1
    buf.clear()
    return telnet_buf


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
        t.write(b'\n' * 10)
        for line in s:
            if type(line) is int:
                time.sleep(int(line))
                t.write(('\nsys\n' * 3).encode('utf-8'))
            else:
                t.write((line + '\n').encode('utf-8'))
        # print(t.read_eager())
        t.write(b'\nsubm\n' * 10)
        ts = time.time()
        out = t.read_until(b'subm', timeout=59)
        if write_file:
            with open(f'outs/as{asn}/' + name + '.out', 'wb') as fp:
                fp.write(out)
        if time.time() - ts >= 60:
            t.close()
            raise RuntimeError(f'{name} (:{port}) timed out')
        t.write(b'\b' * 15)
        # print(out.decode('utf-8', errors='ignore'))
        t.close()
        done_vis.add(name)
        print(f'{name} (:{port}) done')

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

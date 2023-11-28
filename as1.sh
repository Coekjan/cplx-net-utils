asn 1

# external devices

extern rtbr1 rtbr2

# ip address

ls 1

rtce 1 202.112.1.1/24:g0/0/1 172.26.15.1/24:g0/0/0

rtrr 1 172.26.15.3/24:g0/0/0 @.1.1.2/24:g0/0/1 @.1.7.1/24:g4/0/1 @.1.9.1/24:g4/0/2 @.1.11.1/24:g4/0/3
rtrr 2 172.26.15.2/24:g0/0/0 @.1.2.2/24:g0/0/1 @.1.8.1/24:g4/0/1 @.1.10.1/24:g4/0/2 @.1.12.1/24:g4/0/3

rtbr 1  # todo
rtbr 2  # todo
rtbr 3 @.1.7.2/24:g4/0/0 @.1.8.2/24:g4/0/1 @.0.0.245/24:g0/0/0
rtbr 4 @.1.9.2/24:g4/0/0 @.1.10.2/24:g4/0/1 @.0.0.241/24:g0/0/0
rtbr 5 @.1.11.2/24:g4/0/0 @.1.12.2/24:g4/0/1 @.0.0.237/24:g0/0/0

# nat

nat-rtce 1 202.112.1.186-202.112.1.196:g0/0/1 172.16.0.0/12

# ospf

ospf-rtrr 1,2 ^172.0.0.0/8
ospf-rtbr 1,2,3,4,5 ^@.0.0.0/16

# mpls

mpls-rtrr 1,2 g0/0/1 g4/0/1 g4/0/2 g4/0/3
mpls-rtbr 1,2  # todo
mpls-rtbr 3,4,5 g0/0/0 g4/0/0 g4/0/1

# bgp

bgp-rtrr 1,2 br=1,2,3,4,5 ex=2{rtrr1,rtrr2}:3{rtrr1,rtrr2}

bgp-rtbr 1,2,3,4,5 rr=1,2
bgp-rtbr 1 ex=2{@.0.0.254} prefer=false
bgp-rtbr 2 ex=2{@.0.0.250} prefer=true
bgp-rtbr 3 ex=3{@.0.0.246} prefer=false
bgp-rtbr 4 ex=3{@.0.0.242} prefer=true
bgp-rtbr 5 ex=3{@.0.0.238} prefer=false

bgp-rtrr-done 1,2
bgp-rtbr-done 1,2,3,4,5

# vpn

vpn-rtrr 1,2 6 100:6 import=300:1,300:2,400:1,400:2,200:7 export=100:6
vpn-rtrr-bgp 1,2 6 172.26.15.1
vpn-rtrr-bind 1,2 6 g0/0/0
vpn-rtce-bgp 1 6 172.26.15.2,172.26.15.3 202.112.1.0/24

asn 2

# external devices

extern rtbr1 rtbr2

# ip address

ls 2

rtce 1 172.27.1.1/24:g0/0/2 172.27.15.3/24:g0/0/1 172.27.15.4/24:g0/0/3

rtrr 1 172.27.15.1/24:g0/0/1 @.2.2.2/24:g0/0/2 @.2.7.1/24:g4/0/1 @.2.8.1/24:g4/0/2
rtrr 2 172.27.15.2/24:g0/0/1 @.2.1.2/24:g0/0/2 @.2.8.1/24:g4/0/1 @.2.10.1/24:g4/0/2

rtbr 1  # todo
rtbr 2  # todo
rtbr 3 @.2.7.2/24:g0/0/1 @.2.9.2/24:g0/0/2 @.0.0.233/24:g4/0/0
rtbr 4 @.2.8.2/24:g0/0/1 @.2.10.2/24:g0/0/2 @.0.0.231/24:g4/0/0
# rtbr 5 #@.1.11.2/24:g4/0/0 @.1.12.2/24:g4/0/1 @.0.0.237/24:g0/0/0

# nat

# nat-rtce 1 202.112.1.186-202.112.1.196:g0/0/1 172.16.0.0/12

# ospf

ospf-rtrr 1,2 ^172.0.0.0/8
ospf-rtbr 1,2,3,4 ^@.0.0.0/16

# mpls

mpls-rtrr 1,2 g0/0/2 g4/0/2 g4/0/1
mpls-rtbr 1,2  # todo
mpls-rtbr 3,4 g0/0/1 g0/0/2

# bgp

bgp-rtrr 1,2 br=1,2,3,4 ex=2{rtrr1,rtrr2}:3{rtrr1,rtrr2}

bgp-rtbr 1,2,3,4 rr=1,2
bgp-rtbr 1 ex=2{@.0.0.253} prefer=false
bgp-rtbr 2 ex=2{@.0.0.249} prefer=true
bgp-rtbr 3 ex=2{@.0.0.234} prefer=false
bgp-rtbr 4 ex=2{@.0.0.230} prefer=true
# bgp-rtbr 5 ex=2{@.0.0.238} prefer=false

bgp-rtrr-done 1,2
bgp-rtbr-done 1,2,3,4

# vpn

vpn-rtrr 1,2 7 200:7 import=300:1,300:2,400:1,400:2,100:6 export=100:6
vpn-rtrr-bgp 1,2 7 172.27.15.3
vpn-rtrr-bind 1,2 7 g0/0/1
vpn-rtce-bgp 1 7 172.27.15.1,172.27.15.2 172.27.1.254/32

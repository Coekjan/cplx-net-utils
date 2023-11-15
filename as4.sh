asn 4

# ip address

## rr 1

rtrr 1 @.4.1.2/24:g0/0/0 @.4.3.2/24:g0/0/1 @.4.11.1/24:g0/0/2
rtrr 1 @.4.5.1/24:g4/0/0 @.4.6.1/24:g4/0/1
rtrr 1 172.24.15.1/24:g4/0/2

## rr 2

rtrr 2 @.4.4.2/24:g0/0/0 @.4.2.2/24:g0/0/1 @.4.11.2/24:g0/0/2
rtrr 2 @.4.7.1/24:g4/0/0! @.4.8.1/24:g4/0/1

## br

rtbr 1 @.0.0.234/24:g0/0/0 @.4.2.1/24:g0/0/1 @.4.1.1/24:g0/0/2
rtbr 2 @.0.0.230/24:g0/0/0 @.4.3.1/24:g0/0/1 @.4.4.1/24:g0/0/2
# rtbr 3 @.0.0.238/24:g0/0/0 @.3.5.1/24:g0/0/1 @.3.6.1/24:g0/0/2

## pe

rtpe 1 @.4.8.2/24:g0/0/0 @.4.10.1:g0/0/1 172.22.31.2/24:g4/0/0 172.21.31.1/24:g0/0/2
rtpe 2 @.4.6.2/24:g0/0/0 @.4.10.2/24:g0/0/1 172.22.31.1/24:g0/0/2
rtpe 3 @.4.7.2/24:g0/0/0 @.4.9.2/24:g0/0/1 172.21.31.2/24:g0/0/2
rtpe 4 @.4.5.2/24:g0/0/0! @.4.9.1/24:g0/0/1 172.21.31.1/24:g0/0/2

## ce

lsce 1 172.24.15.2/24:g0/0/1 172.24.@.2/28:g0/0/2
lsce 2 172.21.31.3/24:g0/0/1 172.21.@.2/29:g0/0/2,g0/0/3
lsce 3 172.21.31.4/24:g0/0/1 172.21.@.1/29:g0/0/2,g0/0/3
lsce 4 172.22.31.3/24:g0/0/1 172.22.@.2/29:g0/0/2,g0/0/3
lsce 5 172.22.31.4/24:g0/0/1 172.22.@.1/29:g0/0/2,g0/0/3
lsce 6 172.22.31.2/24:g0/0/1 172.23.@.2/28:g0/0/2


# ospf

ospf-rtrr 1,2 ^172.0.0.0/8
ospf-rtbr 1,2 ^@.0.0.0/16
ospf-rtpe 1,2,3,4 ^172.0.0.0/8

# mpls

mpls-rtrr 1,2 g0/0/0 g0/0/1 g0/0/2 g4/0/0 g4/0/1
mpls-rtbr 1,2 g0/0/1 g0/0/2
mpls-rtpe 1,2,3,4 g0/0/0 g0/0/1

# bgp

bgp-rtrr 1,2 pe=1,2,3,4 br=1,2 ex=1{rtrr1,rtrr2}

bgp-rtbr 1,2 rr=1,2
bgp-rtbr 1 ex=1{@.0.0.233} prefer=false
bgp-rtbr 2 ex=1{@.0.0.231} prefer=true
# bgp-rtbr 3 ex=1{@.0.0.237}

bgp-rtpe 1,2,3,4 rr=1,2

bgp-rtrr-done 1,2
bgp-rtbr-done 1,2
bgp-rtpe-done 1,2,3,4

# vpn

## vpn 1

vpn-rtrr 1,2 1 400:1 import=300:1,300:5,400:1,100:6,200:7 export=400:1
vpn-rtpe 1,2 1 400:1 import=300:1,300:5,400:1,100:6,200:7 export=400:1
vpn-rtpe-bgp 1 1 172.21.31.3
vpn-rtpe-bgp 2 1 172.21.31.4
vpn-rtpe-bind 1,2 1 g0/0/2
vpn-lsce-bgp 3 1 172.21.31.1 172.21.@.0/29
vpn-lsce-bgp 4 1 172.21.31.2 172.21.@.0/29

## vpn 2

vpn-rtrr 1,2 2 400:2 import=300:2,300:5,400:2,100:6,200:7 export=400:2 
vpn-rtpe 3,4 2 400:2 import=300:2,300:5,400:2,100:6,200:7 export=400:2
vpn-rtpe-bgp 3 2 172.22.31.3
vpn-rtpe-bgp 4 2 172.22.31.4
vpn-rtpe-bind 3,4 2 g0/0/2
vpn-lsce-bgp 5 2 172.22.31.1 172.22.@.0/29 
vpn-lsce-bgp 6 2 172.22.31.2 172.22.@.0/29

## vpn 3

vpn-rtrr 1,2 3 400:3 import=300:3,400:3 export=400:3
vpn-rtpe 4 3 400:3 import=300:3,400:3 export=400:3
vpn-rtpe-bgp 4 3 172.23.31.2
vpn-rtpe-bind 4 3 g0/0/2
vpn-lsce-bgp 2 3 172.23.31.1 172.23.@.0/28

## vpn 4

vpn-rtrr 1,2 4 400:4 import=400:1,400:2 export=400:4
vpn-rtrr-bgp 1 4 172.24.15.2
vpn-rtrr-bind 1 4 g0/0/2
vpn-lsce-bgp 1 4 172.24.15.1 172.24.@.0/28

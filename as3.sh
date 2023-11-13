asn 3

# ip address

## rr 1

rtrr 1 @.3.1.2/24:g0/0/0 @.3.3.2/24:g0/0/1 @.3.5.2/24:g0/0/2
rtrr 1 @.3.7.1/24:g4/0/0 @.3.8.1/24:g4/0/1 @.3.9.1/24:g4/0/2
rtrr 1 172.25.15.1/24:g6/0/0

## rr 2

rtrr 2 @.3.2.2/24:g0/0/0 @.3.4.2/24:g0/0/1 @.3.6.2/24:g0/0/2
rtrr 2 @.3.7.2/24:g4/0/0 @.3.10.1/24:g4/0/1 @.3.11.1/24:g4/0/2

## br

rtbr 1 @.0.0.246/24:g0/0/0 @.3.1.1/24:g0/0/1 @.3.2.1/24:g0/0/2
rtbr 2 @.0.0.242/24:g0/0/0 @.3.3.1/24:g0/0/1 @.3.4.1/24:g0/0/2
rtbr 3 @.0.0.238/24:g0/0/0 @.3.5.1/24:g0/0/1 @.3.6.1/24:g0/0/2

## pe

rtpe 1 @.3.8.2/24:g0/0/0 @.3.12.1/24:g4/0/0 172.23.15.1/24:g6/0/0 172.21.15.1/24:g6/0/1
rtpe 2 @.3.10.2/24:g0/0/0 @.3.12.2/24:g4/0/0 172.21.15.2/24:g6/0/1
rtpe 3 @.3.9.2/24:g0/0/0 @.3.13.1/24:g4/0/0 172.22.15.1/24:g6/0/1
rtpe 4 @.3.11.2/24:g0/0/0 @.3.13.2/24:g4/0/0 172.22.15.2/24:g6/0/1

## ce

lsce 1 172.25.15.2/24:g0/0/1 172.25.1.2/24:g0/0/24
lsce 2 172.23.15.2/24:g0/0/1 172.23.1.2/24:g0/0/24
lsce 3 172.21.15.3/24:g0/0/1 172.21.1.1/24:g0/0/24 172.21.7.1/24:g0/0/13
lsce 4 172.21.15.4/24:g0/0/1 172.21.1.2/24:g0/0/24 172.21.7.2/24:g0/0/13
lsce 5 172.22.15.3/24:g0/0/1 172.22.1.1/24:g0/0/24 172.22.7.1/24:g0/0/13
lsce 6 172.22.15.4/24:g0/0/1 172.22.1.2/24:g0/0/24 172.22.7.2/24:g0/0/13

# ospf

ospf-rtrr 1,2 ^172.0.0.0/8
ospf-rtbr 1,2,3 ^@.0.0.0/16
ospf-rtpe 1,2,3,4 ^172.0.0.0/8

# mpls

mpls-rtrr 1,2 g0/0/0 g0/0/1 g0/0/2 g4/0/0 g4/0/1 g4/0/2
mpls-rtbr 1,2,3 g0/0/1 g0/0/2
mpls-rtpe 1,2,3,4 g0/0/0 g4/0/0

# bgp

bgp-rtrr 1,2 pe=1,2,3,4 br=1,2,3 ex=1{rtrr1,rtrr2}

bgp-rtbr 1,2,3 rr=1,2
bgp-rtbr 1 ex=1{@.0.0.245}
bgp-rtbr 2 ex=1{@.0.0.241}
bgp-rtbr 3 ex=1{@.0.0.237}

bgp-rtpe 1,2,3,4 rr=1,2

bgp-rtrr-done 1,2
bgp-rtbr-done 1,2,3
bgp-rtpe-done 1,2,3,4

asn 2

# ip address

lsce 1 172.27.@.1/28:g0/0/2 172.27.15.3/24:g0/0/1,g0/0/3

rtrr 1 @.2.11.1/24:g0/0/0 172.27.15.1/24:g0/0/1 @.2.2.2/24:g0/0/2 @.2.4.2/24:g4/0/0 @.2.7.1/24:g4/0/1 @.2.8.1/24:g4/0/2
rtrr 2 @.2.11.2/24:g0/0/0 172.27.15.2/24:g0/0/1 @.2.1.2/24:g0/0/2 @.2.3.2/24:g4/0/0 @.2.9.1/24:g4/0/1 @.2.10.1/24:g4/0/2

rtbr 1 @.2.1.1/24:g0/0/1 @.2.2.1/24:g0/0/2 @.0.0.254/24:g0/0/0
rtbr 2 @.2.3.1/24:g0/0/1 @.2.4.1/24:g0/0/2 @.0.0.250/24:g0/0/0
rtbr 3 @.2.7.2/24:g0/0/1 @.2.9.2/24:g0/0/2 @.0.0.233/24:g4/0/0
rtbr 4 @.2.8.2/24:g0/0/1 @.2.10.2/24:g0/0/2 @.0.0.231/24:g4/0/0

# ospf

ospf-rtrr 1,2 ^172.0.0.0/8
ospf-rtbr 1,2,3,4 ^@.0.0.0/16

# mpls

mpls-rtrr 1,2 g0/0/0 g0/0/1 g0/0/2 g4/0/2 g4/0/1 g4/0/0
mpls-rtbr 1,2 g0/0/0 g0/0/1 g0/0/2
mpls-rtbr 3,4 g4/0/0 g0/0/1 g0/0/2

# bgp

bgp-rtrr 1,2 br=1,2,3,4 ex=1{rtrr1,rtrr2}:3{rtrr1,rtrr2}:4{rtrr1,rtrr2}

bgp-rtbr 1,2,3,4 rr=1,2
bgp-rtbr 1 ex=1{@.0.0.253} prefer=false
bgp-rtbr 2 ex=1{@.0.0.249} prefer=true
bgp-rtbr 3 ex=4{@.0.0.234} prefer=false
bgp-rtbr 4 ex=4{@.0.0.230} prefer=true

bgp-rtrr-done 1,2
bgp-rtbr-done 1,2,3,4

# vpn

vpn 1 6
vpn-rtrr 1,2 100:6 import=300:1,300:2,400:1,400:2,200:7 export=100:6

vpn 2 7
vpn-rtrr 1,2 200:7 import=300:1,300:2,400:1,400:2,100:6 export=200:7
vpn-rtrr-bgp 1,2 172.27.15.3
vpn-rtrr-bind 1,2 g0/0/1
vpn-lsce-bgp 1 172.27.15.1,172.27.15.2 172.27.@.0/28

vpn 3 1
vpn-rtrr 1,2 300:1 import=300:1,300:5,400:1,100:6,200:7 export=300:1

vpn 3 2
vpn-rtrr 1,2 300:2 import=300:2,300:5,400:2,100:6,200:7 export=300:2

vpn 3 3
vpn-rtrr 1,2 300:3 import=300:3,400:3 export=300:3

vpn 3 5
vpn-rtrr 1,2 300:5 import=300:1,300:2,400:1,400:2 export=300:5

vpn 4 1
vpn-rtrr 1,2 400:1 import=300:1,300:5,400:1,100:6,200:7 export=400:1

vpn 4 2
vpn-rtrr 1,2 400:2 import=300:2,300:5,400:2,100:6,200:7 export=400:2

vpn 4 3
vpn-rtrr 1,2 400:3 import=300:3,400:3 export=400:3

vpn 4 4
vpn-rtrr 1,2 400:4 import=300:1,300:2,400:1,400:2 export=400:4

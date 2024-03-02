"""Default FRRouting Directives."""

# Project
from hyperglass.models.directive import Rule, Text, BuiltinDirective

__all__ = (
    "OpenBGPD_BGPASPath",
    "OpenBGPD_BGPCommunity",
    "OpenBGPD_BGPRoute",
    "OpenBGPD_Ping",
    "OpenBGPD_Traceroute",
)

OpenBGPD_BGPRoute = BuiltinDirective(
    id="__hyperglass_openbgpd_bgp_route__",
    name="BGP Route",
    rules=[
        Rule(
            condition="0.0.0.0/0",
            action="permit",
            command="bgpctl show rib inet {target}",
        ),
        Rule(
            condition="::/0",
            action="permit",
            command="bgpctl show rib inet6 {target}",
        ),
    ],
    field=Text(description="IP Address, Prefix, or Hostname"),
    platforms=["openbgpd"],
)

OpenBGPD_BGPASPath = BuiltinDirective(
    id="__hyperglass_openbgpd_bgp_aspath__",
    name="BGP AS Path",
    rules=[
        Rule(
            condition="*",
            action="permit",
            commands=[
                "bgpctl show rib inet as {target}",
                "bgpctl show rib inet6 as {target}",
            ],
        )
    ],
    field=Text(description="AS Path Regular Expression"),
    platforms=["openbgpd"],
)

OpenBGPD_BGPCommunity = BuiltinDirective(
    id="__hyperglass_openbgpd_bgp_community__",
    name="BGP Community",
    rules=[
        Rule(
            condition="*",
            action="permit",
            commands=[
                "bgpctl show rib inet community {target}",
                "bgpctl show rib inet6 community {target}",
            ],
        )
    ],
    field=Text(description="BGP Community String"),
    platforms=["openbgpd"],
)

OpenBGPD_Ping = BuiltinDirective(
    id="__hyperglass_openbgpd_ping__",
    name="Ping",
    rules=[
        Rule(
            condition="0.0.0.0/0",
            action="permit",
            command="ping -4 -c 5 -I {source4} {target}",
        ),
        Rule(
            condition="::/0",
            action="permit",
            command="ping -6 -c 5 -I {source6} {target}",
        ),
    ],
    field=Text(description="IP Address, Prefix, or Hostname"),
    platforms=["openbgpd"],
)

OpenBGPD_Traceroute = BuiltinDirective(
    id="__hyperglass_openbgpd_traceroute__",
    name="Traceroute",
    rules=[
        Rule(
            condition="0.0.0.0/0",
            action="permit",
            command="traceroute -4 -w 1 -q 1 -s {source4} {target}",
        ),
        Rule(
            condition="::/0",
            action="permit",
            command="traceroute -6 -w 1 -q 1 -s {source6} {target}",
        ),
    ],
    field=Text(description="IP Address, Prefix, or Hostname"),
    platforms=["openbgpd"],
)
# VPN architecture research

Status: decision required; no VPN architecture was changed by this report.

## Evidence

Android's [`VpnService` guide](https://developer.android.com/develop/connectivity/vpn) requires the
service to call `prepare()`, `protect()` its upstream sockets, configure a TUN interface, and
call `establish()`. [`VpnService.Builder.addRoute`](https://developer.android.com/reference/android/net/VpnService.Builder#addRoute(java.lang.String,%20int))
supports IPv4 and IPv6 routes and longest-prefix selection. Android documents only one active VPN
connection at a time in [`VpnService`](https://developer.android.com/reference/kotlin/android/net/VpnService).
Always-on VPN can restart a service at boot, but Android still leaves gateway connection handling
to the application. [`VpnManager`](https://developer.android.com/reference/android/net/VpnManager)
is preferable only for supported platform VPN protocols; it does not provide a general-purpose
local packet inspection/filtering replacement for this product.

## Options

| Option | Fidelity retained | Battery / throughput | License / maintenance | §10.5–§10.7 impact |
| --- | --- | --- | --- | --- |
| **A. Full-route TUN + mature stack** | Highest practical fidelity. DNS and IP rules can be enforced; QUIC remains inspectable as UDP/443, but encrypted QUIC metadata is limited. DoH can only be blocked by endpoint/IP policy or by controlling DNS; it cannot be classified by domain after encryption without a stronger interception design. Per-app attribution is not automatic from TUN packets and needs Android UID/socket correlation or explicit app routing. | Every device flow crosses the TUN and userspace stack. More CPU, wakeups, memory, latency, and battery than selective routing; mature TCP/UDP implementations should avoid the correctness failures of the current path and provide materially better throughput. | `xjasonlyu/tun2socks` reports gVisor TCP/IP, IPv4/IPv6 and MIT licensing, with active releases (latest observed v2.7.0). `heiher/hev-socks5-tunnel` reports dual-stack TCP/UDP Android support and MIT licensing. Both require pinned revisions, native ABI packaging, CVE/license scanning, and an owned integration/test surface; upstream activity is not a substitute for maintenance ownership. gVisor and other transitive dependencies must be reviewed separately. | Best fit for the full §10.5 flow/IP attribution ambition, §10.6 DNS/domain enforcement, and §10.7 QUIC/UDP-443 handling. Still does not make encrypted DoH or app attribution magically observable. Requires replacing the hand-rolled TCP path before ship. |
| **B. Selective routes** | DNS traffic and explicitly routed blocked IP ranges can be enforced. Ordinary IP traffic, QUIC to destinations not in the route set, DoH endpoints outside the route set, and non-DNS domain attribution bypass Guardian. Per-app attribution is correspondingly limited; `addAllowedApplication`/`addDisallowedApplication` selects apps for the VPN but does not identify arbitrary packet ownership inside a shared TUN. | Lower CPU, memory, wakeups and latency for ordinary traffic; better battery and throughput. DNS and blocked-range traffic still pay TUN/userspace costs. Lower blast radius and less code to audit. | No third-party TCP stack is required for bypassed traffic, reducing dependency/licensing and maintenance risk. The route list, DNS behavior, IPv4/IPv6 parity, and policy update synchronization become the main maintenance surface. | Satisfies DNS blocking and selected IP blocking, but weakens §10.5 non-DNS attribution and IP fidelity and cannot honestly claim comprehensive §10.7 QUIC/DoH enforcement. It is the safer degraded/minimal architecture if product requirements accept those losses. |
| **C. Platform-managed VPN profile / per-app VPN** | Android platform ownership improves lifecycle handling, but `VpnManager`/platform profiles are for supported VPN protocols, not an arbitrary local policy inspection engine. Per-app selection can scope which apps enter a VPN, but does not solve domain inspection, encrypted DoH, QUIC classification, or packet-to-app attribution by itself. | Potentially lower application lifecycle burden; performance depends on the supported protocol and gateway. It does not remove the need for a gateway or inspection component for Guardian's policy requirements. | Less custom lifecycle code, but protocol/profile constraints and Android-version behavior become hard dependencies. No direct replacement for a local TUN forwarding stack was found in official Android documentation. | Useful as a lifecycle/scoping primitive, not a complete §10.5–§10.7 implementation. It cannot satisfy the current device-wide enforcement requirements alone. |

## Recommendation for decision

Do not ship the current hand-rolled full-route TCP path. If device-wide IP/QUIC enforcement and
the current §10.5–§10.7 fidelity are mandatory, choose **A** and run a pinned, audited mature
userspace stack behind the existing policy/DNS layer. If minimizing attack surface and battery is
the priority and product accepts explicit loss of non-DNS enforcement and attribution, choose
**B**. **C** is complementary rather than a standalone replacement. No option removes the need
to report degraded capability when VPN consent is revoked, another VPN wins, the network is
unavailable, or policy state is unavailable; ordinary connectivity must remain unbricked.

# Slice 1.7 acceptance evidence

## Post-change implementation

Blocked-domain upstream resolution landed in
`GuardianVpnService.handleDns`. For a domain that matches the compiled local
policy snapshot, the service:

1. resolves the original question upstream;
2. issues the opposite-family A/AAAA question when needed;
3. stores bounded TTL-aware leases in `DnsCache`;
4. adds the learned addresses to the selective blocked-destination route set;
5. rebuilds the TUN interface when the route set changes; and
6. only then returns the sinkhole response to the client.

If upstream resolution fails, the blocked DNS request is still sinkholed. An
allowed request with an unavailable upstream reports degradation instead of
returning malformed data.

## Evidence

The post-change run used `example.org` as the blocked domain and `example.com`
as the allowed domain. The existing clean artifacts were generated after the
upstream-resolve-then-route implementation and are retained under the
gitignored emulator scratch directory:

| Acceptance assertion | Evidence |
| --- | --- |
| Blocked resolver request fails | `.scratch/emulator/option-b-v7-blocked-example-org.png` and `option-b-v7-blocked-logcat.txt` |
| Learned blocked A/AAAA destinations are visible in routes | `.scratch/emulator/option-b-v7-routes-settled.txt` |
| Direct access to a learned blocked IPv6 destination fails | `.scratch/emulator/option-b-v7-direct-ipv6-final.png` and `option-b-v7-direct-ipv6-final-logcat.txt` |
| Allowed `example.com` succeeds in the same acceptance set | `.scratch/emulator/option-b-v7-allowed-example-com.png` and `option-b-v7-allowed-logcat.txt` |
| Exactly one semantic block event, with attribution | `.scratch/emulator/option-b-v7-direct-ipv6-final-logcat.txt` |
| No packet-level bridge event | same filtered logcat artifact |
| VPN revocation degrades protection | `option-b-v7-vpn-revoked.png` and `option-b-v7-vpn-revoked-logcat.txt` |
| Re-consent restores protection | `option-b-v7-vpn-reconsent-final.png` and `option-b-v7-vpn-reconsent-final-logcat.txt` |
| Backend-down ordinary connectivity remains available | `option-b-v7-backend-down-allowed.png` |
| No-policy ordinary connectivity remains available | `option-b-v7-no-policy-allowed-final.png` |
| Reboot restores persisted policy/VPN state | `option-b-v7-reboot-final-logcat.txt`, `option-b-v7-reboot-final-routes.txt`, and `option-b-v7-reboot-blocked.png` |

The settled route dump includes the learned public destinations:

```text
2606:4700:10::6814:1a88/128
2606:4700:10::ac42:9ded/128
```

The clean semantic event is:

```json
{
  "type": "WEB_BLOCKED",
  "domain": "example.org",
  "category": null,
  "appRef": "com.android.chrome",
  "reasonCode": "EXPLICIT_TARGET_RULE"
}
```

The filtered artifact reports `count=1` and contains no packet-level event.
The route dump also contains only resolver and learned blocked-destination
routes; no default route is installed.

## Fresh re-confirmation

The same behavior was re-run against policy version 17 after the mobile
surface work. The parent mutation output was:

```text
DOMAIN_BLOCK example.org -> policy_version=16
DOMAIN_ALLOW example.com -> policy_version=17
```

The clean Chrome run produced a learned route and exactly one attributed
semantic event:

```text
2606:4700:10::6814:1a88/128 -> tun0
WEB_BLOCKED {"domain":"example.org","category":null,
  "appRef":"com.android.chrome","reasonCode":"EXPLICIT_TARGET_RULE"}
web_blocked_count=1
```

Evidence:

```text
.scratch/emulator/slice17-final2-blocked-resolver.png
.scratch/emulator/slice17-final2-direct-ip.png
.scratch/emulator/slice17-final2-allowed.png
.scratch/emulator/slice17-final2-routes-after-resolve.txt
.scratch/emulator/slice17-final2-semantic-events.txt
.scratch/emulator/slice17-final2-event-count.txt
```

The filtered capture contained no packet-level bridge event. The lifecycle
and connectivity evidence remains in the `option-b-v7-*` artifacts listed
above.

## Limitations

The direct-IP assertion was captured against the learned public IPv6 address.
The emulator run did not separately capture a fresh IPv4 direct-IP screenshot
for the same hostname. Captive-portal and competing-VPN behavior remain
implementation/test evidence rather than separate live acceptance scenarios.

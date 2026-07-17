# Security Policy

## Supported Versions

The `main` branch and the latest tagged release, when one exists, receive
security fixes. Older research snapshots are not guaranteed to receive
backported fixes.

## Reporting a Vulnerability

Use the repository host's vulnerability reporting feature if it is enabled. If
that feature is unavailable, open a minimal issue that requests a maintainer
contact channel without disclosing exploit details, secret material, cluster access
material, or unpublished run data.

Please include:

- affected version or commit;
- affected component, command, or benchmark helper;
- reproduction steps using synthetic or redacted data;
- expected and observed impact.

Do not include live secret material, cluster access files, SSH keys, service
account tokens, raw cluster dumps, or unredacted infrastructure identifiers in
public issues, pull requests, or artifact data.

## Scope

Security-relevant areas include package code, benchmark fetch and deploy
helpers, run-ledger handling, network-emulation helpers, and artifact
validation scripts. Live-cluster helpers are intended for controlled testbeds
and should not be run against shared or production clusters without explicit
operator approval.

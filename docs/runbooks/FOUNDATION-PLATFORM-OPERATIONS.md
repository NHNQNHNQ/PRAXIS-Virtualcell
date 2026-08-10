# Foundation Platform Operations Runbook

> Status: `TEMPLATE_ONLY / NOT_DEPLOYED`
>
> Product candidate: `1.7.0 LOCAL_RC_INCOMPLETE / UNPUBLISHED`
>
> This runbook is documentation, not deployment authority. P30B1–P30B4 are
> `NOT_AUTHORIZED / NOT_RUN`. No command or template below may be applied to staging,
> production, `.53`, an existing service, port, secret store, certificate, monitor, backup or
> traffic path without one complete, exact authorization window.

## 1. Operating invariants

1. Freeze one exact source SHA, wheel/OCI digest, release manifest digest and capability
   classification digest before any external change.
2. Use a new immutable deploy ref, directory, service instance and port. Never overwrite a
   running version or move a tag/ref.
3. Bind health evidence to `product_version`, `api_protocol_version`,
   `runtime_protocol_version` and full `git_sha`; an HTTP 200 alone is insufficient.
4. Keep the service offline by default. LLM credentials, external data, weights and model
   endpoints are separate authorization and trust boundaries.
5. Preserve engineering, science and product policy as independent states. Deployment cannot
   promote a biological capability.
6. Keep old application bytes and restorable run data until the authorized rollback observation
   is complete.
7. Stop on a hash, identity, scope, permission, health, privacy or rollback mismatch. Do not repair
   an external system outside the approved window.

## 2. Authorization freeze record

Every value in this table must be concrete, reviewed and recorded before the corresponding
external action. `<UNSET>` is a stop condition, not a wildcard.

| Surface | Values that must be frozen | Earliest window | Without approval |
|---|---|---|---|
| source and release | exact 40-hex SHA, branch/ref, version, commit epoch, capability-classification digest, release-manifest digest | P30B1 | no push or remote CI |
| artifacts | wheel/OCI filenames, sizes, SHA-256, SBOM/licence/audit/provenance digests, source, write-new destination | P30B2 | no upload, publication, signing or tag |
| staging target | host, owner, new deploy ref, new directory, new port, local/remote network boundary, approved run-data path | P30B3 | no remote read/write, copy or directory creation |
| systemd | new unit name, unit bytes/digest, service user/group, executable path, environment-file path, start/stop/restart commands | P30B3; P30B4 separately for production | no unit install, daemon reload or service change |
| logs | sink, retention, rotation size/time, ownership/mode, redaction rules, approved readers, deletion/restore policy | P30B3 | stdout/journal only in an authorized isolated instance; no existing-log changes |
| secrets | exact secret names, issuer/source, recipient service, storage path/provider, mode/owner, expiry/rotation/revocation plan; never secret values in the record | separate secret authorization plus P30B3/P30B4 | offline mode; no secret read, copy, print or creation |
| TLS and ingress | DNS/hostnames, certificate identity/source/digest or managed issuer, listener, upstream address, allowed methods/body limits, firewall/proxy changes | P30B3; P30B4 separately for production | loopback-only service; no certificate, DNS or ingress change |
| monitoring | health URL, exact expected identity, interval/timeouts, alert destinations, data-retention/privacy boundary, owner | P30B3 | local smoke evidence only; no external telemetry or alerts |
| backup | exact source paths/data class, destination, encryption/key owner, retention, size/hash manifest, exclusion list and restore objective | P30B3/P30B4 as scoped | no backup read/write or user-data copy |
| restore | exact backup manifest/digest, fresh restore target, validation suite, allowed reads/writes, owner and cleanup/retention decision | P30B3/P30B4 as scoped | no overwrite and no restore into a live path |
| production traffic | old/new endpoints, change time, approver/operator, ramp/observation plan, abort thresholds | P30B4 | no traffic or production configuration change |
| rollback | previous immutable ref/artifact/config/data snapshot, rollback trigger, exact switch commands, verification, maximum decision time and final keep/remove decision | P30B4 | no production action; rollback remains untested |

The authorization record must also name prohibited actions. At minimum: no force push, tag move,
history rewrite, mutable artifact overwrite, undeclared asset/model access, secret disclosure,
unapproved port/traffic change or cleanup of pre-existing files.

## 3. Immutable layout template

The following names are placeholders only. An approved deployment must replace every value and
must use a path that does not already exist.

```text
<APPROVED_DEPLOY_ROOT>/
  releases/<EXACT_GIT_SHA>/        # read-only wheel or extracted runtime
  manifests/<EXACT_GIT_SHA>/       # release manifest, checksums, SBOM, licence, audit
  config/<EXACT_GIT_SHA>/          # non-secret configuration
  current -> releases/<EXACT_GIT_SHA>  # create/switch only in the approved window

<APPROVED_STATE_ROOT>/
  runs/                             # separately backed-up mutable state
```

Do not place secrets in the release tree, OCI labels, command line, Git, logs, SBOM or provenance.
Do not make `current` point at a candidate until its separately authorized smoke gate passes.

## 4. systemd template

This fragment is not installed anywhere. The approved unit must use a new service name and exact
paths, and its bytes must be hashed in the authorization record.

```ini
[Unit]
Description=PRAXIS-VirtualCell <EXACT_GIT_SHA>
After=network.target

[Service]
Type=simple
User=<APPROVED_SERVICE_USER>
Group=<APPROVED_SERVICE_GROUP>
WorkingDirectory=<APPROVED_DEPLOY_ROOT>/releases/<EXACT_GIT_SHA>
Environment=PRAXIS_VIRTUALCELL_MODE=offline
Environment=PRAXIS_VC_RUNS=<APPROVED_STATE_ROOT>/runs
Environment=GIT_SHA=<EXACT_GIT_SHA>
EnvironmentFile=-<APPROVED_SECRET_FILE_IF_SEPARATELY_AUTHORIZED>
ExecStart=<APPROVED_VENV>/bin/praxis-vc serve --host 127.0.0.1 --port <APPROVED_NEW_PORT>
Restart=on-failure
RestartSec=5s
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=<APPROVED_STATE_ROOT>/runs
UMask=0027

[Install]
WantedBy=multi-user.target
```

Absent explicit secret authorization, omit `EnvironmentFile` entirely. P30B3 may authorize a new
staging unit only; it does not authorize modifying, stopping or restarting an existing production
unit. P30B4 must name the exact unit commands and expected pre/post state.

## 5. Logs, secrets and TLS

### Logs

Prefer service stdout/stderr to an approved journal sink. Freeze retention and access policy before
enabling persistence. Logs may include timestamps, stable error/abstain codes, product version,
full candidate SHA and request/job identifiers that are safe for the approved data class. They must
not include prompts containing private data, uploaded content, raw biological data, filesystem
secrets, credentials, tokens, environment dumps or unredacted exception text.

If file logging is explicitly approved, use a new service-specific directory owned by the service
account and a separately reviewed rotation rule. Rotation must never glob a shared log root, follow
symlinks or delete pre-existing logs. `vc_api.log` is protected and outside this runbook.

### Secrets

Offline serving requires no API key. A later LLM-assisted window must freeze the exact secret name,
consumer, source, expiry and revocation plan. Store the value only in the approved secret provider
or a root-owned `0600` environment file; pass the path, never the value, through the unit. Do not use
checked-in `.env` files, shell history, command-line values or diagnostic environment dumps.

### TLS and ingress

Keep the application listener on `127.0.0.1:<APPROVED_NEW_PORT>` and terminate TLS at a separately
approved reverse proxy or ingress. Freeze hostname, certificate identity/issuer, protocol/cipher
policy, request-size and timeout limits, forwarded-header trust and allowed paths. The proxy must
not rewrite `/api/health` identity fields or broaden CORS/upload policy. No DNS, firewall,
certificate or proxy mutation belongs to P30A.

## 6. Monitoring template

The minimum staging probe is a loopback request to `/api/health` followed by exact field checks:

```text
status == "ok"
product_version == "1.7.0"
git_sha == <EXACT_GIT_SHA>
api_protocol_version == <EXPECTED_API_PROTOCOL>
runtime_protocol_version == <EXPECTED_RUNTIME_PROTOCOL>
```

An approved monitor must also freeze interval, timeout, consecutive-failure threshold, latency/error
budgets, disk-space threshold for the runs volume, alert recipient and retention/privacy boundary.
Do not send request bodies, reports or biological values to an external telemetry service unless
that exact data flow is separately approved. A green health endpoint proves service identity and
liveness, not scientific validity or prediction availability.

## 7. Backup and restore

### Backup template

1. Freeze the mutable source set, exclusions and data classification. Application artifacts are
   reproduced from immutable digests; mutable `runs/` data is a separate scope.
2. Choose a new approved destination and encryption/key owner. Never infer authorization from free
   space or an existing backup directory.
3. Record start/end time, file count, byte count and a SHA-256 manifest without copying secret
   values into the record.
4. Preserve the source; backup does not authorize deletion, compaction or retention changes.

### Restore template

1. Verify the approved backup manifest and encryption identity before reading payload data.
2. Restore into a new empty target, never over a live or pre-existing path.
3. Recompute the manifest, validate ownership/modes and run the approved read-only application
   checks against the fresh target.
4. Record success or the exact negative result. Do not switch the service to the restored data as
   part of the rehearsal unless that switch is explicitly authorized.

A backup is not accepted until a restore rehearsal has produced immutable evidence for the same
backup identity and recovery objective.

## 8. Staging and production sequence

### P30B3 — immutable staging

After P30B1/P30B2 prerequisites named by the release governance are satisfied, a separately
authorized P30B3 window may:

1. verify the target and candidate identities without changing existing state;
2. create one new deploy directory, state directory, service instance and port;
3. copy only the approved immutable artifacts and reviewed non-secret configuration;
4. start only the new staging instance;
5. verify exact health identity, non-root execution, persistence boundaries, static UI and the
   approved offline abstention smoke;
6. stop and preserve evidence on any mismatch.

P30B3 does not switch production traffic, modify an existing service or prove a real biological
model.

### P30B4 — production and real rollback

A distinct maintenance-window authorization must freeze the old and new immutable deployments,
traffic commands, operator, observation period, abort thresholds and rollback commands. The
operator may then perform the approved traffic switch, monitor the frozen signals and execute an
actual rollback to the exact previous deployment. Rollback acceptance requires rechecking the old
version/SHA and service behavior after traffic returns; a dry-run command review is not sufficient.

After rollback verification, the operator must explicitly choose the final serving version. Keep
both immutable deployments and all evidence until the approved retention decision; do not
automatically delete the candidate or previous release.

## 9. Evidence record

For every authorized run, retain an append-only record containing:

- authorization window, named operator/approver and timestamps;
- exact old/new SHA, artifact and configuration digests;
- target host/ref/directory/port without secrets;
- preflight and postflight service/status identities;
- health, smoke, monitoring and backup/restore results, including failures;
- traffic and rollback actions actually performed;
- final serving version and explicit cleanup/retention decision;
- confirmation that no science or product-policy status changed.

Until such a record exists, this runbook remains `TEMPLATE_ONLY / NOT_DEPLOYED`, and P30B1–P30B4
remain `NOT_AUTHORIZED / NOT_RUN`.

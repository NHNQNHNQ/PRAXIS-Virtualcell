# External-Disk Git Maintenance — Non-Destructive Runbook

> Status: `REVIEWED_RUNBOOK — CLEANUP REQUIRES EXPLICIT APPROVAL`
>
> Applies to Git worktrees on ExFAT/removable media that may create AppleDouble `._*` files, including inside `.git/objects`.

The safe recovery order is inventory → verified APFS recovery material → clone/restore → bidirectional verification → make the source read-only. Cleanup is optional, separate, and never a prerequisite for continuing work in the APFS clone.

## Red lines

- Do not run `git gc`, `git prune`, `git repack`, `git clean`, `reset --hard`, force-push, history rewrite, or `find ... -delete` on the contaminated source.
- Do not manually edit `.git` files or remove object paths because their names look like sidecars.
- Do not use a broad path such as `$HOME`, `~`, `/`, a volume root, or an unresolved glob as a copy/quarantine target.
- Do not read or print secret files. Record ignored secret paths and sizes only; back them up only through an approved secure channel.
- Do not make the bundle path the repository's GitHub `origin`.

## 1. Resolve explicit paths and freeze source state

Use task-specific variables with fully resolved paths:

```bash
SOURCE_REPO=/absolute/exfat/path/to/repo
RECOVERY_DIR=/absolute/apfs/path/to/recovery-directory
TARGET_REPO=/absolute/apfs/path/to/new-clone

test -d "$SOURCE_REPO/.git"
test ! -e "$TARGET_REPO"
mkdir -p "$RECOVERY_DIR"
```

Collect without modifying the source:

```bash
git -C "$SOURCE_REPO" status --porcelain=v1 --branch
git -C "$SOURCE_REPO" show-ref --head
git -C "$SOURCE_REPO" stash list
git -C "$SOURCE_REPO" ls-tree -r --name-only refs/stash^3
git -C "$SOURCE_REPO" remote -v
git -C "$SOURCE_REPO" branch -vv
df -h "$SOURCE_REPO" "$RECOVERY_DIR"
find "$SOURCE_REPO" -name '._*' -type f
```

Save the outputs in the APFS recovery directory. From this point, treat the source repository as a logical read-only archive.

## 2. Build APFS recovery material

Create committed-history recovery:

```bash
git -C "$SOURCE_REPO" bundle create "$RECOVERY_DIR/repo-all.bundle" --all
git bundle verify "$RECOVERY_DIR/repo-all.bundle"
git bundle list-heads "$RECOVERY_DIR/repo-all.bundle"
shasum -a 256 "$RECOVERY_DIR/repo-all.bundle"
```

Save tracked WIP separately with explicit protected paths:

```bash
git -C "$SOURCE_REPO" diff --binary -- path/to/wip-a path/to/wip-b > "$RECOVERY_DIR/wip.patch"
git -C "$SOURCE_REPO" diff --check -- path/to/wip-a path/to/wip-b
shasum -a 256 "$RECOVERY_DIR/wip.patch"
```

Inventory and copy only named untracked/user assets, excluding AppleDouble:

```bash
rsync -a --exclude='._*' "$SOURCE_REPO/path/to/untracked-asset" "$RECOVERY_DIR/untracked/"
```

Large ignored scientific data need an explicit asset list and source/target hashes. Rebuildable environments, caches, dependencies, build output, and test output should normally be reconstructed rather than copied. For `.env` or keys, record only path, ignored-rule source, and byte size until the user selects a secure backup method.

## 3. Check source connectivity read-only

```bash
git -C "$SOURCE_REPO" rev-list --objects --all --missing=print
git -C "$SOURCE_REPO" fsck --full
```

Stop on any missing/corrupt object. Record dangling commits or garbage/AppleDouble warnings separately; do not “fix” them in place.

## 4. Restore into a new APFS repository

Initialize with an intentionally unused unborn branch so local `main` can be fetched safely:

```bash
git init --initial-branch=__recovery_unborn__ "$TARGET_REPO"
git -C "$TARGET_REPO" remote add recovery "$RECOVERY_DIR/repo-all.bundle"
git -C "$TARGET_REPO" fetch recovery \
  '+refs/heads/*:refs/heads/*' \
  '+refs/tags/*:refs/tags/*' \
  '+refs/remotes/*:refs/remotes/*' \
  '+refs/stash:refs/stash' \
  '+refs/codex/*:refs/codex/*'
```

Add the recorded GitHub URL explicitly, switch the source HEAD branch, and restore upstream metadata:

```bash
git -C "$TARGET_REPO" remote add origin git@github.com:OWNER/REPOSITORY.git
git -C "$TARGET_REPO" switch source-head-branch
git -C "$TARGET_REPO" branch --set-upstream-to=origin/source-head-branch source-head-branch
git -C "$TARGET_REPO" branch --set-upstream-to=origin/main main
```

Restore the WIP only after a dry check, then copy the named assets:

```bash
git -C "$TARGET_REPO" apply --check "$RECOVERY_DIR/wip.patch"
git -C "$TARGET_REPO" apply "$RECOVERY_DIR/wip.patch"
rsync -a --exclude='._*' "$RECOVERY_DIR/untracked/" "$TARGET_REPO/"
```

Bundles preserve `refs/stash` and stash objects but not reflogs. If `git stash list` must expose `stash@{0}`, reconstruct that reflog only in the new clone, only after verifying the exact stash OID exists in the bundle, and keep the bundle/manifest unchanged as rollback authority.

## 5. Verify source and clone

Compare named protected namespaces from source and target before creating new branches:

```bash
git -C "$SOURCE_REPO" for-each-ref --format='%(refname) %(objectname)' \
  refs/heads refs/tags refs/remotes/origin refs/stash refs/codex
git -C "$TARGET_REPO" for-each-ref --format='%(refname) %(objectname)' \
  refs/heads refs/tags refs/remotes/origin refs/stash refs/codex
```

Then run:

```bash
git -C "$TARGET_REPO" rev-list --objects --all --missing=print
git -C "$TARGET_REPO" fsck --full
find "$TARGET_REPO/.git" -name '._*' -type f
git -C "$TARGET_REPO" status --short --branch
git -C "$TARGET_REPO" stash list
git -C "$TARGET_REPO" rev-parse HEAD main refs/stash
```

Required results: protected ref OIDs match, missing count is zero, fsck has no corrupt/missing diagnostics, target `.git` has zero AppleDouble files, and the restored WIP/assets match their saved hashes/status.

Write a recovery manifest containing paths, filesystem types, refs, worktree inventory, ignored-secret metadata, asset hashes, commands, exit codes, and known caveats. Make the verified bundle and manifest read-only.

## 6. Cut over and retain rollback

- Perform all development/test/release work in the verified APFS clone.
- Keep the ExFAT repository unchanged as an archive until the project is released and all recovery evidence is independently backed up.
- Keep the verified bundle, WIP patch, checksum manifest, and any stash/untracked export through final GitHub/local/deployment synchronization.
- Rebuild virtual environments and frontend dependencies from declared manifests on APFS.

## 7. Optional AppleDouble maintenance window

This consolidation does not perform source cleanup. If a later user-approved maintenance window requires it:

1. Re-verify the APFS clone and bundle immediately before touching the archive.
2. Create an explicit sibling quarantine directory on APFS with a timestamp and manifest.
3. Use a reviewed script to move only resolved `._*` paths into quarantine while preserving their source-relative paths; do not delete and do not operate on ordinary object names.
4. Do not run Git gc/repack/prune on ExFAT.
5. Re-run source `fsck --full`, missing-object checks, ref comparison, and APFS-clone checks.
6. On any discrepancy, stop and restore quarantined files to their exact original paths.
7. Delete quarantine only after a separate approval and retention decision.

The preferred long-term model is to keep active Git repositories on APFS and use ExFAT only for verified bundle/checksum/manifest copies, not as development truth.

The 2026-07-18 execution evidence for this repository is recorded in [Project State](../status/PROJECT-STATE-2026-07-18.md) and the external APFS recovery manifest.

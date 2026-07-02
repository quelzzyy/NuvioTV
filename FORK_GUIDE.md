# Keeping Custom Features While Auto-Updating

This copy of NuvioTV carries custom features on top of the official
[tapframe/NuvioTV](https://github.com/tapframe/NuvioTV) code. This document
explains how updates work and how to keep receiving upstream improvements
without losing the custom features.

## Custom features in this build

- **Sleep timer** — in the player, open the "more actions" row (arrow button
  in the controls) and choose the moon icon. Playback pauses automatically
  after 15–120 minutes. The timer can be cancelled from the same dialog.
- **Random episode** — series detail pages show a shuffle button next to
  Play. It picks a random aired episode from any season and starts it.
- **Fork-aware updater** — `UPDATER_GITHUB_OWNER` / `UPDATER_GITHUB_REPO` in
  `local.properties` redirect the in-app updater to your own fork's GitHub
  Releases (defaults to the official repo when unset).

## Why the stock auto-updater can't be used as-is

Two hard facts about Android and this app:

1. **APK signatures.** A self-built APK is signed with *your* key. Official
   releases are signed with the developer's key. Android refuses to install
   one over the other, so the stock updater would download official APKs and
   fail to install them — and even if it could, an official APK would not
   contain your custom features.
2. **The updater checks one repo.** It reads the latest GitHub release of
   `GITHUB_OWNER/GITHUB_REPO` and compares the tag against the installed
   `versionName`.

So the working model is: **your devices auto-update from *your* fork, and
your fork stays synced with the official repo.** Every release you publish =
latest official code + your features.

## One-time setup

1. **Fork** `tapframe/NuvioTV` on GitHub (e.g. `youruser/NuvioTV`).
2. Push this repo there:
   ```
   git remote add origin https://github.com/youruser/NuvioTV.git
   git push -u origin my-features
   ```
   (`upstream` already points at the official repo; your commits live on the
   `my-features` branch, based on the official `0.7.13-beta` tag.)
3. In `local.properties` (and in the `LOCAL_PROPERTIES_BASE64` secret if you
   use the CI release workflow), set:
   ```
   UPDATER_GITHUB_OWNER=youruser
   UPDATER_GITHUB_REPO=NuvioTV
   ```
4. Optional but recommended for CI releases — add the signing secrets used by
   `.github/workflows/beta-release.yml` to your fork:
   `NUVIO_RELEASE_KEYSTORE_BASE64`, `NUVIO_RELEASE_KEY_ALIAS`,
   `NUVIO_RELEASE_KEY_PASSWORD`, `NUVIO_RELEASE_STORE_PASSWORD`, and
   `LOCAL_PROPERTIES_BASE64` (base64 of your `local.properties`).
   **Always sign with the same keystore**, otherwise devices can't upgrade in
   place. Without secrets the workflow falls back to debug signing, which
   also works as long as it's consistent.

## Staying up to date with the official app

Two options — use either or both:

- **Automatic:** the `Sync Upstream` workflow
  (`.github/workflows/sync-upstream.yml`) merges the official `main` branch
  into `my-features` every Monday (or on demand from the Actions tab). If a
  merge conflicts with your features, the run fails and you resolve it
  locally.
- **Local:** run `powershell -ExecutionPolicy Bypass -File
  scripts\sync-upstream.ps1` from the repo root. Same merge, on your machine.

## Publishing an update to your devices

After syncing (or adding a feature), publish a release on your fork with the
existing **Beta Release** workflow (Actions → Beta Release → `publish`).
Version rules:

- The tag must compare *newer* than the installed `versionName`
  (numeric parts, e.g. `0.7.13-beta` = `0.7.13`). After merging official
  `0.7.14-beta`, tag yours `0.7.14-beta.1` (the extra `.1` sorts above
  `0.7.14`). For a custom-only release on the same base, bump the last part:
  `0.7.14-beta.2`.
- Publish as a **full release** — the updater ignores drafts and
  prereleases.

Devices running your build then see the update in-app, download your APK, and
install it — official improvements and custom features included.

## Day-to-day development

- Keep every custom change as a commit on `my-features`; never commit to
  `master` (it mirrors the official tag).
- Prefer additive changes (new files, small hooks in existing ones) — they
  merge cleanly when upstream changes.
- Build: `.\gradlew :app:assembleFullDebug` (use JDK 17–21, e.g. Android
  Studio's bundled JBR; Gradle 8.13 does not run on newer JDKs like 26).

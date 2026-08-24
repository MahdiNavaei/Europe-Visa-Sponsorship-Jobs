# Career Radar for Windows

The Windows release is the easiest way to run Career Radar locally. It is self-contained and does not require users to install Python, Node.js, Docker, PostgreSQL, npm packages, pip packages, or any project dependency.

## Install

1. Open the GitHub **Releases** page.
2. Download the setup file matching the release version (for example, `CareerRadar-Setup-v1.1.0.exe`).
3. Run the installer.
4. Launch **Career Radar** from the Start menu (or create the optional desktop shortcut).

On first launch, the v1.1 release package will:

- creates a local SQLite database,
- applies the database migrations,
- starts the bundled FastAPI backend,
- starts the bundled production Next.js application with its bundled Node runtime,
- bootstraps the generated live-verified source registry and official sponsor-evidence cache,
- opens the application in the default browser as soon as the local API and web
  server are ready, and
- synchronizes the central catalog in a background worker.

No development tools are required.

## Local data

User data is stored outside the installation folder under:

```text
%LOCALAPPDATA%\CareerRadar
```

This includes the SQLite database, refresh metadata, and launcher logs. Uninstalling the application does not intentionally remove this user-data directory, so upgrading or reinstalling does not wipe saved candidates/application tracking.

## Job refresh behavior

- The first launch does not wait for a multi-board ATS sweep. The UI becomes
  usable immediately after local services start; the bundled source snapshot and
  any cached catalog remain the offline fallback while the background sync runs.
- Later launches open immediately.
- If the local feed data is older than 24 hours, refresh runs in the background.
- While the launcher remains open, another refresh is scheduled every 24 hours.
- The launcher also exposes a **Refresh jobs** button.

A refresh can partially succeed if an upstream ATS is unavailable. Existing data remains usable and the launcher reports that one or more feeds could not refresh.

## What is bundled

The installer contains:

- `CareerRadar.exe` — a PyInstaller-frozen launcher and Python backend runtime,
- the production Next.js standalone server,
- a bundled Windows Node runtime used only by the local web server,
- Alembic migrations,
- the ranking configuration,
- the skill ontology,
- the audited manual ATS source catalog,
- the generated verified source-registry snapshot, and
- official UKVI/IND sponsor-evidence records.

The local runtime binds only to loopback (`127.0.0.1`) on dedicated high ports; it is not exposed to the LAN by default.

The release workflow runs `CareerRadar.exe --smoke-test` from both a clean silent
installation and a freshly extracted portable directory with host Python and Node
removed from `PATH`. The test uses an isolated data directory and one clearly
fictional fixture so it can verify migrations, the API, the production web server,
the frontend response, and clean child-process shutdown without making a live ATS
network call.

## Portable package

Each release contains a versioned portable archive (for example, `CareerRadar-Portable-v1.1.0.zip`) alongside the
installer when its clean smoke test passes. Extract it and run `CareerRadar.exe`;
it has the same dependency-free runtime as the installer.

## Integrity

`SHA256SUMS.txt` in the release contains SHA-256 hashes for the installer and portable ZIP.

## Windows SmartScreen

The current v1 Windows binary is not Authenticode-signed because the project does not yet have a Windows code-signing certificate. Windows SmartScreen may therefore show an **Unknown publisher** warning. The release workflow builds the binaries from the repository source and publishes SHA-256 checksums alongside them.

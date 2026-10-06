# Smartkiosk Windows client

This is a customized RustDesk client based on upstream commit
`f299fb9906006247863250d7dfaa016f29eef7a4`, with `hbb_common` pinned to
`229b904508364c8997aad0fb5af57effac859f60`.

## Current status

The source changes and installer build workflow are prepared. **No compiled
Smartkiosk executable or MSI has been produced or tested yet.** The local machine
does not have Rust/Cargo, Flutter, or the Visual Studio 2022 C++ toolset.
Monitoring API reporting and periodic screenshots are not implemented: the API
endpoint, authentication, payload format, and interval are still pending.

## Client behavior

- Application name: **Smartkiosk**.
- Default ID server and relay server: `remote.ionline.mn` (assumes both services
  run on this hostname with their standard RustDesk ports).
- Default public key: `Et3a8X4oXI1lng6EqZuef2U1aGoeqAGRVIGVDSQ0uCs=`.
- Explicit saved server settings override these defaults.
- Existing valid IDs in Smartkiosk configuration are preserved. If a new ID is
  needed, upstream's hostname option uses the PC name, replacing spaces with
  hyphens. If hostname lookup fails, upstream falls back to its generated ID.
  Hostname IDs still require acceptance by your ID server and unique PC names.
- The build-time `SMARTKIOSK_PASSWORD` is enforced for incoming connections.
  Startup clears older local permanent passwords and disables password changes.
  Saved/custom verification and approval settings cannot re-enable temporary
  passwords, authenticator OTP, or a kiosk-side Accept prompt.
- The controller must supply the fixed password or remember it locally. Rebuild,
  install the updated client, and restart its service to activate this policy.
- Smartkiosk uses its own configuration directory and service/application name.
  It does not automatically migrate another RustDesk installation's configuration.
- Existing copyright notices and the upstream license are retained. The original
  icon is retained; no custom logo was provided.

## Build with GitHub Actions

Apply the accompanying patch to a checkout of the exact upstream commit:

```powershell
git clone https://github.com/rustdesk/rustdesk.git Smartkiosk
cd Smartkiosk
git checkout f299fb9906006247863250d7dfaa016f29eef7a4
git submodule update --init --recursive
git apply /path/to/Smartkiosk.patch
```

Commit the changes to your own GitHub repository. In its Actions tab, run
**Build Smartkiosk Windows installer**. The workflow builds the Flutter bridge,
native dependencies, customized client, and MSI. Download the
**Smartkiosk-Windows-x64** artifact when the run succeeds. It contains:

- `Smartkiosk-Setup-x64.msi`
- `Smartkiosk-Setup-x64.msi.sha256`

This workflow has not been run yet. It uses upstream's Windows x64 build tool
versions and reusable workflows. It packages the virtual display driver and
window helper; the optional printer driver package is not included. The MSI is
unsigned; no signing certificate was supplied. Nothing is published automatically.

## Package an existing compiled build locally

Use a Visual Studio 2022 C++ developer shell with Python, NuGet, and MSBuild on
PATH. First build the customized client and its generated Flutter bridge using
the upstream Windows build prerequisites. Then run:

```powershell
python scripts/build_smartkiosk_msi.py --check
python scripts/build_smartkiosk_msi.py --output dist
```

The default payload folder is `flutter/build/windows/x64/runner/Release`.
Use `--dist` to select a different compiled payload. The script checks that the
executable, Rust DLL, Flutter DLL, and data directory exist, copies them into an
isolated temporary staging folder, renames the executable to `Smartkiosk.exe`,
and builds the upstream WiX MSI with Smartkiosk product metadata. It does not
install the application on the build machine. Use paths without spaces because
the upstream MSI preprocessor queries the executable through a shell command.

## Validation and regression surface

Local validation: Python syntax check, prerequisite-failure check, Git whitespace
check, and patch applicability check. Compilation, install/uninstall, service
startup, first-run hostname registration, and server connectivity are unverified.

Changed existing paths:

- `src/common.rs`: initializes the custom defaults before custom-client loading.
- `src/custom_server.rs`: supplies app name, network defaults, and hostname-ID
  preference without changing password or saved-ID code.
- `flutter/windows/runner/Runner.rc`: Windows executable product metadata.
- `flutter/windows/runner/main.cpp`: Smartkiosk window-title fallback.

New build files do not add runtime behavior. The shared submodule is unmodified.

## Fixed-password build setup

In this repository, open Settings > Secrets and variables > Actions and create
`SMARTKIOSK_PASSWORD` with your chosen kiosk password (at least 8 characters).
Then run Build Smartkiosk Windows installer. Do not put the password in source,
workflow inputs, or commit messages. For local builds, supply the same environment
variable to the build process. Builds fail if it is absent or too short.

Regression surface: `src/common.rs` applies the policy after all custom-client
loading paths, including early returns. `src/custom_server.rs` uses upstream
preset authentication, clears the local password that would take precedence,
locks password changes, and overrides verification, approval, and 2FA options.
The shared authentication implementation and submodule are unchanged. Existing
always-on service settings and Smart Kiosk title changes are preserved.

Validation: patch whitespace and source review only; the customized executable
and Windows service behavior still require compilation and runtime testing.

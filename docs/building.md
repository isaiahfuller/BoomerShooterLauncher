# Windows builds and Linux AppImages

The `Build Windows and Linux` GitHub Actions workflow builds on native Windows
and Ubuntu 22.04 x86_64 runners using Python 3.14. Docker and Wine are not needed.
The Windows artifact is a cx_Freeze application folder; the Linux artifact is a
single AppImage containing the cx_Freeze application and its bundled libraries.
Neither output includes games or source ports.

## Run the workflow

1. Commit and push the workflow, packaging files, and source changes to GitHub.
2. Once the workflow is on the default branch, open **Actions → Build Windows and
   Linux → Run workflow**.
3. Open the completed run and download its **Artifacts**:
   - **BSL-windows-x64**: extract the ZIP and run `BSL.exe`. Keep all accompanying
     files and directories next to it.
   - **BSL-linux-x86_64**: extract the ZIP, then run:

     ```sh
     chmod +x BSL-linux-x86_64.AppImage
     ./BSL-linux-x86_64.AppImage
     ```

Pushing a `v*` tag also builds both platforms. Relevant pull requests run the
same checks. These are workflow artifacts subject to GitHub's retention policy,
not automatically published GitHub Releases. They are not code-signed; Windows
may display an unknown-publisher warning.

GitHub artifacts do not preserve executable permissions, so Linux users must
run `chmod +x` after downloading. No separate Python installation is required.

## Local builds

Run these commands from the repository root in a Python 3.14 virtual environment:

```sh
python -m pip install -r src/requirements.txt
python src/setup.py build_exe --build-exe build/frozen
```

Build on Windows for Windows, or Linux for Linux. Do not reuse a build directory
from another platform or Python version. `src/setup.py` is the configuration used
by CI; the older `src/freeze.py` and PyInstaller spec are not used.

On x86_64 Linux, install the Qt system dependencies listed in
`.github/workflows/build.yml`, plus `curl` and `desktop-file-utils`. Then:

```sh
desktop-file-validate packaging/linux/bsl.desktop
bash packaging/build-appimage.sh
```

The result is `dist/BSL-linux-x86_64.AppImage`. The packaging script:

- Preserves the frozen application's library and Qt plugin layout inside
  `build/BSL.AppDir`.
- Adds `AppRun`, desktop metadata, and an original project SVG icon (under the
  repository license).
- Downloads versioned appimagetool and type2-runtime releases to
  `build/appimage-tools`, checking their SHA-256 hashes before use.
- Extracts appimagetool rather than relying on FUSE, then creates the AppImage.

To update the packaging tools, update both their release URLs and SHA-256 hashes
in `packaging/build-appimage.sh`. cx_Freeze is pinned in `src/requirements.txt`;
other Python dependencies remain unpinned, so this is not a fully reproducible
build. Clean `build/` before rebuilding after changing dependencies to avoid
retaining obsolete bundled files.

## Validation and compatibility

CI runs the unit tests on both platforms. Windows checks that the frozen program
survives startup. Linux extracts the completed AppImage and launches it with X11
under Xvfb, checking that it remains running for ten seconds. The smoke test
runs outside the source tree without `PYTHONPATH`, so it cannot accidentally
import the application's source files instead of the packaged modules.

For a local headless Linux startup check:

```sh
QT_QPA_PLATFORM=offscreen python packaging/smoke-test.py build/BSL.AppDir/AppRun
```

This is not an interactive UI test: it does not verify Steam discovery, dialogs,
Wayland, graphics drivers, or launching a real source port. Test release builds
on actual Windows and on clean supported Linux distributions before publishing.
The Windows smoke test is intended for disposable CI accounts because QSettings
uses the user's registry there.

Ubuntu 22.04 is the Linux build baseline, not a guarantee of universal Linux
compatibility. AppImages still depend on the host kernel, glibc, graphics stack,
and some system libraries. cx_Freeze collects native dependencies and Qt plugins;
installing a dependency on the build runner does not by itself ensure it is
bundled. If testing on a clean target exposes missing libraries, adjust the
freezer's includes deliberately rather than copying a second Qt installation.
Do not bundle the host's glibc or graphics drivers to work around incompatibility.

The AppRun wrapper does not change the working directory or inject
`LD_LIBRARY_PATH`/Qt plugin environment overrides, avoiding additional environment
pollution for external source ports. Settings and saves use the existing
user-specific locations, outside the read-only AppImage.

If mounting an AppImage is unavailable, extract it instead:

```sh
./BSL-linux-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

The build includes the project license and IWAD metadata attribution. Before
public distribution, review the bundled third-party license notices and source
availability obligations, including Python and Qt/PySide6; creating an AppImage
does not replace that release review.

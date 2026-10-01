# Boomer Shooter Launcher

A launcher for old-school FPS games

Use **Find Steam Games** in the toolbar or welcome dialog to scan installed Steam
games for supported game files. The scan checks Steam's configured libraries,
including additional drives and Linux Flatpak installations, and adds recognized
files to your library. Configure a source port separately to launch them. If Steam
is in an undiscovered location, use **Add Games** to select its game folder manually.

## Documentation

- [MVC refactor plan](docs/mvc-refactor-plan.md)
- [Windows builds and Linux AppImages](docs/building.md)

<details>
<summary>Screenshots</summary>
<img src=https://user-images.githubusercontent.com/9921699/232340110-3b53d266-87fc-4c90-ac7e-ba10ef65571d.png></img>
<img src=https://user-images.githubusercontent.com/9921699/167270128-d027aa9b-3610-494e-9504-838908404450.png></img>
<img src=https://user-images.githubusercontent.com/9921699/167697993-3b1800e9-27c6-416a-8f2b-6b2abbbdf2e6.png></img>
<img src=https://user-images.githubusercontent.com/9921699/232340308-18dc6373-6f1e-4db3-8a06-da152743a274.png></img>
</details>
------------

**Running** - Requires Python 3.14 or higher

From the repository root:

    python -m pip install -r src/requirements.txt
    python src/main.py

**Building** - Requires Python 3.14

    python -m pip install -r src/requirements.txt
    python src/setup.py build

GitHub Actions builds a Windows application folder and a Linux x86_64 AppImage.
See [the build guide](docs/building.md) for downloads, local packaging, and limitations.

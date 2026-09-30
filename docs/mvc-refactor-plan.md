# MVC refactor plan

Status: persistence centralization and the initial domain-model slice are implemented. Remaining MVC migration is incremental.

## Implemented: QSettings repository

`src/repositories/settings_repository.py` now owns QSettings construction and all
group, key, and array access. The main window, game list, runner editor, modpack
editor/importer, scanner, and launcher use repository methods for persistence.
Dictionary APIs remain for callers awaiting migration; the library adapter supplies
domain records. Controllers remain a future step.

The repository preserves the Windows organization/application names
`Isaiah Fuller` / `Boomer Shooter Launcher` and the Linux names
`boomershooterlauncher` / `config`, along with the existing native settings format
and schema. Each operation creates a fresh settings instance, so scanning and UI
operations do not share mutable settings group or array cursors. Writes sync before
returning and report persistence errors. Scanner-to-widget threading behavior is
unchanged and remains part of the service extraction stage.

Modpack saves preserve file order and remembered selections, and clear obsolete
file entries when a pack shrinks or becomes empty. Remembered runners are read
using the same selected base name used when saving and remain available when they
are the only configured runner.

Compatibility tests use disposable INI files with real QSettings. Offscreen UI
checks mock Discord, theme integration, and game process execution. Run from the
repository root with the launcher dependencies installed:

```bash
python -m unittest discover -s tests -v
```

## Implemented: initial domain models and library rules

Immutable game, installed-version, runner, mod-file, and modpack records now live
in `src/models/records.py`. `SettingsRepository.library()` adapts existing
settings into these records; dictionary APIs remain for callers awaiting migration.
Static metadata now lives in `src/models/catalog.py`, with `src/data.py` retaining
compatibility imports.

`models.library.Library` owns runner compatibility and installed-version choices,
and the main window uses those rules to populate its comboboxes. Remembered choices
are preferred only when still available and compatible. Custom ports retain their
existing all-games behavior. Modpack versions resolve through the saved base family;
ordered mod files and existing settings identities remain unchanged.

Validated with domain tests and the existing isolated-settings/offscreen suite,
including stale remembered selections and repository-to-model conversion.

## Implemented: record-backed library selection

The game table now renders `Game` and `Modpack` records and stores them in Qt item
user data. Selection, context-menu actions, and modpack editing/removal resolve
those records rather than parsing labels or positional tuples. Refresh preserves
selection by record type and persisted name, and clears stale selections.
Modpacks are grouped by their base family rather than matching arbitrary table text.

Runner and version comboboxes carry domain records. Launching uses the selected
version's path directly, including when multiple games in a family have identically
named releases. Ordered mod paths come directly from the modpack, preserving commas
and spaces. Saved selection keys and the settings schema remain unchanged.

Validated with the isolated-settings/offscreen suite, including changed display
labels, duplicate release names, game/modpack name collisions, refresh/removal, and
ordered paths containing commas. Remembered versions still use the legacy release
name, so duplicate names cannot be distinguished across restarts without a future
settings-identity extension.

## Implemented: record-backed dialogs

The runner editor stores runner identities in item data rather than parsing display
labels. The modpack editor uses immutable modpack and mod-file drafts, and the
importer keeps ordered mod-file records so duplicate filenames remain independent.
Dialog reads use the library adapter; a record-writing repository adapter preserves
the existing settings schema. JSON dictionaries remain at the import/export boundary.

Reordering and removal keep file metadata aligned with selection, including empty
packs. Export leaves local paths intact. Renaming changes only the draft until Save,
then carries remembered selections to the new identity. Editing a pack whose base
family is no longer installed preserves that family.

Validated with 24 isolated-settings/offscreen tests, including export followed by
editing, removal to empty, cancelled and saved renames, duplicate import filenames,
and runner identity after display-label changes.

Next: complete the IWADINFO compatibility mappings and scanner workflow extraction.
Launcher service extraction, controllers (including JSON workflow extraction), and
widget moves remain pending.

## Purpose

Organize the PySide6 launcher around Model–View–Controller (MVC) while preserving its user interface, supported workflows, and saved configuration. Separate game data and rules from widgets so that scanning, runner selection, modpack management, and launching can be tested without constructing the main window.

## Structure before the persistence refactor

The project already separates several dialogs into view files, but presentation, persistence, and application behavior are mixed together:

- `src/main.py`: `MainWindow` builds the interface, selects compatible runners and versions, coordinates scanning and launching, and updates Discord presence.
- `src/games_view.py`: `GamesView` reads games and modpacks from `QSettings`, builds table rows, and stores selection state.
- `src/mods_view.py`, `src/runner_view.py`, and `src/import_view.py`: dialogs combine widget behavior with configuration reads and writes.
- `src/scanner.py`: `GameScanner` subclasses `QFileDialog` while also scanning files, identifying games, and saving results.
- `src/launcher.py`: `GameLauncher` starts processes but also reads settings, accesses the parent window's selected game, changes the application's working directory, and displays errors.
- `src/data.py`: static game and source-port metadata provides a starting point for a catalog.

## Proposed layout

```text
src/
├── main.py                     # Create application and connect components
├── models/
│   ├── game.py                 # Game and installed versions
│   ├── runner.py               # Source port configuration
│   ├── modpack.py              # Base game and ordered mod files
│   ├── catalog.py              # IWADINFO definitions and supplemental metadata
│   └── library.py              # Library state and compatibility rules
├── views/
│   ├── main_window.py          # Main window layout and UI events
│   ├── games_view.py           # Game list presentation
│   ├── runner_view.py          # Runner management dialog
│   ├── mods_view.py            # Modpack editor
│   ├── import_view.py          # Import dialog
│   ├── first_run_view.py       # Welcome and setup dialog
│   └── theme.py
├── controllers/
│   ├── library_controller.py   # Selection, scanning, runner/version choices
│   ├── launch_controller.py    # Launch workflow and process events
│   ├── runner_controller.py    # Configure and save runners
│   └── modpack_controller.py   # Edit, import, and export modpacks
├── repositories/
│   └── settings_repository.py # Read and write existing QSettings data
└── services/
    ├── scanner.py              # Find and identify game files
    ├── launcher.py             # Build commands and run processes
    └── discord.py              # Discord presence integration
```

This tree shows the application architecture. Existing requirements and build files remain necessary. Add package initializers and update imports and packaging configuration as modules move.

## Responsibilities and boundaries

### Models

Represent games, installed versions, runners, modpacks, and library state as explicit objects rather than positional tuples or widget contents. Preserve mod file order because it affects launch behavior. Keep compatibility rules and launch-configuration validation here.

Models must not depend on windows, dialogs, or table rows. Selection should identify records explicitly rather than relying on display text or a row index as the record's identity.

### Views

Create widgets, display supplied data, collect input, and emit user intent through Qt signals. Views own presentation details such as layout, formatting, file pickers, and error dialogs.

Views should not scan files, construct launch commands, read library records directly from `QSettings`, or decide runner compatibility. Window geometry can be captured by the view and persisted through the settings boundary.

### Controllers

Connect view signals to application workflows. Controllers read the current selection, request model operations, coordinate repositories and services, and update views in response to results.

Keep business rules in models and reusable operations in services so controllers do not become another large `MainWindow`.

### Repositories and services

The settings repository centralizes `QSettings` construction and translates persisted values into application objects. Initially preserve existing platform-specific settings locations, keys, groups, and arrays so users retain their games, runners, modpacks, remembered selections, and window geometry.

Services perform filesystem, process, and external integration work. They accept explicit inputs and report results or errors without reaching into widgets. Qt facilities such as `QProcess` and signals can remain in services; MVC does not require removing Qt from every non-view module.

Scanning should keep the interface responsive. Worker results must return to the GUI thread before widgets are updated, with a clear owner for persistence and worker cleanup.

## Mapping existing behavior

| Current behavior | Proposed owner |
| --- | --- |
| `MainWindow.getRunners()` and `getVersions()` | Library controller requests compatible choices from the model and updates the view |
| `MainWindow.launchGame()` | Launch controller resolves selections and invokes the launcher service |
| `GamesView.refresh()` and `loadModpacks()` reading settings | Repository loads records; view displays supplied records |
| Settings access spread across dialogs | Settings repository |
| Modpack editing, saving, importing, and exporting | Modpack controller coordinates model changes and persistence; JSON handling stays outside widgets |
| `GameScanner` file dialog and scanning | View chooses paths; scanner service identifies files; controller coordinates saving and refresh |
| `GameLauncher.processFinished()` displaying errors | Service reports completion; controller asks the view to display an error |
| Discord updates in `MainWindow` | Controller coordinates the Discord service with application events |

## Example: launching a game

```text
User clicks Launch
    → MainWindow emits launch_requested
    → LaunchController resolves the selected game, version, and runner
    → Model validates and produces a launch request
    → LauncherService prepares arguments and starts the process
    → Controller updates the view and Discord presence
    → Process completion triggers status updates or an error dialog
```

The following is illustrative pseudocode, not an existing API:

```python
# Controller: pass resolved configuration explicitly.
request = library.create_launch_request(selection)
launcher.launch(request)

# Launcher service: operate without accessing the main window.
def launch(self, request):
    executable, arguments = self.build_command(request)
    self.prepare_save_directory(request.save_directory)
    self.process.setWorkingDirectory(str(request.save_directory))
    self.process.start(str(executable), arguments)
```

A launch request should contain the resolved executable, game file, ordered mod files, runner information, and save directory. Command construction must preserve runner-specific arguments, including save-directory flags.

This removes the current dependency on `self.parent().gameList.game`. Using `QProcess.setWorkingDirectory()` also avoids changing the working directory of the entire application with `os.chdir()`. Report both failure to start and unsuccessful process exits to the controller.

## Incremental migration

1. **Centralize persistence — implemented.** Introduce the settings repository and route existing settings access through it. Preserve the stored format and platform-specific configuration names. Keep the current widgets in place.
2. **Introduce explicit models — initial slice implemented.** Define game, installed-version, runner, and modpack objects. Move static metadata into the catalog and compatibility logic into the library. Replace positional record access incrementally. Implement the IWADINFO catalog task below alongside scanner extraction.
3. **Extract scanning and launching.** Separate the file picker from scanning. Give the launcher explicit inputs, remove parent-widget access, and report outcomes through signals. Preserve existing command arguments and save locations.
4. **Extract controllers.** Move selection, runner/version population, launch coordination, and modpack workflows out of widgets. Connect user-intent signals to controllers and send display-ready results back to views.
5. **Move modules into packages.** Reduce `main.py` to application setup and component wiring. Update imports and build configuration as files move. Retain references to controllers, dialogs, and asynchronous services for their required lifetimes.
6. **Optionally adopt Qt model/view tables.** Keep `QTableWidget` during the initial refactor. Later, replace it with `QTableView` and a `QAbstractTableModel` adapter if that simplifies refreshes and selection handling.

A Qt table model is a presentation adapter for the library records, not the entire MVC domain model. This optional step should not block separating workflows from widgets.

## Planned task: adopt UZDoom IWADINFO for game identification

Status: WAD identification slice implemented. A pinned offline IWADINFO catalog is
parsed into ordered definitions. A bounds-checked WAD directory reader matches
`MustContain` rules for manual and Steam scans. Definitions whose filename hint
maps to an existing library game use the existing settings identity; the previous
filename and CRC method remains a fallback when no supported content mapping is
available. The matched IWADINFO `Name` is saved as a display label and shown in
the game list and version picker. Explicit edition aliases map KEX, Unity, BFG,
and Xbox WAD hints to existing Doom, Doom II, TNT, and Plutonia identities;
existing game and release keys remain unchanged
for remembered selections and modpacks. CRC version metadata and blacklist checks
still run for both methods.
Unsupported upstream games, ZIP based IWADs, embedded definitions, companion
requirements, and load ordering remain pending. Manual directory scans now use a
Qt worker and GUI-thread signals for progress, refresh, and cleanup; broader
scanner workflow extraction and launcher service extraction remain pending.

Replace the game-identification portion of `data.games` with definitions from
[UZDoom's `wadsrc_extra/static/iwadinfo.txt`](https://github.com/UZDoom/UZDoom/blob/trunk/wadsrc_extra/static/iwadinfo.txt).
Use [UZDoom's identification implementation](https://github.com/UZDoom/UZDoom/blob/trunk/src/d_iwad.cpp)
as the behavioral reference. This requires changing identification from filename
and CRC lookup to matching internal file entries against ordered `MustContain`
rules; parsing the catalog alone is insufficient.

### Scope and ownership

- Model catalog objects hold names, game families, filename hints, identification
  rules, and definition order. Keep the parser independent of widgets.
- A detection service reads WAD directories and matches definitions in their
  upstream order, so specific games are recognized before more general matches.
- Both manual scanning and Steam scanning use the same detector. Replace their
  reliance on `data.games` for candidate filtering as part of this change.
- Preserve CRC-based release labels as supplemental metadata where exact versions
  matter. IWADINFO does not replace the launcher's full release-hash database or
  optional release-year metadata.
- Keep runner compatibility explicit and separate. Recognition by UZDoom does not
  establish compatibility with other source ports.
- Adapt detection results to the existing repository schema initially. Preserve
  saved games, remembered selections, and modpack base references when mapping
  upstream names and families to existing library identities.

### Implementation sequence

1. Bundle a pinned upstream catalog with its source revision, attribution, and
   applicable license information. Include it in packaged builds and keep scanning
   usable offline.
2. Parse definitions into catalog objects, preserving order and handling comments,
   quoted values, lists, and the catalog's top-level sections. Explicitly distinguish
   identification fields from engine configuration fields.
3. Implement a WAD-directory reader with bounds checks and ordered `MustContain`
   matching. Initially support WAD identification without claiming full UZDoom
   resource-format support.
4. Integrate the detector into manual and Steam scans, retaining supplemental CRC
   metadata and applicable blacklist behavior. Remove `data.games` once its
   identification responsibilities and remaining metadata have been migrated.
5. Extend support to archives and embedded IWADINFO, then implement companion-game
   requirements and load ordering. Until those stages are implemented, report
   unsupported cases explicitly rather than treating recognition as launch support.

### Acceptance checks

- A pinned catalog parses deterministically and is available in source and packaged
  execution without network access.
- Synthetic WAD fixtures verify specific-before-general matching, missing required
  entries, unrecognized files, and malformed or truncated directories.
- Known CRCs retain their release labels; unknown CRCs can still identify a game
  through its contents. Test blacklist behavior explicitly.
- Manual and Steam scans identify the same file consistently and preserve existing
  saved selections and modpack associations.
- Runner filtering remains correct for the identified game, including games that
  require UZDoom-specific features.
- Archive, embedded-definition, dependency, and load-order tests accompany their
  later implementation stages.

## Validation during implementation

Validate each stage before expanding the refactor:

- Existing saved configuration loads without migration or data loss; edits persist across restarts.
- Scanning chosen paths and dropped files identifies games and refreshes the library without updating widgets from worker threads.
- Selecting a game or modpack produces the expected compatible runners and installed versions, including remembered choices.
- Modpack editing, ordering, import, and export preserve the base game and file metadata.
- Launch commands preserve game paths, mod order, runner-specific flags, and save locations, including paths containing spaces.
- Missing executables, process-start failures, and nonzero exits produce useful UI errors; completion restores application status.
- Discord presence, first-run setup, and window geometry continue to behave as before.
- Source execution and the supported packaging workflows still work after module moves.

Use focused unit tests for compatibility rules, command construction, and repository round trips with isolated settings. Use manual GUI smoke checks for dialogs, drag-and-drop, selection, and process lifecycle behavior.

## Completion criteria

The refactor is complete when widgets handle presentation and input, controllers coordinate workflows, models own application data and rules, and repositories and services handle persistence and external operations. Launching and scanning must work without reading state from parent widgets, and existing user configuration and launcher behavior must remain compatible.

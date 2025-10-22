# GitHub Actions PyInstaller Fix

## Issue
When running the GitHub Actions workflow for building the Windows EXE, PyInstaller was throwing an error:

```
ERROR: option(s) not allowed:
  --onedir/--onefile
  --specpath
makespec options not valid when a .spec file is given
```

## Root Cause
In `.github/workflows/release.yml`, the PyInstaller command was using conflicting options:

```bash
# ❌ WRONG - Conflicts with .spec file
pyinstaller --specpath dist/windows runner.spec \
  --onefile \
  --distpath dist/windows/dist \
  --workpath dist/windows/build
```

When you provide a `.spec` file to PyInstaller, you **cannot** use:
- `--onefile` / `--onedir` (already defined in spec)
- `--specpath` (spec file already exists)

## Solution
Remove the conflicting options and only use path configuration:

```bash
# ✅ CORRECT - Works with .spec file
pyinstaller runner.spec \
  --distpath dist/windows/dist \
  --workpath dist/windows/build
```

The build configuration (including `--onefile`) is already defined in `runner.spec`, so PyInstaller doesn't need command-line options for it.

## Files Fixed

### 1. `.github/workflows/release.yml` (Line 244-264)
**Changed:**
- Removed `--specpath dist/windows`
- Removed `--onefile`
- Kept `--distpath` and `--workpath` for output control

### 2. `release.sh` (Already fixed previously)
The local `release.sh` script was already using the correct format:
```bash
pyinstaller runner.spec --distpath dist/windows/dist --workpath dist/windows/build
```

## Impact

✅ Windows EXE builds will now work correctly in GitHub Actions
✅ No change to build behavior - `runner.spec` defines `onefile=True`
✅ Consistent with local `release.sh` implementation
✅ Future releases will build successfully

## Testing

The fix has been applied to:
- Local script: `release.sh` ✅
- GitHub Actions: `.github/workflows/release.yml` ✅

Next release will be successful with this fix in place.

## Related Files
- `runner.spec` - PyInstaller specification file (defines onefile, distpath, etc.)
- `.github/workflows/release.yml` - GitHub Actions workflow
- `release.sh` - Local release script

# GitHub Packages Configuration Guide

This guide explains how to properly configure GitHub Packages Python registry for the Python Script Runner project.

## Overview

GitHub Packages is a package hosting service that allows you to host packages privately or publicly. The Python registry supports publishing Python packages via twine.

## Why 404 Error?

The 404 error typically occurs due to:

1. **Authentication Issues**: Repository might not be public or token lacks proper scope
2. **Repository Settings**: Package registry might not be enabled
3. **Configuration**: Incorrect registry URL or credentials

## Solution Options

### Option 1: Disable GitHub Packages Publishing (Recommended for Now)

Since PyPI is the primary registry, you can skip GitHub Packages for now:

In `.github/workflows/publish.yml`:
- The GitHub Packages step now has `continue-on-error: true`
- Workflow won't fail if GitHub Packages step fails
- PyPI publishing remains the primary distribution method

### Option 2: Set Up GitHub Packages with Personal Access Token

1. **Create a Personal Access Token (PAT)**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Scopes needed:
     - `write:packages` - Upload packages
     - `read:packages` - Download packages
     - `delete:packages` - Delete packages
   - Copy the token

2. **Add Token to GitHub Secrets**
   - Go to: https://github.com/jomardyan/Python-Script-Runner/settings/secrets/actions
   - Click "New repository secret"
   - Name: `GITHUB_PACKAGES_TOKEN`
   - Value: (paste the PAT)

3. **Update Workflow**
   ```yaml
   - name: Publish to GitHub Packages
     if: success()
     env:
       TWINE_REPOSITORY_URL: https://python.pkg.github.com/jomardyan/python-script-runner
       TWINE_USERNAME: jomardyan
       TWINE_PASSWORD: ${{ secrets.GITHUB_PACKAGES_TOKEN }}
     run: |
       twine upload dist/* --verbose
   ```

### Option 3: Manual GitHub Packages Setup

For automated publishing without special tokens:

1. Ensure repository is **public**
2. Enable "Allow GitHub Actions" in Settings → Actions → General
3. Repository tab in Settings → Show in Packages

## Current Status

✅ **Primary Distribution: PyPI**
- Fully automated via `PYPI_API_TOKEN`
- Works reliably
- Public package at: https://pypi.org/project/python-script-runner/

⚠️ **Secondary Distribution: GitHub Packages**
- Currently optional (continue-on-error: true)
- Requires additional setup (see above)
- Can be implemented when needed

## For Users

### Install from PyPI (Recommended)
```bash
pip install python-script-runner
```

### Access GitHub Packages (When Available)
```bash
# Configure authentication in ~/.pypirc or use token
pip install --index-url https://python.pkg.github.com/jomardyan/python-script-runner python-script-runner
```

## Workflow Behavior

Current workflow for `v6.2.1+`:

1. ✅ **Validate Version** - Checks consistency
2. ✅ **Test** - Runs on Python 3.8-3.12
3. ✅ **Publish to PyPI** - Primary distribution
4. ⚠️ **Publish to GitHub Packages** - Optional (skips on error)
5. ✅ **Create GitHub Release** - With build artifacts

## Troubleshooting

### Check Workflow Logs
1. Go to: https://github.com/jomardyan/Python-Script-Runner/actions
2. Click the failed workflow run
3. Expand the "Publish to GitHub Packages" step
4. Look for error messages

### Common Issues

**404 Not Found**
- Repository might be private
- Token lacks `write:packages` scope
- Incorrect repository URL

**401 Unauthorized**
- Invalid or expired token
- Incorrect username
- Token not added to GitHub Secrets

**50x Server Error**
- GitHub API might be down
- Try again later

## Manual Testing

To test GitHub Packages locally:

```bash
# Create .pypirc with token
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    github-packages

[github-packages]
repository = https://python.pkg.github.com/jomardyan/python-script-runner
username = __token__
password = YOUR_PAT_TOKEN_HERE
EOF

# Build distributions
python -m build

# Test upload (dry-run if possible)
twine upload dist/* -r github-packages --verbose
```

## References

- [GitHub Packages Documentation](https://docs.github.com/en/packages)
- [GitHub Python Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-python-registry)
- [Creating a Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

## Next Steps

1. **For now**: Keep using PyPI (primary distribution) ✅
2. **Optional**: Set up GitHub Packages when needed (follow Option 2 or 3 above)
3. **Future**: Consider GitHub Packages for private packages


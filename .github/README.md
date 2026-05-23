# `.github/` folder

This folder contains GitHub-specific project automation.

## Current workflow

```text
.github/workflows/ci.yml
```

The CI workflow installs dependencies and runs tests on pushes and pull requests to `main`.

## Recommended future additions

- Issue template for bug reports.
- Pull request template.
- Deployment workflow after you are comfortable deploying manually.

Do not put secrets in this folder. Use GitHub Actions secrets if you later automate deployment.

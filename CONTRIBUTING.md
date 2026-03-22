# Contributing to ros2_medkit_clients

Thanks for your interest in contributing to ros2_medkit_clients! This guide explains how to report issues, suggest features, and contribute code.

## How to Report Issues

### Did you find a bug?

- **Ensure the bug was not already reported** by searching [Issues](https://github.com/selfpatch/ros2_medkit_clients/issues)
- If you can't find an existing issue, [open a new one](https://github.com/selfpatch/ros2_medkit_clients/issues/new/choose) and select the **Bug report** template
- Fill in all sections of the template:
  - **Steps to reproduce** - numbered steps to recreate the issue
  - **Expected behavior** - what you expected to happen
  - **Actual behavior** - what actually happened, including error messages or stack traces
  - **Environment** - ros2_medkit_clients version, spec version, OS
  - **Additional information** - logs, snippets, or screenshots if helpful

### Do you want to suggest a feature or improvement?

- Check if the feature has already been suggested in [Issues](https://github.com/selfpatch/ros2_medkit_clients/issues)
- If not, [open a new issue](https://github.com/selfpatch/ros2_medkit_clients/issues/new/choose) and select the **Feature request / General issue** template
- Fill in all sections:
  - **Proposal** - describe the change or feature you'd like to see
  - **Motivation** - why is this important? Who does it benefit?
  - **Alternatives considered** - other options or implementations you considered
  - **Additional context** - any other context or screenshots

## How to Contribute Code

### Development Workflow

1. **Fork the repository** and clone your fork locally
2. **Create a branch** from `main` with a descriptive name:
   - `feature/short-description` for new features
   - `fix/short-description` for bug fixes
   - `docs/short-description` for documentation changes
3. **Make your changes** following the project's coding standards
4. **Test your changes** locally (see Build and Test section below)
5. **Commit your changes** with clear, descriptive commit messages
6. **Push your branch** to your fork
7. **Open a Pull Request** against the `main` branch of this repository

### Commit Messages

- Use clear and descriptive commit messages
- Start with a verb in imperative mood (e.g., "Add", "Fix", "Update", "Remove")
- Keep the first line under 72 characters
- Add a blank line followed by a more detailed explanation if needed

Examples:
```
Add Python client generation support

Fix incorrect response schema in fault endpoints

Update documentation for spec validation workflow
```

### Build and Test Requirements

Before opening or updating a Pull Request, you **must**:

1. Validate the OpenAPI spec:
   ```bash
   npx @stoplight/spectral-cli@6.14.2 lint spec/openapi.yaml
   ```

2. Generate clients to confirm the spec produces valid output:
   ```bash
   ./scripts/generate.sh
   ```

3. If you have modified the gateway and need to export a fresh spec:
   ```bash
   ./scripts/export-spec.sh
   ```
   Note: this requires a running gateway instance.

4. Ensure the spec validates without errors and generated clients compile cleanly.

### Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows the repository's style and conventions
- [ ] Spec validates without errors
- [ ] Generated clients build successfully
- [ ] New tests are added for new functionality
- [ ] Existing tests are updated if behavior changes
- [ ] Documentation is updated where applicable
- [ ] PR description clearly explains what changed and why
- [ ] Related issue is referenced (e.g., "Fixes #123")

### Code Review Process

- The project maintainers will review pull requests as time permits
- Address review feedback promptly
- Keep discussions professional and constructive
- Be patient - maintainers may need time to review

## What NOT to Contribute

- **Purely cosmetic changes** that don't add functionality (whitespace, formatting without other changes)
- **Large refactors** without prior discussion - open an issue first
- **Breaking changes** without coordination with maintainers
- **Code that doesn't pass validation** or breaks existing functionality

## Questions and Help

- For questions about **using ros2_medkit_clients**, open a [Discussion](https://github.com/selfpatch/ros2_medkit_clients/discussions) or an Issue with the question label
- For questions about **contributing**, feel free to ask in your PR or Issue
- For **security vulnerabilities**, see [`SECURITY.md`](SECURITY.md)

## Code of Conduct

By contributing to ros2_medkit_clients, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful and considerate in all interactions.

## License

By contributing to ros2_medkit_clients, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for improving ros2_medkit_clients! We value contributions of all sizes - from typo fixes to major features.

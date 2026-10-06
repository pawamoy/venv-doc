# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.1.0](https://github.com/pawamoy/venv-doc/releases/tag/0.1.0) - 2026-10-06

<small>[Compare with first commit](https://github.com/pawamoy/venv-doc/compare/45cf8ad49ec045b2a0be1b1077e2d9fe03ff164d...0.1.0)</small>

### Features

- Expose build and serve subcommands ([e7a8e20](https://github.com/pawamoy/venv-doc/commit/e7a8e20a335258b7e3c834a02ea4935d9f0436b1) by Timothée Mazzucotelli).
- Rework display, support more stuff ([3493ac5](https://github.com/pawamoy/venv-doc/commit/3493ac5bf5f0df715097faed682e9976b2066825) by Timothée Mazzucotelli).
- Initial version ([45cf8ad](https://github.com/pawamoy/venv-doc/commit/45cf8ad49ec045b2a0be1b1077e2d9fe03ff164d) by Timothée Mazzucotelli).

### Bug Fixes

- Fix distribution discovery ([c688322](https://github.com/pawamoy/venv-doc/commit/c6883225ba047725c78f0a1d80846aef11de8477) by Timothée Mazzucotelli).

### Performance Improvements

- Add prune-source dependency to make Griffe faster ([cdae091](https://github.com/pawamoy/venv-doc/commit/cdae0912c356033f12cbe2ffc31e1cccfc7b6225) by Timothée Mazzucotelli).
- Load data ourselves to avoid resolving aliases again after each package load (in handler) ([23e2a7e](https://github.com/pawamoy/venv-doc/commit/23e2a7e4242461063d963439a0bd25a1244be9ad) by Timothée Mazzucotelli).
- Pre-parse docstrings, prevent Zensical from resetting handlers data ([c8ca442](https://github.com/pawamoy/venv-doc/commit/c8ca442a82123dd8576af0190d8ac9e04b11f176) by Timothée Mazzucotelli).

### Code Refactoring

- Don't show source ([603d3e8](https://github.com/pawamoy/venv-doc/commit/603d3e88083394f3a6a472736b78e40129f10625) by Timothée Mazzucotelli).
- Use Zensical to render docs, detect docstring styles ([e00ee40](https://github.com/pawamoy/venv-doc/commit/e00ee40fa92b0c18552e477408daa18e647013bb) by Timothée Mazzucotelli).

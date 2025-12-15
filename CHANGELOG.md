# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.2.0] - 2025-05-26

### Changed

- Build system now uses `uv` insteaed of `poetry`.

- Updated dependencies, minimum Python version is now 3.9.

## [4.1.0] - 2023-02-10

### Added

- It is now possible to use an AST directly as a compilation input.

## [4.0.1] - 2022-05-30

### Fixed

- `wait_until()` command argument should be a duration, not a plain varuint.

## [4.0.0] - 2022-04-26

This release cleans up old unused code from the project and adds almost full
typing coverage and plenty of unit tests.

The license of the project is changed to GNU General Public License v3.

Detailed changes are as follows:

- Removed support for Sunlite Suite files.

- Removed unused `connect` and `upload` subcommands.

- Removed support for easing modes.

- Added GPLv3 license.

## [3.2.1] - 2021-06-08

This is the release that serves as a basis for changelog entries above. Refer
to the commit logs for changes affecting this version and earlier versions.

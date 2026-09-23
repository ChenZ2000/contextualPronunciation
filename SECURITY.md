# Security policy

## Supported versions

Security fixes are made for the latest public release. Earlier versions may require an upgrade. Supported NVDA versions are declared in the release manifest; development beta testing does not promise compatibility with future releases.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/ChenZ2000/contextualPronunciation/security/advisories/new) to contact ChenZ2000. Include affected versions, a minimal reproduction and expected impact. Do not include credentials, personal speech content or proprietary voice files. If private reporting is unavailable, open an issue requesting a private contact without disclosing exploit details.

## Runtime scope

The add-on reads packaged lexical data and its NVDA configuration, and rewrites temporary speech strings through public extension points. It has no network client, updater, remote service, shell execution or telemetry in its runtime. It does not write source documents or record spoken content. Generic error messages deliberately exclude input text and exception values.

Development scripts are separate: they download pinned open-source dependencies and may run compilers or offline synthesizer probes. They are not installed in the add-on. Public Actions do not load licensed voices, live NVDA profiles or user dictionaries. Security review still matters: like other NVDA add-ons, installed Python code executes in NVDA's process and is not sandboxed by this project.

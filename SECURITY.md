# Security Policy

## Supported Versions

FAIR PhyloFlow is currently an alpha research prototype. Security fixes are
provided for the latest release and the default development branch.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability. Contact the
maintainer privately through the contact channel on the maintainer's GitHub
profile and include:

- affected version or commit;
- reproduction steps;
- expected impact;
- any suggested mitigation.

Please allow a reasonable period for acknowledgement and investigation before
public disclosure.

## Operational Scope

Project configuration files and biological inputs should be treated as
untrusted when they originate outside your organization. Review generated
commands before execution. The application can invoke external scientific
software, and the security and licensing of those tools remain the user's
responsibility.

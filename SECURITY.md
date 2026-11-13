# Security and threat model

This is an offline local validator, not a hardened untrusted-image sandbox. It does not make network requests, execute asset metadata, or upload art. It restricts asset paths and refuses symlinked assets on supported systems. POSIX uses `O_NOFOLLOW` on each opened directory entry; Windows checks are best-effort and not a guarantee against adversarial concurrent modifications. Python packages and Pillow must be kept patched. Report suspected vulnerabilities privately to repository maintainers. Do not attach sensitive images or private project data to public issues.

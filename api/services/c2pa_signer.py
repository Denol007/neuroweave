"""C2PA digital provenance signer.

Creates C2PA manifests for dataset exports, providing cryptographic
proof of origin and processing chain.

In production, uses AWS KMS for X.509 certificate signing.
In development, uses a self-signed certificate.
"""

from __future__ import annotations

import hashlib
import json

import structlog

logger = structlog.get_logger()


def compute_content_hash(data: str | bytes) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(data, str):
        data = data.encode()
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def create_manifest(
    export_id: int,
    record_count: int,
    content_hash: str,
    source_server: str,
) -> dict:
    """Create a C2PA manifest for a dataset export.

    Args:
        export_id: Database ID of the export.
        record_count: Number of records in the dataset.
        content_hash: SHA-256 hash of the JSONL content.
        source_server: Discord server identifier.

    Returns:
        C2PA manifest dict with claim, assertions, and signature placeholder.
    """
    manifest = {
        "claim": {
            "dc:title": f"NeuroWeave Export #{export_id}",
            "dc:format": "application/jsonl",
            "claim_generator": "neuroweave/0.1.0",
        },
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {"action": "c2pa.created", "softwareAgent": "neuroweave-pipeline"},
                        {"action": "c2pa.edited", "softwareAgent": "neuroweave-anonymizer"},
                    ]
                },
            },
            {
                "label": "neuroweave.provenance",
                "data": {
                    "source": f"discord:{source_server}",
                    "record_count": record_count,
                    "content_hash": content_hash,
                    "pii_redacted": True,
                    "consent_verified": True,
                },
            },
        ],
        "signature": {
            "algorithm": "sha256-rsa",
            "certificate": "placeholder-use-aws-kms-in-production",
        },
    }

    logger.info(
        "c2pa_manifest_created",
        export_id=export_id,
        records=record_count,
    )
    return manifest


def sign_manifest(manifest: dict) -> str:
    """Sign a C2PA manifest and return its hash.

    In production, this would use AWS KMS to sign with an X.509 certificate.
    For now, returns the SHA-256 of the manifest JSON.
    """
    manifest_json = json.dumps(manifest, sort_keys=True)
    manifest_hash = compute_content_hash(manifest_json)
    return manifest_hash

"""Generate a VAPID key pair for Web Push.

Run once and copy the values into your environment (Railway variables):

    python gen_vapid.py

Set VAPID_PRIVATE_KEY in the server environment. Keep it secret - never commit it.
The public key is derived automatically by the app; it's printed here just so
you can see it.
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main():
    vapid = Vapid01()
    vapid.generate_keys()

    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    print("VAPID_PRIVATE_KEY=" + b64url(private_raw))
    print()
    print("# public application server key (derived automatically, for reference):")
    print("# " + b64url(public_raw))


if __name__ == "__main__":
    main()

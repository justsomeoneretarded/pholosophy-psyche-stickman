"""Fail fast with a clear message if the Groq key or network access is not working."""
import os
import sys
try:
    from groq import Groq
    key = os.environ.get('GROQ_API_KEY', '').strip()
    if not key:
        print('::error title=Groq::The GROQ_API_KEY secret is empty or missing'); sys.exit(1)
    ids = sorted(m.id for m in Groq(api_key=key, timeout=30).models.list().data)
    wanted = [m for m in ids if 'qwen3' in m or 'gpt-oss' in m]
    print(f'::notice title=Groq access OK::{len(ids)} models; writer candidates: {", ".join(wanted) or "none"}')
except Exception as exc:  # noqa: BLE001
    print(f'::error title=Groq access failed::{type(exc).__name__}: {str(exc)[:500]}')
    sys.exit(1)

"""JSON completions from free language models, with automatic fallback.

Order (override with WRITER_MODELS, comma separated):
  1. groq:qwen/qwen3.8-27b      main writer (needs the GROQ_API_KEY secret)
  2. groq:openai/gpt-oss-120b   if qwen is unavailable or rate limited
  3. ollama:gemma4:12b          local CPU model if Groq cannot be used at all
"""
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODELS = 'groq:qwen/qwen3.8-27b,groq:openai/gpt-oss-120b,ollama:gemma4:12b'
GROQ = 'https://api.groq.com/openai/v1'
# Groq sits behind Cloudflare, which refuses Python's default user-agent (error 1010).
USER_AGENT = 'stickman-essay-studio/1.0 (+https://github.com/justsomeoneretarded/pholosophy-psyche-stickman)'
ROOT = Path(__file__).resolve().parents[2]


class WriterError(RuntimeError):
    pass


def notice(title, message, level='notice'):
    print(f'::{level} title={title}::{str(message).replace(chr(10), " ")[:900]}', flush=True)


def parse_json(text):
    """Extract the JSON object from a model reply (tolerates think blocks and code fences)."""
    text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.S).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        raise ValueError('No JSON object in the reply')
    return json.loads(text[start:end + 1])


def _post(url, payload, headers, timeout=240):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT, 'Accept': 'application/json', **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class Groq:
    def __init__(self, model):
        self.key = os.environ.get('GROQ_API_KEY', '').strip()
        if not self.key:
            raise WriterError('GROQ_API_KEY is not set')
        self.model = self._resolve(model)
        self.optional = {'reasoning_format': 'hidden'} if 'qwen' in self.model else {'reasoning_effort': 'medium'}

    def _resolve(self, wanted):
        """Use the exact model id if Groq lists it, otherwise the closest listed id."""
        try:
            req = urllib.request.Request(GROQ + '/models', headers={'Authorization': 'Bearer ' + self.key, 'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                ids = [m['id'] for m in json.load(r).get('data', [])]
        except Exception as exc:  # noqa: BLE001
            detail = exc.read().decode(errors='replace')[:200] if hasattr(exc, 'read') else ''
            notice('Groq model list unavailable', f'{type(exc).__name__} {getattr(exc, "code", "")} {detail}; trying {wanted} directly', 'warning')
            return wanted
        if wanted in ids:
            return wanted
        stem = wanted.split('/')[-1].lower()
        close = [i for i in ids if stem.split('-')[0] in i.lower()]
        if close:
            notice('Groq model id', f'{wanted} not listed; using {close[0]}')
            return close[0]
        raise WriterError(f'{wanted} is not offered by Groq for this key (available: {", ".join(ids[:12])})')

    def complete(self, system, user, temperature=.8, max_tokens=7000):
        payload = {'model': self.model, 'temperature': temperature, 'max_completion_tokens': max_tokens,
                   'response_format': {'type': 'json_object'},
                   'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], **self.optional}
        for attempt in range(6):
            try:
                result = _post(GROQ + '/chat/completions', payload, {'Authorization': 'Bearer ' + self.key})
                choice = result['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise WriterError('Reply was cut off by the output limit')
                usage = result.get('usage', {})
                notice('Writer', f'{self.model}: {usage.get("prompt_tokens")} prompt + {usage.get("completion_tokens")} output tokens')
                return choice['message']['content']
            except urllib.error.HTTPError as exc:
                body = exc.read().decode(errors='replace')[:600]
                if exc.code == 400 and self.optional and any(k in body for k in self.optional):
                    for k in list(self.optional):
                        payload.pop(k, None)
                    self.optional = {}
                    continue
                if exc.code == 429 or exc.code >= 500:
                    wait = float(exc.headers.get('retry-after') or 0) or min(90, 15 * (attempt + 1))
                    notice('Groq busy', f'HTTP {exc.code}; waiting {wait:.0f}s', 'warning')
                    time.sleep(min(wait, 120))
                    continue
                if exc.code in (401, 403):
                    notice('Groq refused the request', f'HTTP {exc.code}: {body[:200]}. Check the GROQ_API_KEY secret.', 'error')
                raise WriterError(f'Groq HTTP {exc.code}: {body}')
            except (urllib.error.URLError, TimeoutError) as exc:
                time.sleep(10 * (attempt + 1))
                last = exc
        raise WriterError(f'Groq did not answer after retries ({self.model})')


class Ollama:
    def __init__(self, model):
        self.model = model
        self.url = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')
        if not self._alive():
            notice('Writer fallback', f'Starting local Ollama with {model}; this is slower than Groq', 'warning')
            subprocess.run(['bash', str(ROOT / 'scripts' / 'ollama_fallback.sh'), model], check=True, timeout=1800)

    def _alive(self):
        try:
            urllib.request.urlopen(self.url + '/api/tags', timeout=3)
            return True
        except Exception:  # noqa: BLE001
            return False

    def complete(self, system, user, temperature=.8, max_tokens=7000):
        payload = {'model': self.model, 'stream': False, 'format': 'json', 'think': False, 'keep_alive': '10m',
                   'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                   'options': {'temperature': temperature, 'num_ctx': 16384, 'num_predict': max_tokens}}
        result = _post(self.url + '/api/chat', payload, {}, timeout=3600)
        return result['message']['content']


class Writer:
    """Tries each configured model in order until one returns valid JSON."""

    def __init__(self, models=None):
        self.specs = [m.strip() for m in (models or os.environ.get('WRITER_MODELS') or DEFAULT_MODELS).split(',') if m.strip()]
        self.used = None
        self.clients = {}

    def _client(self, spec):
        if spec not in self.clients:
            provider, _, model = spec.partition(':')
            self.clients[spec] = Groq(model) if provider == 'groq' else Ollama(model)
        return self.clients[spec]

    def json(self, system, user, validate=None, temperature=.8):
        errors = []
        for spec in self.specs:
            try:
                client = self._client(spec)
            except Exception as exc:  # noqa: BLE001
                errors.append(f'{spec}: {exc}')
                notice('Writer unavailable', f'{spec}: {exc}', 'warning')
                continue
            feedback = ''
            for attempt in range(3):
                try:
                    reply = client.complete(system, user + feedback, temperature=temperature)
                    data = parse_json(reply)
                    result = validate(data) if validate else data
                    self.used = spec
                    return result
                except WriterError as exc:
                    errors.append(f'{spec}: {exc}')
                    notice('Writer error', f'{spec}: {exc}', 'warning')
                    break
                except Exception as exc:  # noqa: BLE001 -- invalid JSON or failed checks: ask for a fix
                    errors.append(f'{spec} attempt {attempt + 1}: {exc}')
                    notice('Script revision', f'{spec} attempt {attempt + 1}: {str(exc)[:400]}', 'warning')
                    feedback = f'\n\nYOUR PREVIOUS ANSWER WAS REJECTED: {str(exc)[:1500]}\nReturn the complete corrected JSON.'
        raise WriterError('No writer produced a valid script: ' + ' | '.join(errors[-6:]))

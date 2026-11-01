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


class Rejected(ValueError):
    """A parsed reply that failed checks; `usable` is a fallback result if nothing better arrives."""

    def __init__(self, message, usable=None, severity=1):
        super().__init__(message)
        self.usable = usable
        self.severity = severity


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
    """Groq through its official Python SDK (requests Cloudflare accepts), with raw HTTP as a backup."""

    def __init__(self, model):
        self.key = os.environ.get('GROQ_API_KEY', '').strip()
        if not self.key:
            raise WriterError('GROQ_API_KEY is not set')
        try:
            from groq import Groq as Client
            self.client = Client(api_key=self.key, max_retries=2, timeout=240)
        except ImportError:
            self.client = None
        self.model = self._resolve(model)
        self.optional = {'reasoning_format': 'hidden'} if 'qwen' in self.model else {'reasoning_effort': 'low'}

    def _list(self):
        if self.client is not None:
            return [m.id for m in self.client.models.list().data]
        req = urllib.request.Request(GROQ + '/models', headers={'Authorization': 'Bearer ' + self.key, 'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            return [m['id'] for m in json.load(r).get('data', [])]

    def _resolve(self, wanted):
        """Use the exact model id if Groq lists it, otherwise the closest listed id."""
        try:
            ids = self._list()
        except Exception as exc:  # noqa: BLE001
            raise WriterError(f'Groq refused the model list: {type(exc).__name__}: {str(exc)[:300]}')
        if wanted in ids:
            return wanted
        stem = wanted.split('/')[-1].lower()
        close = [i for i in ids if stem.split('-')[0] in i.lower()]
        if close:
            notice('Groq model id', f'{wanted} not listed; using {close[0]}')
            return close[0]
        raise WriterError(f'{wanted} is not offered by Groq for this key (available: {", ".join(ids[:15])})')

    def _call(self, payload):
        if self.client is not None:
            extra = {k: payload.pop(k) for k in list(payload) if k in ('reasoning_format', 'reasoning_effort')}
            r = self.client.chat.completions.create(**payload, extra_body=extra or None)
            return {'choices': [{'message': {'content': r.choices[0].message.content}, 'finish_reason': r.choices[0].finish_reason}],
                    'usage': {'prompt_tokens': r.usage.prompt_tokens, 'completion_tokens': r.usage.completion_tokens}}
        return _post(GROQ + '/chat/completions', payload, {'Authorization': 'Bearer ' + self.key})

    def complete(self, system, user, temperature=.8, max_tokens=7000):
        budget = min(max_tokens, getattr(self, '_output_cap', max_tokens))
        base = {'model': self.model, 'temperature': temperature, 'max_tokens': budget,
                'response_format': {'type': 'json_object'},
                'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
        for attempt in range(6):
            payload = {**base, **self.optional}
            try:
                result = self._call(payload)
                self._shrinks = 0
                choice = result['choices'][0]
                if choice.get('finish_reason') == 'length':
                    if getattr(self, '_output_cap', None):
                        raise WriterError(f'{self.model} truncated the reply at its {self._output_cap}-token output cap; use a model with more capacity or split this stage into smaller requests')
                    raise ValueError('The reply was cut off. Preserve the required narration word count and JSON structure; '
                                     'shorten visual descriptions and metadata, not the spoken explanation.')
                usage = result.get('usage', {})
                notice('Writer', f'{self.model}: {usage.get("prompt_tokens")} prompt + {usage.get("completion_tokens")} output tokens')
                return choice['message']['content']
            except (WriterError, ValueError):
                raise
            except Exception as exc:  # noqa: BLE001
                status = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
                text = str(getattr(exc, 'body', '') or exc)[:600]
                if status == 400 and self.optional and any(k in text for k in self.optional):
                    self.optional = {}
                    continue
                if status == 400 and 'json' in text.lower() and attempt < 2:
                    base['messages'][1]['content'] = user + '\n\nReturn one valid JSON object only.'
                    continue
                if status in (413, 429) and 'too large' in text.lower():
                    shrinks = getattr(self, '_shrinks', 0) + 1
                    self._shrinks = shrinks
                    if shrinks > 2:
                        raise WriterError(f'{self.model} cannot fit this request on the free tier: {text[:300]}')
                    nums = dict(re.findall(r'(Limit|Requested)\D{0,3}(\d+)', text))
                    old_budget = base['max_tokens']
                    if nums.get('Limit') and nums.get('Requested'):
                        limit, requested = int(nums['Limit']), int(nums['Requested'])
                        if 'OTPM' in text or 'output tokens per minute' in text.lower():
                            # An output cap is independent of prompt size. Never impose a floor above it.
                            self._output_cap = max(1, limit - min(32, max(0, limit // 10)))
                            new_budget = min(old_budget - 1, self._output_cap)
                        else:
                            new_budget = old_budget - max(0, requested - limit) - 150
                    else:
                        new_budget = int(old_budget * .75)
                    if new_budget < 128 or new_budget >= old_budget:
                        raise WriterError(f'{self.model} cannot fit the prompt/output budget within its reported free-tier limit: {text[:300]}')
                    base['max_tokens'] = new_budget
                    notice('Groq budget', f'request too large ({text[:220]}); output budget now {base["max_tokens"]} tokens', 'warning')
                    continue
                if status == 429 or (isinstance(status, int) and status >= 500) or status is None:
                    headers = getattr(getattr(exc, 'response', None), 'headers', {}) or {}
                    wait = float(headers.get('retry-after') or 0) or min(90, 15 * (attempt + 1))
                    notice('Groq busy', f'{status}: {text[:160]}; waiting {wait:.0f}s', 'warning')
                    time.sleep(min(wait, 120))
                    continue
                raise WriterError(f'Groq error {status}: {text}')
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
                   'options': {'temperature': temperature, 'num_ctx': 16384, 'num_predict': max_tokens, 'num_gpu': 0}}
        result = _post(self.url + '/api/chat', payload, {}, timeout=3600)
        self.last_stats = {k: result.get(k) for k in ('total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration')}
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

    def json(self, system, user, validate=None, temperature=.8, max_tokens=None, attempts=4):
        errors, best, answered = [], None, False
        specs = ([self.used] + [s for s in self.specs if s != self.used]) if self.used in self.specs else self.specs
        for spec in specs:
            if spec.startswith('ollama:') and answered:
                break               # Groq works; a slower, weaker local model will not do better
            try:
                client = self._client(spec)
            except Exception as exc:  # noqa: BLE001
                errors.append(f'{spec}: {exc}')
                notice('Writer unavailable', f'{spec}: {exc}', 'warning')
                continue
            feedback = ''
            for attempt in range(attempts):
                try:
                    budget = max_tokens or 7000
                    if spec.startswith('groq:'):
                        # Groq's free tier rejects requests whose prompt + output budget exceed the per-minute token limit.
                        budget = min(budget, max(128, int(os.environ.get('GROQ_TPM', '8000')) - 250 - int(len(system + user + feedback) / 3.4)))
                    reply = client.complete(system, user + feedback, temperature=temperature, max_tokens=budget)
                    answered = True
                    data = parse_json(reply)
                    result = validate(data) if validate else data
                    self.used = spec
                    return result
                except WriterError as exc:
                    errors.append(f'{spec}: {exc}')
                    notice('Writer error', f'{spec}: {exc}', 'warning')
                    break
                except Exception as exc:  # noqa: BLE001 -- invalid JSON or failed checks: ask for a fix
                    usable = getattr(exc, 'usable', None)
                    if usable is not None and (best is None or exc.severity < best[0]):
                        best = (exc.severity, usable, spec, str(exc))
                    errors.append(f'{spec} attempt {attempt + 1}: {exc}')
                    notice('Script revision', f'{spec} attempt {attempt + 1}: {str(exc)[:400]}', 'warning')
                    feedback = f'\n\nYOUR PREVIOUS ANSWER WAS REJECTED: {str(exc)[:1500]}\nReturn the complete corrected JSON.'
        if best is not None:
            notice('Script accepted with a length warning', f'{best[2]}: {best[3][:300]}', 'warning')
            self.used = best[2]
            return best[1]
        raise WriterError('No writer produced a valid script: ' + ' | '.join(errors[-6:]))

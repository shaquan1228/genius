import json
import pathlib
import select
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class Client:
    def __init__(self, db, project, name, channel=False):
        self.proc = subprocess.Popen(
            ['node', str(ROOT / 'bridge.mjs'), '--db', str(db), '--project', str(project),
             '--name', name, '--harness', name] + (['--claude-channel'] if channel else []),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self.sequence = 0
        self.notifications = []
        self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                    'clientInfo': {'name': 'spike-test', 'version': '1'}})
        self.write({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def write(self, value):
        self.proc.stdin.write(json.dumps(value) + '\n')
        self.proc.stdin.flush()

    def read(self):
        if not select.select([self.proc.stdout], [], [], 5)[0]:
            raise TimeoutError('MCP server did not respond')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(self.proc.stderr.read())
        return json.loads(line)

    def request(self, method, params):
        self.sequence += 1
        self.write({'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': params})
        while True:
            result = self.read()
            if result.get('id') == self.sequence:
                return result['result']
            self.notifications.append(result)

    def tool(self, name, **arguments):
        result = self.request('tools/call', {'name': name, 'arguments': arguments})
        if result.get('isError'):
            raise ValueError(result['content'][0]['text'])
        return json.loads(result['content'][0]['text'])

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.proc.stderr.close()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name)
        self.db = self.path / 'mailbox.sqlite'
        self.other = self.path / 'other'
        self.other.mkdir()
        self.clients = []

    def client(self, name, project=None, channel=False):
        client = Client(self.db, project or self.path, name, channel)
        self.clients.append(client)
        return client

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.tmp.cleanup()

    def test_request_reply_and_delivery_states(self):
        claude, codex = self.client('claude'), self.client('codex')
        a, b = claude.tool('peers')['self'], codex.tool('peers')['self']
        self.assertEqual(len(claude.tool('peers')['peers']), 2)
        sent = claude.tool('send', to=b, body='Review policy.bend; check project isolation.')
        self.assertEqual(sent['status'], 'queued')
        self.assertEqual(codex.tool('inbox', after=0)[0]['body'], 'Review policy.bend; check project isolation.')
        self.assertEqual(claude.tool('conversation', after=0)[0]['retrieved'], 1)
        self.assertEqual(claude.tool('conversation', after=0)[0]['acked'], 0)
        codex.tool('ack', id=sent['id'])
        codex.tool('send', to=a, body='Reviewed. Cross-project recipients are rejected by Bend.')
        self.assertEqual(len(claude.tool('inbox', after=0)), 1)
        self.assertEqual(len(claude.tool('conversation', after=0)), 2)
        self.assertEqual(claude.tool('conversation', after=0)[0]['acked'], 1)
        self.assertEqual(codex.tool('inbox', after=sent['id']), [])

    def test_policy_rejects_unknown_and_cross_project_recipient(self):
        a, b = self.client('a'), self.client('b', self.other)
        with self.assertRaisesRegex(ValueError, 'Bend policy rejected'):
            a.tool('send', to=b.tool('peers')['self'], body='wrong project')
        with self.assertRaisesRegex(ValueError, 'Bend policy rejected'):
            a.tool('send', to=9999, body='unknown peer')
        self.assertEqual(a.tool('conversation', after=0), [])

    def test_cannot_supply_sender_or_ack_another_inbox(self):
        a, b = self.client('a'), self.client('b')
        with self.assertRaisesRegex(ValueError, 'fields'):
            a.tool('send', to=b.tool('peers')['self'], body='x', sender=123)
        sent = a.tool('send', to=b.tool('peers')['self'], body='x')
        with self.assertRaisesRegex(ValueError, 'not addressed'):
            a.tool('ack', id=sent['id'])

    def test_claude_channel_wire_notification(self):
        a, b = self.client('sender'), self.client('claude', channel=True)
        sent = a.tool('send', to=b.tool('peers')['self'], body='Review requested')
        pushed = b.read()
        self.assertEqual(pushed['method'], 'notifications/claude/channel')
        self.assertEqual(pushed['params']['meta']['message_id'], str(sent['id']))
        self.assertEqual(a.tool('conversation', after=0)[0]['retrieved'], 0)

    def test_unicode_line_separators_are_message_content(self):
        a = self.client('a')
        body = 'line\u2028separator\u2029and newline\nkept'
        a.tool('send', to=a.tool('peers')['self'], body=body)
        self.assertEqual(a.tool('inbox', after=0)[0]['body'], body)


if __name__ == '__main__':
    unittest.main(verbosity=2)

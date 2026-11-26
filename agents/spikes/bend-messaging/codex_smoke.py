"""Use the installed Codex MCP client; no model calls or user config edits."""
import json
import os
import pathlib
import select
import subprocess
import tempfile

from test_bridge import Client, ROOT


def run():
    with tempfile.TemporaryDirectory() as directory:
        work = pathlib.Path(directory)
        db = work / 'mailbox.sqlite'
        config = {'command': 'node', 'args': [str(ROOT / 'bridge.mjs'), '--db', str(db),
                  '--project', str(work), '--name', 'codex-real-client', '--harness', 'codex'],
                  'startup_timeout_sec': 10}
        # The structured TOML object is a single argv value, never shell interpolated.
        toml = '{ command = "node", args = ' + json.dumps(config['args']) + ', startup_timeout_sec = 10 }'
        env = dict(os.environ, CODEX_HOME=str(work / 'codex-home'))
        (work / 'codex-home').mkdir()
        with (ROOT / 'codex-smoke.stderr.log').open('w') as errors:
            proc = subprocess.Popen(['codex', 'app-server', '-c', 'mcp_servers.genius=' + toml],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=errors, text=True, bufsize=1, env=env)
            sequence = 0

            def request(method, params):
                nonlocal sequence
                sequence += 1
                proc.stdin.write(json.dumps({'id': sequence, 'method': method, 'params': params}) + '\n')
                proc.stdin.flush()
                while True:
                    if not select.select([proc.stdout], [], [], 20)[0]:
                        raise TimeoutError(method)
                    line = proc.stdout.readline()
                    if not line:
                        raise RuntimeError('app server closed; see codex-smoke.stderr.log')
                    value = json.loads(line)
                    if value.get('id') == sequence:
                        if 'error' in value:
                            raise RuntimeError(value['error'])
                        return value['result']

            peer = None
            try:
                request('initialize', {'clientInfo': {'name': 'genius-spike', 'version': '0.0.1'},
                                       'capabilities': {'experimentalApi': True}})
                proc.stdin.write('{"method":"initialized"}\n')
                proc.stdin.flush()
                started = request('thread/start', {'cwd': str(work), 'ephemeral': True, 'sandbox': 'read-only', 'approvalPolicy': 'never'})
                thread = started['thread']['id']
                inventory = request('mcpServerStatus/list', {'threadId': thread, 'serverName': 'genius'})

                def tool(name, arguments):
                    result = request('mcpServer/tool/call', {'threadId': thread, 'server': 'genius', 'tool': name, 'arguments': arguments})
                    # Keep raw protocol output to document the actual installed version.
                    records.append({'tool': name, 'result': result})
                    payload = result.get('result', result)
                    if payload.get('isError'):
                        raise RuntimeError(payload)
                    return json.loads(payload['content'][0]['text'])

                records = []
                identity = tool('peers', {})['self']
                peer = Client(db, work, 'claude-protocol-client')
                peer_id = peer.tool('peers')['self']
                peer.tool('send', to=identity, body='Please review policy.bend for project isolation.')
                inbox = tool('inbox', {'after': 0})
                assert len(inbox) == 1
                tool('ack', {'id': inbox[0]['id']})
                tool('send', {'to': peer_id, 'body': 'Received through the actual Codex MCP client; model review not performed.'})
                reply = peer.tool('inbox', after=0)
                assert len(reply) == 1
                conversation = tool('conversation', {'after': 0})
                assert len(conversation) == 2
                evidence = {'codex_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
                            'model_calls': 0, 'claude_client': 'protocol test client, not Claude Code',
                            'inventory': inventory, 'calls': records, 'conversation': conversation}
                (ROOT / 'codex-smoke.json').write_text(json.dumps(evidence, indent=2) + '\n')
                print('PASS: actual Codex app-server discovered five tools and completed MCP request/ack/reply; no model call.')
            finally:
                if peer:
                    peer.close()
                proc.stdin.close()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
                proc.stdout.close()


if __name__ == '__main__':
    run()

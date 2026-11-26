import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def expected_type_rejection(result, expected_pair):
    fields = {}
    for line in (result.stdout + result.stderr).splitlines():
        for label in ('expected', 'observed'):
            prefix = f'- {label} : '
            if line.startswith(prefix):
                fields[label] = line[len(prefix):].strip()
    return result.returncode != 0 and (fields.get('expected'), fields.get('observed')) == expected_pair


def main():
    parser = argparse.ArgumentParser(description='Check the Bend 2 reasoning experiment with the actual compiler.')
    parser.add_argument('--bend', default=os.environ.get('BEND_BIN', 'bend'))
    parser.add_argument('--verdict', action='store_true', help='Also check proofs through the Lean-backed kernel.')
    args = parser.parse_args()

    def run(path, *flags):
        return subprocess.run([args.bend, str(path), *flags], text=True, capture_output=True,
                              timeout=60, env=dict(os.environ, BEND_NO_TELEMETRY='1'))

    version = subprocess.run([args.bend, 'version'], text=True, capture_output=True, check=True).stdout.strip()
    if version.removeprefix('bend ').split('.', 1)[0] != '2':
        raise SystemExit(f'Bend 2 required; observed {version!r}')
    print(f'Compiler: {version}')
    proof = run(ROOT / 'PROOF.bend', *(['--verdict'] if args.verdict else []))
    if proof.returncode != 0 or 'ALL PROOFS CHECK' not in proof.stdout:
        raise SystemExit(proof.stdout + proof.stderr)
    print(proof.stdout.strip())
    demo = run(ROOT / 'demo.bend')
    expected = ('Derived claim: False\nDirected claim: False\nDependent observation: False\n'
                'Unconfirmed observation: False\nIndependent confirmation: True\n')
    if demo.returncode != 0 or demo.stdout != expected:
        raise SystemExit('Unexpected demonstration result:\n' + demo.stdout + demo.stderr)
    print(demo.stdout.strip())

    fixtures = {
        'derived': 'def main() -> Evidence.Support:\n  Evidence.admit(Evidence.Derived{}, {==})\n',
        'directed': 'def main() -> Evidence.Support:\n  Evidence.admit(Evidence.Directed{}, {==})\n',
        'dependent': 'def main() -> Evidence.Support:\n  Evidence.admit(Evidence.Observed{False{}, True{}}, {==})\n',
        'unconfirmed': 'def main() -> Evidence.Support:\n  Evidence.admit(Evidence.Observed{True{}, False{}}, {==})\n',
        'missing_observation_rule': 'def bypass(-Before: Type, -After: Type, action: Before) -> After:\n  action\n',
        'unchecked_reductio': 'def bypass(-Proposition: Type, burden: (Proposition -> Empty) -> Empty) -> Proposition:\n  burden\n',
        'missing_norm': (
            'def bypass() -> (Empty -> Empty) -> Empty:\n'
            '  Reasoning.validation_burden(Unit, Unit, Empty, Unit, Unit, Unit{}, Unit{},\n'
            '    classified => refute => Unit{}, depends => assumption => Unit{}, risk => risk)\n'
        ),
    }
    expected_errors = {
        'derived': ('False{}', 'True{}'),
        'directed': ('False{}', 'True{}'),
        'dependent': ('False{}', 'True{}'),
        'unconfirmed': ('False{}', 'True{}'),
        'missing_observation_rule': ('After', 'Before'),
        'unchecked_reductio': ('Proposition', '@_:(@_:Proposition -> Empty) -> Empty'),
        'missing_norm': ('Empty', 'Unit'),
    }
    with tempfile.TemporaryDirectory(prefix='.check-', dir=ROOT) as temporary:
        for name, body in fixtures.items():
            path = Path(temporary) / f'{name}.bend'
            path.write_text('import Base\nimport ../evidence.bend as Evidence\n'
                            'import ../reasoning.bend as Reasoning\n\n' + body)
            rejected = run(path, '--check-only')
            output = rejected.stdout + rejected.stderr
            if not expected_type_rejection(rejected, expected_errors[name]):
                raise SystemExit(f'{name}: expected a type-check rejection, observed:\n{output}')
            print(f'Rejected as expected: {name}')
        for name, body in {
            'syntax_error': '@@@\n',
            'undefined_name': 'def main() -> Bool:\n  Evidence.missing_name\n',
        }.items():
            path = Path(temporary) / f'{name}.bend'
            path.write_text('import Base\nimport ../evidence.bend as Evidence\n\n' + body)
            control = run(path, '--check-only')
            if control.returncode == 0 or any(expected_type_rejection(control, pair) for pair in expected_errors.values()):
                raise SystemExit(f'{name}: diagnostic control did not fail independently of semantic tests')
            print(f'Excluded unrelated diagnostic: {name}')
    print('PASS: proof modules, executable demo, and seven invalid derivations.')


if __name__ == '__main__':
    main()

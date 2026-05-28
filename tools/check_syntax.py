#!/usr/bin/env python3
"""Check index.html main <script> block for JS syntax errors.

Run before every commit that touches index.html:
    python3 tools/check_syntax.py

Exit 0 = ok, exit 1 = syntax error (with line + context).
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(os.path.dirname(HERE), 'index.html')


def main() -> int:
    if not os.path.exists(INDEX):
        print(f'ERROR: {INDEX} not found', file=sys.stderr)
        return 1

    with open(INDEX) as f:
        html = f.read()

    scripts = list(re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL))
    if not scripts:
        print('ERROR: no <script> blocks in index.html', file=sys.stderr)
        return 1

    main_script = max((m.group(1) for m in scripts), key=len)
    print(f'Checking main <script> block ({len(main_script):,} chars)...')

    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as tmp:
        tmp.write(main_script)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ['node', '--check', tmp_path],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print('ERROR: node not installed. Install with `brew install node`.',
              file=sys.stderr)
        os.unlink(tmp_path)
        return 1
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if result.returncode == 0:
        print('OK')

        # Bonus checks for common silent issues:
        warnings = []

        # 1) Unescaped apostrophe inside single-quoted MAP_LOCATIONS strings.
        ml_match = re.search(
            r"const MAP_LOCATIONS\s*=\s*\[(.*?)\];",
            main_script,
            re.DOTALL,
        )
        if ml_match:
            ml_block = ml_match.group(1)
            # Strip // line comments and /* */ block comments first to skip
            # false positives like `// Children's Neighborhood Museum`.
            ml_no_comments = re.sub(r'//[^\n]*', '', ml_block)
            ml_no_comments = re.sub(r'/\*.*?\*/', '', ml_no_comments, flags=re.DOTALL)
            bad = re.findall(r"'[^'\\]*[A-Za-z]'s\s+[A-Za-z]", ml_no_comments)
            if bad:
                warnings.append(
                    f"  - {len(bad)} possible unescaped apostrophe(s) in "
                    f"MAP_LOCATIONS single-quoted strings (e.g., \"Children's\")."
                    " Escape with \\' or use double-quoted strings."
                )

        # 2) EVENTS array empty / drastically smaller than expected.
        ev_match = re.search(
            r'const EVENTS\s*=\s*\[(.*?)\];', main_script, re.DOTALL,
        )
        if ev_match:
            count = ev_match.group(1).count('"date"')
            if count < 100:
                warnings.append(f'  - EVENTS array only has {count} entries.')

        if warnings:
            print('\nWarnings (script parses but check these):')
            for w in warnings:
                print(w)
        return 0

    # Parse the error message for line + position
    err = result.stderr or result.stdout
    print('\nSYNTAX ERROR in main script block:\n', file=sys.stderr)
    print(err, file=sys.stderr)

    # Show context around the failing line
    line_match = re.search(r':(\d+)\b', err)
    if line_match:
        bad_line = int(line_match.group(1))
        lines = main_script.split('\n')
        if 0 < bad_line <= len(lines):
            print(f'\nContext around script line {bad_line}:', file=sys.stderr)
            for offset in range(-1, 2):
                idx = bad_line - 1 + offset
                if 0 <= idx < len(lines):
                    marker = '>> ' if offset == 0 else '   '
                    snippet = lines[idx]
                    if len(snippet) > 240:
                        snippet = snippet[:240] + '...(truncated)'
                    print(f'{marker}{idx + 1}: {snippet}', file=sys.stderr)

    return 1


if __name__ == '__main__':
    sys.exit(main())

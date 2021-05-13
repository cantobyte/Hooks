#! /usr/bin/env python3 
"""Find all of the files with staged hunks in the git
repository. Run clang-format only on the staged hunks 
from those files.

"""
import subprocess
import shlex
import re
import os
from collections import defaultdict

REFORMAT_EXTS = set(('.c', '.cc', '.cpp', '.h', '.hh', '.hpp'))

def main():
    """Find staged hunks and reformat them."""
    diff_lines = get_cached_diff()
    hunks = parse_hunks_from_diff(diff_lines)
    # print(hunks)
    for filename, line_chunks in hunks.items():
        if format_hunks(filename, line_chunks):
            print(filename)


def get_cached_diff():
    """Return the unified diff between the staged changes and HEAD.

    Return:
    A list of lines of diff output

    """
    git_diff_cmd = 'git diff -U0 --no-color --cached'
    result = subprocess.run(shlex.split(git_diff_cmd),
                            check=True,
                            text=True,
                            capture_output=True)
    # print(result.stdout)
    # if that raises an exception, there's nothing else we can do
    return result.stdout.splitlines()


def parse_hunks_from_diff(diff_lines):
    """Create a dictionary of added file hunks from diff output.

    Arguments:
    diff_lines - A list of lines of diff output to parse

    Return:
    A dictionary of hunks keyed by filename 
    {filename: [(start_line, num_lines), ...]}

    """
    hunks = defaultdict(list)
    filename = ''
    for line in diff_lines:
        if line.startswith('@@'):
            if filename and not os.path.splitext(filename)[1] in REFORMAT_EXTS:
                # If we've set a file and it's not one of the kind we're
                # reformatting, move to the next line
                continue
            if match := re.match('@@ -[0-9,]+ \+([0-9]+)(,[0-9]+)? @@', line):
                start_line = int(match.group(1))
                if match.group(2) is not None:
                    num_lines = int(match.group(2)[1:])
                else:
                    num_lines = 1
                hunks[filename].append((start_line, num_lines))
        elif line.startswith('+++'):
            filename = line[6:]  # strip '+++ b/'
    return hunks


def format_hunks(filename, line_infos):
    """Run clang-format on this file only on the hunks of the
    file indicated by line_infos.

    Arguments:
    filename - The name of the file to reformat
    line_infos - A list of pairs (start_line, num_lines) that indicate 
    which hunks of the file to reformat

    Return:
    True if formatting violations existed, False otherwise

    """
    format_cmd = f'clang-format -i {filename}'
    for start_line, num_lines in line_infos:
        format_cmd += f' --lines={start_line}:{start_line + num_lines}'
    # print(format_cmd)
    # Do a dry run to determine if any changes will be made
    violations = subprocess.run(shlex.split(format_cmd + ' --dry-run'),
                                text=True,
                                check=True,
                                capture_output=True).stderr
    # print(violations)
    if violations.strip():
        result = subprocess.run(shlex.split(format_cmd),
                                text=True,
                                capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f'Error running {format_cmd}: {result.stderr}')
        return True
    return False


if __name__ == '__main__':
    main()

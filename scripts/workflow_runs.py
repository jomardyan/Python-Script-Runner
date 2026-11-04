"""Preview workflow-history cleanup by default; execute only with exact confirmation."""
import argparse
import json
import re
import subprocess


def api(arguments):
    return subprocess.check_output(['gh', 'api', *arguments], text=True)


def maintain(repo, current_run, execute=False, confirmation='', request=api):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Expected an owner/repository name')
    if execute and confirmation != repo:
        raise ValueError('Deletion requires confirmation matching the exact owner/repository')
    pages = json.loads(request(['--paginate', '--slurp', f'repos/{repo}/actions/runs?per_page=100&status=completed']))
    selected = sorted({int(run['id']) for page in pages for run in page['workflow_runs']
                       if run['status'] == 'completed' and int(run['id']) != current_run})
    failed = []
    if execute:
        # Snapshot IDs once: a failed DELETE must never cause an endless page-one loop.
        for run_id in selected:
            try:
                request(['--method', 'DELETE', f'repos/{repo}/actions/runs/{run_id}'])
            except subprocess.CalledProcessError:
                failed.append(run_id)
    return dict(mode='execute' if execute else 'preview', selected=len(selected),
                deleted=len(selected)-len(failed) if execute else 0, failed=failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--current-run', type=int, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    try:
        result = maintain(args.repo, args.current_run, args.execute, args.confirm)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result))
    return 1 if result['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

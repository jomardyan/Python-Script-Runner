import json
import subprocess
import unittest
from unittest.mock import Mock

from scripts.workflow_runs import maintain


class WorkflowHistoryTests(unittest.TestCase):
    def pages(self):
        return json.dumps([
            {'workflow_runs': [{'id': 1, 'status': 'completed'}, {'id': 9, 'status': 'completed'}]},
            {'workflow_runs': [{'id': 2, 'status': 'completed'}, {'id': 1, 'status': 'completed'},
                               {'id': 3, 'status': 'in_progress'}]},
        ])

    def test_preview_paginates_without_mutation_and_excludes_current_or_running(self):
        request = Mock(return_value=self.pages())
        result = maintain('owner/repo', 9, request=request)
        self.assertEqual(result, {'mode': 'preview', 'selected': 2, 'deleted': 0, 'failed': []})
        request.assert_called_once_with(['--paginate', '--slurp', 'repos/owner/repo/actions/runs?per_page=100&status=completed'])

    def test_destructive_execution_requires_exact_confirmation_before_any_request(self):
        for confirmation in ['', 'other/repo', 'OWNER/repo']:
            request = Mock()
            with self.subTest(confirmation=confirmation), self.assertRaisesRegex(ValueError, 'confirmation'):
                maintain('owner/repo', 9, True, confirmation, request)
            request.assert_not_called()

    def test_failed_delete_is_attempted_once_and_reported(self):
        request = Mock(side_effect=[self.pages(), subprocess.CalledProcessError(1, 'gh'), ''])
        result = maintain('owner/repo', 9, True, 'owner/repo', request)
        self.assertEqual(result, {'mode': 'execute', 'selected': 2, 'deleted': 1, 'failed': [1]})
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args_list[1].args[0][-1], 'repos/owner/repo/actions/runs/1')
        self.assertEqual(request.call_args_list[2].args[0][-1], 'repos/owner/repo/actions/runs/2')


if __name__ == '__main__':
    unittest.main()

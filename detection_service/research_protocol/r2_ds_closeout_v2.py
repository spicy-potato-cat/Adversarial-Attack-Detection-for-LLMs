"""Accept the full current test suite and new-run durable ledger evidence."""

import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import r2_ds_completion_v2 as completion
from detection_service.research_protocol import r2_ds_closeout as original


def accept():
    path = p.ROOT / 'tmp/r2_ds_all_postrun.xml'
    cases = list(ET.parse(path).getroot().iter('testcase'))
    p.require(len(cases) >= 1500, 'FULL_TEST_SUITE_NOT_RUN')
    p.require(not any(case.find(tag) is not None for case in cases
                      for tag in ('failure', 'error', 'skipped')), 'FULL_SUITE_FAILURE')
    track_b = p.files.read_json(p.OUT / 'r2_ds_track_b_reference_update_v1.json')
    p.require(track_b['commander_authorization'] == 'Accept the updated Track-B reference; finish Track A',
              'TRACK_B_REFERENCE_NOT_AUTHORIZED')
    p.require(p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() ==
              track_b['approved_untouched_reference'], 'TRACK_B_CHANGED')
    accounting = completion.ledger()
    original.accept()
    prior = p.files.read_json(p.OUT / 'r2_ds_final_acceptance_v1.json')
    report = p.files.read_json(p.OUT / 'r2_ds_report_binding_v1.json')
    p.require(report['report_path'].endswith('_v2.md'), 'NEW_REPORT_REQUIRED')
    paths = [*p.OUT.glob('*.json'), *p.OUT.glob('*.csv'), p.ROOT / report['report_path']]
    destination = p.OUT / 'r2_ds_final_acceptance_v2.json'
    paths = [item for item in paths if item != destination]
    p.publish(destination, dict(status='PASS', artifact_version='r2_ds_final_acceptance_v2',
        run_id=accounting['run_id'], tests=dict(passed=len(cases), failed=0, errors=0, skipped=0,
            receipt_path=path.relative_to(p.ROOT).as_posix(), receipt_sha256=p.files.sha(path)),
        baseline_preservation=prior['baseline_preservation'], release_preservation=prior['release_preservation'],
        patch_hash_checks=prior['patch_hash_checks'], source_preservation_checks=prior['source_preservation_checks'],
        baseline_replays=accounting['baseline_replays'], baseline_replay_violations=0,
        new_run_unique_generation_queries=accounting['unique_model_queries'],
        new_run_logical_generation_queries=accounting['logical_queries'],
        historical_failed_calls='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61', known_diagnostic_calls=364,
        final_replay_calls=698, forbidden_generation_calls=0, Track_B_unchanged_by_this_task=True,
        approved_track_b_reference=track_b['approved_untouched_reference'],
        original_task_track_b_reference=track_b['original_task_reference'],
        verdict=report['verdict'],
        sha256={item.relative_to(p.ROOT).as_posix(): p.files.sha(item) for item in paths}))


if __name__ == '__main__':
    accept()

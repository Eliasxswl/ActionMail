"""One status/count comparison for evaluation and owner-amended review."""


def compare_reference(prediction, gold, accepted_outcomes=()):
    if prediction is None:
        return False, False
    status = prediction['status']
    count = len(prediction.get('actions', []))
    if accepted_outcomes:
        return (any(o['status'] == status for o in accepted_outcomes),
                any(o['status'] == status and o['action_count'] == count for o in accepted_outcomes))
    expected_count = len(gold['actions']) if 'actions' in gold else int(gold['status'] == 'action')
    return status == gold['status'], count == expected_count

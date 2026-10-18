"""Sélection des soumissions approuvées pour la consolidation."""


def select_latest_approved_submissions(
    submissions: list[dict[str, str]],
) -> dict[str, str]:
    """Associe chaque rapport à sa dernière soumission approuvée."""

    latest_by_report: dict[str, tuple[int, str]] = {}

    for submission in submissions:
        if submission["status"] != "APPROVED":
            continue

        report_id = submission["report_id"]
        revision_no = int(submission["revision_no"])
        previous = latest_by_report.get(report_id)

        if previous is None or revision_no > previous[0]:
            latest_by_report[report_id] = (
                revision_no,
                submission["submission_id"],
            )

    return {
        report_id: submission_id
        for report_id, (_, submission_id) in latest_by_report.items()
    }

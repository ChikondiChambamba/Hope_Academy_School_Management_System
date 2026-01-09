"""Repair script to populate missing student_fee_exemptions.

Run this script when you suspect student balances disagree with preview due
to missing exemptions. It will:
- For each active student, if they paid one tuition fee type, mark other
  tuition fee types for the same academic year as exempt for that student.
- For students who are not new, add exemptions for Registration and Uniform
  fee types (these fees only apply to new students).

Usage:
    python -m scripts.repair_exemptions
"""
from database.connection import db
import config
import argparse
from typing import List, Tuple


def _fetch_ids_for_year(academic_year: str) -> Tuple[List[int], List[int]]:
    tuition_rows = db.execute_query(
        "SELECT fee_type_id FROM fee_types WHERE academic_year = %s AND LOWER(fee_name) LIKE %s",
        (academic_year, '%tuition%'),
        fetch=True
    ) or []
    tuition_ids = [r['fee_type_id'] for r in tuition_rows]

    reg_rows = db.execute_query(
        "SELECT fee_type_id FROM fee_types WHERE academic_year = %s AND (LOWER(fee_name) LIKE %s OR LOWER(fee_name) LIKE %s)",
        (academic_year, '%registration%', '%uniform%'),
        fetch=True
    ) or []
    reg_ids = [r['fee_type_id'] for r in reg_rows]
    return tuition_ids, reg_ids


def repair_exemptions(academic_year: str = None, dry_run: bool = True, apply: bool = False) -> dict:
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR

    summary = {
        'students_processed': 0,
        'tuition_exemptions_planned': 0,
        'tuition_exemptions_added': 0,
        'reg_uniform_exemptions_planned': 0,
        'reg_uniform_exemptions_added': 0,
        'planned_inserts': [],
        'errors': []
    }

    try:
        tuition_ids, reg_ids = _fetch_ids_for_year(academic_year)

        students = db.execute_query("SELECT student_id, is_new FROM students WHERE is_active = 1", fetch=True) or []

        for s in students:
            sid = s['student_id']
            summary['students_processed'] += 1

            # Determine tuition types the student has paid
            paid = db.execute_query(
                "SELECT DISTINCT ft.fee_type_id FROM student_fees sf JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id "
                "WHERE sf.student_id = %s AND ft.academic_year = %s AND LOWER(ft.fee_name) LIKE %s",
                (sid, academic_year, '%tuition%'),
                fetch=True
            ) or []
            paid_ids = {r['fee_type_id'] for r in paid}

            # Plan tuition exemptions for other tuition types
            if tuition_ids and paid_ids:
                for tid in tuition_ids:
                    if tid not in paid_ids:
                        summary['planned_inserts'].append((sid, tid, 'Auto-exempted because another tuition paid'))
                        summary['tuition_exemptions_planned'] += 1

            # Plan reg/uniform exemptions for returning students
            if not s.get('is_new') and reg_ids:
                for rid in reg_ids:
                    summary['planned_inserts'].append((sid, rid, 'Auto-exempted for returning student'))
                    summary['reg_uniform_exemptions_planned'] += 1

        # If apply requested, execute planned inserts
        if apply and summary['planned_inserts']:
            for sid, fid, reason in summary['planned_inserts']:
                try:
                    db.execute_query(
                        "INSERT IGNORE INTO student_fee_exemptions (student_id, fee_type_id, reason) VALUES (%s, %s, %s)",
                        (sid, fid, reason)
                    )
                    if 'tuition' in reason.lower():
                        summary['tuition_exemptions_added'] += 1
                    else:
                        summary['reg_uniform_exemptions_added'] += 1
                except Exception as e:
                    summary['errors'].append(str(e))

        return summary

    except Exception as e:
        summary['errors'].append(str(e))
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repair student fee exemptions (dry-run by default)')
    parser.add_argument('--year', '-y', help='Academic year to target (default: current)', default=None)
    parser.add_argument('--apply', action='store_true', help='Actually apply changes to the database')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of students to process (0 = all)')
    args = parser.parse_args()

    print('Scanning for missing student fee exemptions...')
    summary = repair_exemptions(academic_year=args.year, dry_run=not args.apply, apply=args.apply)

    planned = summary.get('planned_inserts', [])
    print(f"Students processed: {summary.get('students_processed', 0)}")
    print(f"Planned tuition exemptions: {summary.get('tuition_exemptions_planned', 0)}")
    print(f"Planned reg/uniform exemptions: {summary.get('reg_uniform_exemptions_planned', 0)}")

    if planned:
        print('\nSample planned inserts (first 50):')
        for sid, fid, reason in planned[:50]:
            print(f"INSERT IGNORE INTO student_fee_exemptions (student_id, fee_type_id, reason) VALUES ({sid}, {fid}, '{reason}')")

    if args.apply:
        print('\nApply mode: attempted to write changes to the database.')
        print(f"Tuition exemptions added: {summary.get('tuition_exemptions_added', 0)}")
        print(f"Reg/Uniform exemptions added: {summary.get('reg_uniform_exemptions_added', 0)}")
    else:
        print('\nDry-run mode: no changes made. To apply, re-run with --apply')

    if summary.get('errors'):
        print('\nErrors encountered:')
        for e in summary['errors']:
            print('-', e)

    print('\nDone.')

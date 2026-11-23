#!/usr/bin/env python3
"""Undo the automatic tuition exemptions created by an old rule.

Until November 2026, recording any payment on a fee whose name contained
"tuition" exempted the pupil from every other "tuition" fee of the academic
year - including other terms - and scripts/repair_exemptions.py applied the
same rule in bulk. Paying Term 3 tuition therefore cancelled Term 2 tuition.

    python scripts/repair_tuition_exemptions.py            # report only, changes nothing
    python scripts/repair_tuition_exemptions.py --apply    # remove the automatic tuition exemptions

--apply removes only exemptions whose recorded reason shows they came from that
rule; exemptions entered for other reasons are kept, and so are exemptions for
pupils who enrolled after that term had ended (they never owed its fees). The removed rows are saved
to a CSV in the backups folder first. Balances already carried into a later term
are NOT changed: the report lists, per pupil, any tuition that the bad exemption
kept out of a rollover, for the school to check before adjusting anything.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from database.connection import db  # noqa: E402

AUTOMATIC = ("reason LIKE 'Exempted because tuition %%' "
             "OR reason = 'Auto-exempted because another tuition paid'")


def automatic_exemptions():
    return db.execute_query(
        f"""
        SELECT e.exemption_id, e.student_id, e.fee_type_id, e.reason, e.created_at,
               s.student_code, CONCAT(s.first_name, ' ', s.last_name) AS student_name, s.class, s.is_active,
               s.enrollment_date,
               ft.fee_name, ft.term, ft.academic_year, ft.amount,
               EXISTS (SELECT 1 FROM fee_type_classes x JOIN classes c ON c.class_id = x.class_id
                       WHERE x.fee_type_id = ft.fee_type_id AND LOWER(c.class_name) = LOWER(s.class))
                 OR NOT EXISTS (SELECT 1 FROM fee_type_classes x0 WHERE x0.fee_type_id = ft.fee_type_id)
                 AS applies_to_class
        FROM student_fee_exemptions e
        JOIN students s ON s.student_id = e.student_id
        JOIN fee_types ft ON ft.fee_type_id = e.fee_type_id
        WHERE {AUTOMATIC}
        ORDER BY s.class, s.last_name, s.first_name
        """, fetch=True) or []


def joined_after_term(row) -> bool:
    """True if the pupil enrolled after the exempted fee's term had ended."""
    if row["academic_year"] != config.Config.CURRENT_ACADEMIC_YEAR:
        return False            # only the current year's term dates are configured
    _, term_end = config.Config.get_term_date_bounds(row["term"])
    enrolled = config.Config.parse_config_date(row["enrollment_date"])
    return bool(term_end and enrolled and enrolled > term_end)


def carry_shortfalls(rows):
    """Tuition a rollover did not carry because the fee was (wrongly) exempted at the time."""
    out = []
    for r in rows:
        if not (r["applies_to_class"] and r["is_active"]):
            continue
        run = db.execute_query(
            "SELECT to_academic_year, to_term, completed_at FROM term_rollover_runs "
            "WHERE status = 'COMPLETED' AND academic_year = %s AND from_term = %s "
            "ORDER BY completed_at DESC LIMIT 1",
            (r["academic_year"], r["term"]), fetch=True)
        if not run or r["created_at"] is None or r["created_at"] >= run[0]["completed_at"]:
            continue    # exempted after the rollover: the debt was carried normally
        paid_here = float(db.execute_query(
            "SELECT COALESCE(SUM(amount_paid), 0) AS s FROM student_fees WHERE student_id = %s AND fee_type_id = %s",
            (r["student_id"], r["fee_type_id"]), fetch=True)[0]["s"])
        # tuition paid in the same term under another (wrong) tuition fee type
        paid_elsewhere = float(db.execute_query(
            "SELECT COALESCE(SUM(sf.amount_paid), 0) AS s FROM student_fees sf JOIN fee_types ft ON ft.fee_type_id = sf.fee_type_id "
            "WHERE sf.student_id = %s AND ft.academic_year = %s AND ft.term = %s AND ft.fee_type_id <> %s "
            "AND LOWER(ft.fee_name) LIKE '%%tuition%%'",
            (r["student_id"], r["academic_year"], r["term"], r["fee_type_id"]), fetch=True)[0]["s"])
        carried = float(db.execute_query(
            "SELECT COALESCE(SUM(carried_amount), 0) AS s FROM student_term_fee_rollover_items "
            "WHERE student_id = %s AND from_academic_year = %s AND from_term = %s AND source_fee_type_id = %s",
            (r["student_id"], r["academic_year"], r["term"], r["fee_type_id"]), fetch=True)[0]["s"])
        shortfall = max(float(r["amount"]) - paid_here - paid_elsewhere - carried, 0.0)
        if shortfall > 0:
            out.append({
                "student_code": r["student_code"], "student_name": r["student_name"], "class": r["class"],
                "fee": f"{r['fee_name']} ({r['term']} {r['academic_year']})", "fee_amount": float(r["amount"]),
                "paid_on_this_fee": paid_here, "paid_on_other_tuition_fees": paid_elsewhere,
                "already_carried": carried, "not_carried_forward": shortfall,
                "carried_into": f"{run[0]['to_term']} {run[0]['to_academic_year'] or r['academic_year']}",
            })
    return out


def write_csv(path, rows):
    if not rows:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="remove the automatic tuition exemptions")
    args = parser.parse_args()
    if config.Config.DB_BACKEND == "sqlite":
        db.prepare()

    found = automatic_exemptions()
    kept = [r for r in found if joined_after_term(r)]
    rows = [r for r in found if not joined_after_term(r)]
    harmful = [r for r in rows if r["applies_to_class"]]
    print(f"Automatic tuition exemptions: {len(found)}")
    print(f"  kept, pupil enrolled after that term ended (never owed it): {len(kept)}")
    print(f"  on a tuition fee that applies to the pupil's own class (waiving tuition they owe): {len(harmful)}")
    print(f"  on a tuition fee for another class (had no effect): {len(rows) - len(harmful)}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(config.Config.PATHS["backups"])
    shortfalls = carry_shortfalls(rows)
    report = write_csv(folder / f"tuition_not_carried_forward_{stamp}.csv", shortfalls)
    print(f"Pupils whose unpaid tuition was left out of a rollover: {len(shortfalls)}, "
          f"total {sum(s['not_carried_forward'] for s in shortfalls):,.2f}")
    if report:
        print(f"  details for checking: {report}")

    if not args.apply:
        print("\nNothing changed. Run with --apply to remove the automatic tuition exemptions.")
        return 0
    if not rows:
        print("Nothing to remove.")
        return 0

    saved = write_csv(folder / f"removed_tuition_exemptions_{stamp}.csv",
                      [{k: r[k] for k in ("exemption_id", "student_id", "fee_type_id", "reason", "created_at",
                                          "student_code", "student_name", "fee_name", "term")} for r in rows])
    with db.transaction() as conn:
        for r in rows:
            db.execute_query_in_transaction(conn, "DELETE FROM student_fee_exemptions WHERE exemption_id = %s",
                                            (r["exemption_id"],))
    print(f"\nRemoved {len(rows)} automatic tuition exemptions. A copy of the removed rows: {saved}")
    print("Balances carried into later terms were not changed; see the report above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

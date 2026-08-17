import json
import re
import sys
from pathlib import Path
from html import escape
from collections import defaultdict


BASE_DIR = Path(__file__).resolve().parent

STATUS_LABELS = {
    "pass": "ผ่าน",
    "partial": "ผ่านบางส่วน",
    "verify": "ต้องยืนยัน",
    "wait": "ยังไม่พบ",
}

FEEDBACK_LABELS = {
    "fix": "FIX",
    "improve": "IMPROVE",
    "next": "NEXT",
}

REVIEW_PATTERN = re.compile(
    r"^week(\d{2})-round(\d{2})\.json$"
)


def read_arguments():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python generate.py <STUDENT_ID>")
        print("  python generate.py --all")
        print()
        print("Example:")
        print("  python generate.py 69319010020")
        print("  python generate.py --all")
        sys.exit(1)

    return sys.argv[1]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_reviews(student_dir):
    reviews = []

    for path in student_dir.glob("week??-round??.json"):
        match = REVIEW_PATTERN.match(path.name)

        if not match:
            continue

        week = int(match.group(1))
        review_round = int(match.group(2))

        reviews.append({
            "week": week,
            "round": review_round,
            "path": path,
        })

    reviews.sort(
        key=lambda item: (item["week"], item["round"])
    )

    return reviews


def validate_review(review, student_id, week, review_round):
    if review.get("student_id") != student_id:
        raise ValueError(
            f"{review['student_id']}: Student ID does not match "
            f"file for {student_id}"
        )

    if review.get("week") != week:
        raise ValueError(
            f"Week does not match: expected {week}"
        )

    if review.get("review_round") != review_round:
        raise ValueError(
            f"Review round does not match: expected {review_round}"
        )


def build_result_map(review):
    return {
        item["criterion_id"]: item
        for item in review.get("items", [])
    }


def calculate_summary(review):
    summary = {
        "pass": 0,
        "partial": 0,
        "verify": 0,
        "wait": 0,
    }

    for item in review.get("items", []):
        status = item.get("status", "verify")

        if status not in summary:
            status = "verify"

        summary[status] += 1

    return summary


def calculate_section_summary(section, result_map):
    passed = 0
    total = len(section["criteria"])

    for criterion in section["criteria"]:
        result = result_map.get(criterion["id"])

        if result and result.get("status") == "pass":
            passed += 1

    return passed, total


def status_badge(status):
    safe_status = (
        status if status in STATUS_LABELS else "verify"
    )

    label = STATUS_LABELS[safe_status]

    return (
        f'<span class="badge badge-{safe_status}">'
        f'{escape(label)}'
        f'</span>'
    )


def generate_section(section, result_map):
    passed, total = calculate_section_summary(
        section,
        result_map,
    )

    rows = []

    for criterion in section["criteria"]:
        criterion_id = criterion["id"]
        label = criterion["label"]

        result = result_map.get(
            criterion_id,
            {
                "status": "verify",
                "detail": "ไม่มีผลการตรวจสำหรับเกณฑ์นี้",
            },
        )

        status = result.get("status", "verify")
        detail = result.get("detail", "")

        rows.append(
            f"""
            <tr>
                <td>{escape(label)}</td>
                <td>{status_badge(status)}</td>
                <td>{escape(detail)}</td>
            </tr>
            """
        )

    return f"""
    <section class="review-section">

        <div class="section-heading">
            <h2>{escape(section["title"])}</h2>
            <span>{passed} / {total} ผ่าน</span>
        </div>

        <table>
            <thead>
                <tr>
                    <th>เกณฑ์</th>
                    <th>สถานะ</th>
                    <th>รายละเอียดจาก AI Review</th>
                </tr>
            </thead>

            <tbody>
                {''.join(rows)}
            </tbody>
        </table>

    </section>
    """


def generate_feedback(feedback):
    if not feedback:
        return "<p>ไม่มี Feedback เพิ่มเติม</p>"

    items = []

    for item in feedback:
        feedback_type = item.get(
            "type",
            "improve",
        )

        message = item.get(
            "message",
            "",
        )

        label = FEEDBACK_LABELS.get(
            feedback_type,
            feedback_type.upper(),
        )

        items.append(
            f"""
            <li>
                <strong>{escape(label)}</strong>
                {escape(message)}
            </li>
            """
        )

    return f"<ul>{''.join(items)}</ul>"


def build_history(reviews, current_week, current_round, page_type):
    grouped = defaultdict(list)

    for item in reviews:
        grouped[item["week"]].append(item)

    blocks = []

    for week in sorted(grouped.keys(), reverse=True):
        links = []

        for item in sorted(
            grouped[week],
            key=lambda x: x["round"],
        ):
            week_number = item["week"]
            round_number = item["round"]

            is_current = (
                week_number == current_week
                and round_number == current_round
            )

            if page_type == "index":
                href = (
                    f"./reviews/"
                    f"week{week_number:02d}-"
                    f"round{round_number:02d}.html"
                )
            else:
                href = (
                    f"./week{week_number:02d}-"
                    f"round{round_number:02d}.html"
                )

            current_class = (
                " history-current"
                if is_current
                else ""
            )

            current_text = (
                " · ล่าสุด"
                if is_current and page_type == "index"
                else ""
            )

            links.append(
                f"""
                <a class="history-link{current_class}"
                   href="{href}">
                    รอบที่ {round_number}{current_text}
                </a>
                """
            )

        blocks.append(
            f"""
            <div class="history-week">
                <strong>Week {week}</strong>

                <div class="history-links">
                    {''.join(links)}
                </div>
            </div>
            """
        )

    return "".join(blocks)


def generate_html(
    student_id,
    rules,
    review,
    reviews,
    page_type,
):
    week = review["week"]
    review_round = review["review_round"]

    result_map = build_result_map(review)
    summary = calculate_summary(review)

    sections_html = "".join(
        generate_section(section, result_map)
        for section in rules["sections"]
    )

    feedback_html = generate_feedback(
        review.get("feedback", [])
    )

    history_html = build_history(
        reviews,
        week,
        review_round,
        page_type,
    )

    if page_type == "index":
        back_link = ""
        latest_text = " · ผลล่าสุด"
    else:
        back_link = """
        <div class="back-link">
            <a href="../index.html">
                ← กลับหน้าผลล่าสุด
            </a>
        </div>
        """
        latest_text = ""

    return f"""<!DOCTYPE html>
<html lang="th">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
AI Review - {escape(student_id)}
</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 0;
    background: #f4f6f8;
    color: #222;
}}

.container {{
    max-width: 1100px;
    margin: 40px auto;
    padding: 0 20px;
}}

.header,
.history,
.summary,
.review-section,
.feedback {{
    background: white;
    border-radius: 10px;
    padding: 24px;
    margin-bottom: 20px;
}}

.header h1 {{
    margin-top: 0;
}}

.meta {{
    line-height: 1.8;
}}

.summary-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}}

.summary-card {{
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}}

.summary-number {{
    font-size: 28px;
    font-weight: bold;
}}

.section-heading {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}}

th,
td {{
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
    vertical-align: top;
}}

th {{
    background: #f7f7f7;
}}

.badge {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 13px;
    white-space: nowrap;
}}

.badge-pass {{
    background: #dff5e3;
}}

.badge-partial {{
    background: #fff0c7;
}}

.badge-verify {{
    background: #dcecff;
}}

.badge-wait {{
    background: #eeeeee;
}}

.history-week {{
    margin-top: 18px;
}}

.history-links {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}}

.history-link {{
    display: inline-block;
    text-decoration: none;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 12px;
    color: #222;
    background: #fafafa;
}}

.history-link:hover {{
    background: #eeeeee;
}}

.history-current {{
    font-weight: bold;
    border-color: #777;
}}

.feedback li {{
    margin-bottom: 10px;
    line-height: 1.6;
}}

.back-link {{
    margin-bottom: 20px;
}}

.back-link a {{
    text-decoration: none;
}}

@media (max-width: 700px) {{

    .summary-grid {{
        grid-template-columns: repeat(2, 1fr);
    }}

    table {{
        font-size: 14px;
    }}

}}

</style>

</head>

<body>

<div class="container">

    {back_link}

    <section class="header">

        <h1>Student Progress</h1>

        <div class="meta">

            <strong>Student ID:</strong>
            {escape(student_id)}
            <br>

            <strong>Week:</strong>
            {week}
            <br>

            <strong>AI Review:</strong>
            รอบที่ {review_round}{latest_text}
            <br>

            <strong>Workshop:</strong>
            {escape(rules["title"])}

        </div>

    </section>

    <section class="history">

        <h2>Review History</h2>

        {history_html}

    </section>

    <section class="summary">

        <h2>Review Summary</h2>

        <div class="summary-grid">

            <div class="summary-card">
                <div class="summary-number">
                    {summary["pass"]}
                </div>
                ผ่าน
            </div>

            <div class="summary-card">
                <div class="summary-number">
                    {summary["partial"]}
                </div>
                ผ่านบางส่วน
            </div>

            <div class="summary-card">
                <div class="summary-number">
                    {summary["verify"]}
                </div>
                ต้องยืนยัน
            </div>

            <div class="summary-card">
                <div class="summary-number">
                    {summary["wait"]}
                </div>
                ยังไม่พบ
            </div>

        </div>

    </section>

    {sections_html}

    <section class="feedback">

        <h2>
            สิ่งที่ควรตรวจสอบ / แก้ไขต่อ
        </h2>

        {feedback_html}

    </section>

</div>

</body>

</html>
"""

def generate_student(student_id):

    student_dir = BASE_DIR / student_id

    print()
    print("=== AI Review HTML Generator V2 ===")
    print(f"Student : {student_id}")

    if not student_dir.exists():
        raise FileNotFoundError(
            f"Student directory not found: {student_dir}"
        )

    reviews = find_reviews(student_dir)

    if not reviews:
        raise FileNotFoundError(
            f"No review files found for {student_id}"
        )

    print(f"Reviews : {len(reviews)}")

    loaded_reviews = []

    for item in reviews:

        review = load_json(item["path"])

        validate_review(
            review,
            student_id,
            item["week"],
            item["round"],
        )

        loaded_reviews.append({
            **item,
            "data": review,
        })

        print(
            f"Found   : "
            f"Week {item['week']} "
            f"Round {item['round']}"
        )

    latest = max(
        loaded_reviews,
        key=lambda item: (
            item["week"],
            item["round"],
        ),
    )

    print(
        f"Latest  : "
        f"Week {latest['week']} "
        f"Round {latest['round']}"
    )

    reviews_dir = student_dir / "reviews"

    reviews_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Generate HTML for every review round

    for item in loaded_reviews:

        week = item["week"]
        review_round = item["round"]
        review = item["data"]

        rule_file = (
            BASE_DIR
            / "review-rules"
            / f"week{week:02d}.json"
        )

        if not rule_file.exists():
            raise FileNotFoundError(
                f"Rule file not found: {rule_file}"
            )

        rules = load_json(rule_file)

        history_html = generate_html(
            student_id,
            rules,
            review,
            loaded_reviews,
            "history",
        )

        output_file = (
            reviews_dir
            / (
                f"week{week:02d}-"
                f"round{review_round:02d}.html"
            )
        )

        output_file.write_text(
            history_html,
            encoding="utf-8",
        )

        print(
            f"Generated: "
            f"{output_file}"
        )

    # Generate latest page

    latest_week = latest["week"]

    latest_rule_file = (
        BASE_DIR
        / "review-rules"
        / f"week{latest_week:02d}.json"
    )

    latest_rules = load_json(
        latest_rule_file
    )

    latest_html = generate_html(
        student_id,
        latest_rules,
        latest["data"],
        loaded_reviews,
        "index",
    )

    output_file = (
        student_dir
        / "index.html"
    )

    output_file.write_text(
        latest_html,
        encoding="utf-8",
    )

    print(
        f"Generated: "
        f"{output_file}"
    )

    print("=== SUCCESS ===")

def main():

    argument = read_arguments()

    # Generate all students from students.json
    if argument == "--all":

        students_file = BASE_DIR / "students.json"

        if not students_file.exists():
            raise FileNotFoundError(
                f"students.json not found: {students_file}"
            )

        data = load_json(students_file)

        students = data.get("students", [])

        if not students:
            raise ValueError(
                "No students found in students.json"
            )

        print("=== AI Review HTML Generator V2 ===")
        print("Mode    : ALL STUDENTS")
        print(f"Students: {len(students)}")

        success = 0
        skipped = 0
        failed = 0

        for student in students:

            student_id = student.get("student_id")

            if not student_id:
                print()
                print("SKIP: student_id not found")
                skipped += 1
                continue

            student_dir = BASE_DIR / student_id

            # Student has no review directory yet
            if not student_dir.exists():
                print()
                print(
                    f"SKIP: {student_id} "
                    f"- student directory not found"
                )
                skipped += 1
                continue

            # Student has directory but no review JSON yet
            reviews = find_reviews(student_dir)

            if not reviews:
                print()
                print(
                    f"SKIP: {student_id} "
                    f"- no review files found"
                )
                skipped += 1
                continue

            try:
                generate_student(student_id)
                success += 1

            except Exception as error:
                print()
                print(
                    f"ERROR: {student_id} "
                    f"- {error}"
                )
                failed += 1

        print()
        print("=== GENERATE ALL SUMMARY ===")
        print(f"Success : {success}")
        print(f"Skipped : {skipped}")
        print(f"Failed  : {failed}")
        print("=== FINISHED ===")

        if failed > 0:
            sys.exit(1)

        return

    # Generate one student
    generate_student(argument)


if __name__ == "__main__":
    main()

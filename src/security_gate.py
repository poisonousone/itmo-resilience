import json
import sys


def check(path):
    with open(path, encoding="utf-8") as file:
        report = json.load(file)

    findings = []

    for result in report.get("Results") or []:
        issues = (result.get("Vulnerabilities") or []) + (result.get("Misconfigurations") or [])

        for issue in issues:
            if issue.get("Severity") in ("HIGH", "CRITICAL"):
                findings.append(issue)

    for issue in findings:
        name = issue.get("VulnerabilityID", issue.get("ID", "Unknown"))
        print(f"{issue['Severity']}: {name}")

    if findings:
        raise SystemExit("FAILED: security gate")

    print(f"PASSED: {path}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        check(path)


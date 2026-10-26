"""Create the original fictional demo corpus and fixed evaluation questions."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ["guest", "alice", "bob"]

# id, title, access group, evidence sentence, direct question, paraphrased question
DOCUMENTS = [
    ("pub01", "Visitor check-in", "public", "Visitors must sign in at the lobby desk and wear a blue visitor badge while inside Cedarline Cooperative offices.", "What badge must visitors wear in the office?", "How can staff identify a guest on site?"),
    ("pub02", "Meeting room bookings", "public", "Meeting rooms may be reserved at most fourteen calendar days ahead through the shared calendar.", "How far ahead can a meeting room be booked?", "What is the advance booking window for a room?"),
    ("pub03", "Office hours", "public", "The reception desk is staffed from 9:00 a.m. to 5:00 p.m. on weekdays, excluding listed holidays.", "When is the reception desk staffed?", "Can I find someone at reception on a weekday afternoon?"),
    ("pub04", "Lost property", "public", "Found items go to the reception desk, where they are kept for thirty days before donation.", "How long are found items kept?", "Where should someone take a misplaced item?"),
    ("pub05", "Bike parking", "public", "Members may park bicycles in the covered rack behind the east entrance; bicycles may not be left in hallways.", "Where may members park bicycles?", "Is it acceptable to leave a bike in the corridor?"),
    ("pub06", "Guest Wi-Fi", "public", "The guest Wi-Fi network is named Cedarline-Guest and its daily password is displayed at reception.", "Where is the guest Wi-Fi password displayed?", "Which wireless network should a visitor choose?"),
    ("pub07", "Kitchen cleanup", "public", "Anyone using the shared kitchen must label refrigerated food with a name and date and remove it by Friday evening.", "When must refrigerated food be removed?", "What label goes on food in the communal fridge?"),
    ("pub08", "Mail delivery", "public", "Incoming parcels are logged at reception, and the named recipient receives an email for collection within five business days.", "How is a parcel recipient notified?", "How long can a package wait for pickup?"),
    ("pub09", "Workshop registration", "public", "Workshop registration closes at noon two business days before the event, and remaining places are released to the waiting list.", "When does workshop registration close?", "At what point are spare workshop seats offered to the waiting list?"),
    ("pub10", "Accessibility requests", "public", "Accessibility requests for events should be sent to the events desk at least five business days in advance.", "How early should event accessibility requests be sent?", "Who receives a request for event accommodations?"),
    ("pub11", "Emergency assembly", "public", "During an evacuation, people should use the nearest safe exit and gather at the north garden assembly point.", "Where is the emergency assembly point?", None),
    ("pub12", "Public printing", "public", "Guests may print up to ten black-and-white pages per visit at the reception printer.", "How many pages may a guest print per visit?", None),
    ("alice01", "Design review schedule", "alice", "Alice's design team holds its prototype review every Tuesday at 2:30 p.m. in Room Fern.", "When is Alice's prototype review?", None),
    ("alice02", "Interface testing budget", "alice", "Alice's interface team may spend up to 600 fictional credits per quarter on moderated usability sessions.", "What is Alice's quarterly usability-session budget?", None),
    ("alice03", "Research consent", "alice", "Alice's researchers must obtain written participant consent before recording an interview.", "What consent is needed before Alice's team records an interview?", None),
    ("alice04", "Prototype archive", "alice", "Alice's prototype files are archived in the design vault on the first business day of each month.", "When are Alice's prototype files archived?", None),
    ("alice05", "Color review", "alice", "Alice's design team checks every new chart against a 4.5-to-1 text contrast target before release.", "What contrast target does Alice's team check?", None),
    ("alice06", "Interview notes", "alice", "Alice's interview notes are retained for ninety days after the study closes.", "How long are Alice's interview notes retained?", None),
    ("alice07", "Design handoff", "alice", "Alice's team sends approved mockups to engineering on Thursday mornings through the handoff board.", "When does Alice's team hand approved mockups to engineering?", None),
    ("alice08", "Sketch library", "alice", "Alice's sketch library uses the prefix CL-UX for every reusable component record.", "What prefix identifies reusable components in Alice's library?", None),
    ("alice09", "Pilot feedback", "alice", "Alice's pilot feedback is reviewed by two researchers before it appears in a design summary.", "How many researchers review Alice's pilot feedback?", None),
    ("bob01", "Inventory count", "bob", "Bob's operations team counts storage-room inventory on the last Wednesday of each month.", "When does Bob's team count storage-room inventory?", None),
    ("bob02", "Repair approval", "bob", "Bob may approve equipment repairs costing no more than 450 fictional credits without a second signature.", "What repair amount may Bob approve alone?", None),
    ("bob03", "Delivery window", "bob", "Bob's team accepts loading-bay deliveries between 8:00 a.m. and 11:00 a.m. on weekdays.", "When does Bob's team accept loading-bay deliveries?", None),
    ("bob04", "Tool checkout", "bob", "Bob's technicians return borrowed tools to the locked cabinet by 4:00 p.m. on the next business day.", "When must Bob's technicians return borrowed tools?", None),
    ("bob05", "Safety inspection", "bob", "Bob's operations team inspects fire extinguishers on the first Monday of every month.", "When are fire extinguishers inspected by Bob's team?", None),
    ("bob06", "Spare parts", "bob", "Bob's spare-parts shelf is restocked when a labeled bin falls below three units.", "What triggers restocking of Bob's spare-parts shelf?", None),
    ("bob07", "Vehicle log", "bob", "Bob's drivers enter the odometer reading in the vehicle log before returning a shared van key.", "What must Bob's drivers log before returning a van key?", None),
    ("bob08", "Waste collection", "bob", "Bob's team moves sorted recycling to the south loading area every Thursday morning.", "Where does Bob's team move sorted recycling?", None),
    ("bob09", "Equipment labels", "bob", "Bob's team places a red inspection label on equipment that must not be used until repaired.", "What label marks Bob's equipment as unusable?", None),
]

UNANSWERABLE = [
    "What is the cooperative's annual revenue?",
    "Who founded Cedarline Cooperative?",
    "What is the CEO's phone number?",
    "How many employees joined last year?",
    "What is the insurance policy number?",
    "Which building was used before this office?",
    "What is the cafeteria's Sunday menu?",
    "How many shares does each member own?",
    "What was last winter's electricity bill?",
    "Which supplier manufactures the office chairs?",
]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def write_text_pdf(path: Path, title: str, evidence: str) -> None:
    """Write a tiny single-page PDF using standard PDF text operators."""
    lines = [title + ".", evidence, "This public printing note applies to visits at Cedarline Cooperative."]
    wrapped = [part for line in lines for part in textwrap.wrap(line, width=78)]
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in wrapped]
    stream = "BT /F1 12 Tf 50 750 Td 15 TL " + " ".join(f"({line}) Tj T*" for line in escaped) + " ET"
    content = stream.encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        output += f"{offset:010d} 00000 n \n".encode()
    output += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(output)


def main() -> None:
    docs_dir = ROOT / "corpus" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "pub12.md").unlink(missing_ok=True)
    manifest: list[dict] = []
    questions: list[dict] = []
    for doc_id, title, group, evidence, direct, paraphrase in DOCUMENTS:
        grants = PUBLIC if group == "public" else [group]
        filename = f"{doc_id}.pdf" if doc_id == "pub12" else f"{doc_id}.md"
        if doc_id == "pub12":
            write_text_pdf(docs_dir / filename, title, evidence)
        else:
            body = (
                f"# {title}\n\n## Policy\n{evidence}\n\n"
                "## Scope\nThis Cedarline Cooperative note applies only to the activity named in its title. "
                "Staff should consult the current note when the procedure is needed.\n"
            )
            (docs_dir / filename).write_text(body, encoding="utf-8")
        manifest.append({"doc_id": doc_id, "title": title, "path": f"corpus/docs/{filename}", "allowed_users": grants})
        user = "guest" if group == "public" else group
        questions.append({"question_id": f"q-{doc_id}", "user_id": user, "question": direct,
                          "relevant_doc_ids": [doc_id], "answerable": True, "expected_evidence": evidence})
        if paraphrase:
            questions.append({"question_id": f"q-{doc_id}-para", "user_id": "guest", "question": paraphrase,
                              "relevant_doc_ids": [doc_id], "answerable": True, "expected_evidence": evidence})
    # Five of each restricted group are asked from the opposite account.
    for doc_id, _, group, _, direct, _ in [d for d in DOCUMENTS if d[2] != "public" and int(d[0][-2:]) <= 5]:
        other = "bob" if group == "alice" else "alice"
        questions.append({"question_id": f"denied-{doc_id}", "user_id": other, "question": direct,
                          "relevant_doc_ids": [], "forbidden_doc_ids": [doc_id], "answerable": False})
    for index, question in enumerate(UNANSWERABLE, 1):
        questions.append({"question_id": f"unknown-{index:02}", "user_id": PUBLIC[(index - 1) % 3],
                          "question": question, "relevant_doc_ids": [], "answerable": False})
    assert len(manifest) == 30 and len(questions) == 60
    answerable = [q for q in questions if q["answerable"]]
    negative = [q for q in questions if not q["answerable"]]
    assert len(answerable) == 40 and len(negative) == 20
    for index, item in enumerate(answerable):
        item["split"] = "dev" if index < 10 else "test"
    for index, item in enumerate(negative):
        item["split"] = "dev" if index < 5 else "test"
    write_jsonl(ROOT / "corpus" / "manifest.jsonl", manifest)
    write_jsonl(ROOT / "labels" / "questions.jsonl", questions)
    print("Wrote 30 documents, 30 manifest entries, and 60 labeled questions.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Quiz über Pentests (Python 3)
# Idee: Multiple-Choice, Punktesystem, am Ende Ergebnis + Detailauswertung

import random

def ask_question(q):
    print("\n" + q["question"])
    for i, option in enumerate(q["options"], start=1):
        print(f"  {i}) {option}")

    # Eingabe prüfen
    while True:
        user_in = input("Deine Antwort (Zahl): ").strip()
        if user_in.isdigit():
            idx = int(user_in)
            if 1 <= idx <= len(q["options"]):
                return idx - 1
        print("Ungültige Eingabe. Bitte eine Zahl im richtigen Bereich eingeben.")

def grade_answer(question, user_index):
    correct_index = question["answer_index"]
    if user_index == correct_index:
        return True
    return False

def main():
    questions = [
        {
            "question": "Was ist das Ziel eines Penetrationstests?",
            "options": [
                "Sicherheitslücken finden und deren Auswirkung bewerten",
                "Passwörter zu knacken, um Zugriff zu beweisen",
                "Netzwerktraffic zu verschlüsseln",
                "Systeme automatisch zu patchen"
            ],
            "answer_index": 0
        },
        {
            "question": "Welche Phase gehört typischerweise zu einem Penetrationstest?",
            "options": [
                "Reconnaissance (Informationsbeschaffung)",
                "Speculation (Hypothesenbildung)",
                "Photosynthesis",
                "Compiling ohne Scans"
            ],
            "answer_index": 0
        },
        {
            "question": "Was beschreibt der Begriff „Threat Model“ am besten?",
            "options": [
                "Eine Modellierung möglicher Angreifer, Ziele und Auswirkungen",
                "Eine Liste der verwendeten Tools",
                "Ein Verfahren zum Verschlüsseln von Daten",
                "Ein Ersatz für Risikoanalyse"
            ],
            "answer_index": 0
        },
        {
            "question": "Warum ist „Scope“ (Testumfang) wichtig?",
            "options": [
                "Damit nur autorisierte Systeme/Methoden getestet werden",
                "Damit Angreifer bessere Bedingungen haben",
                "Damit keine Reports erstellt werden müssen",
                "Damit nur lokale Maschinen geprüft werden"
            ],
            "answer_index": 0
        },
        {
            "question": "Welche Information ist vor dem Start eines Tests besonders wichtig zu klären?",
            "options": [
                "Die Ziele, Systeme, erlaubte Zeitfenster und Regeln/Constraints",
                "Welche Songs im Team abgespielt werden",
                "Welche Programmiersprache verwendet wird",
                "Wie schnell die Firewall schaltet"
            ],
            "answer_index": 0
        },
        {
            "question": "Was bedeutet „Proof of Concept (PoC)“ in der Sicherheitspraxis?",
            "options": [
                "Ein Beispiel/Beleg, dass eine Schwachstelle grundsätzlich ausnutzbar ist",
                "Eine vollständige Migration ins Produktionssystem",
                "Ein Inventar aller Server",
                "Ein Bericht ohne technische Details"
            ],
            "answer_index": 0
        },
        {
            "question": "Welche Aussage zu CVEs ist am treffendsten?",
            "options": [
                "CVE identifiziert bekannte Sicherheitslücken über eine eindeutige Kennung",
                "CVE ist ein Tool zum automatischen Scannen",
                "CVE ist nur für Endgeräte gedacht",
                "CVE ersetzt Risikoanalysen vollständig"
            ],
            "answer_index": 0
        },
        {
            "question": "Welche Aussage zur Berichterstattung ist sinnvoll?",
            "options": [
                "Der Report sollte Befunde, Risiko, Impact und Empfehlungen enthalten",
                "Der Report sollte nur Tools nennen",
                "Der Report sollte keine Details enthalten",
                "Der Report sollte nur „bestanden“ oder „nicht bestanden“ zeigen"
            ],
            "answer_index": 0
        }
    ]

    print("=== Pentest-Quiz ===")
    print("Hinweis: Dieses Quiz ist für Wissen/Verständnis gedacht.\n")

    # Anzahl Fragen festlegen
    while True:
        n_in = input(f"Wie viele Fragen möchtest du? (1-{len(questions)}): ").strip()
        if n_in.isdigit():
            n = int(n_in)
            if 1 <= n <= len(questions):
                break
        print("Ungültige Zahl.")

    selected = random.sample(questions, k=n)

    score = 0
    for i, q in enumerate(selected, start=1):
        print(f"\nFrage {i}/{n}")
        user_idx = ask_question(q)
        if grade_answer(q, user_idx):
            print("✅ Richtig!")
            score += 1
        else:
            correct = q["options"][q["answer_index"]]
            print(f"❌ Falsch. Richtige Antwort: {correct}")

    print("\n=== Ergebnis ===")
    print(f"Dein Score: {score}/{n} ({(score/n)*100:.0f}%)")

    # Kurze Auswertung: Fehlende anzeigen
    print("\nAuswertung (kurz):")
    for i, q in enumerate(selected, start=1):
        correct = q["options"][q["answer_index"]]
        print(f"  {i}) {q['question']}  -> Richtige Antwort: {correct}")

if __name__ == "__main__":
    main()

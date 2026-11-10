r"""The design on the plans: the plans win over the request (team rule, 10 Nov 2026).

    python plan_design.py <plans.pdf> [<plans.pdf> ...] --lot <lot no> [--house-type "<request's>"]

Job 26061: the request said Hyams 145, the plans said Custom, and the team issued
Custom ("Custom is in the plans; we always go by the design in the plans").

Where the design is. Every sheet of a plan set carries the drafter's title
block, and its text reads, word by word,

    @A3 | <design> [- <facade> Facade] | Lot | <lot no> | <street>

Read on the plans of 24 jobs in four regions on 10 Nov 2026, the design in it
was the issued HOUSE TYPE's design every time it named one:

    Sapphire 200 - Kent Facade          Hyams 145 + 60 - Hamptons facade
    Avoca 180 Koba Facade                Hyams 145 + 60 Bedarra Facade
    4+2 Custom Hamptons Facade           Diamond mod (Karri Facade)
    Custom 290 - Maple                   Cabarita 225
    Custom - Secondary dwelling - Mod Facade     TBA ...  (no design yet)

A leading bedroom count ("4+2") is not the design; "+ 60" and "Secondary
dwelling" mark an aux dwelling; "mod" is written "Modified <design>" as the
team writes it (26047 "Modified Custom", 26029 "Modified Diamond with Studio").

The rule (decide): the plans' design wins when it names a different design.
When every word of it is already in the request's house type, the request's
wording stays: the team's HOUSE TYPE can say more than the title block
("Modified Diamond with Studio" for "Diamond mod"). Plans that disagree with
each other, or no design in them, change nothing and are flagged.

The facade follows the same rule (decide_facade; the team, 10 Nov 2026: "yes -
and before the plans are out, fill from the email or the SA; they usually
agree, 26061 was a rare exception"), written "<name> Façade" (CD-2.8). The
areas total is read and reported: HOUSE SIZE already comes from the plans
only (CD-2.7), so a different size is a mistake in the job JSON, flagged.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

AUX_SUFFIX = " + Auxiliary Unit"   # the documents' wording (CD-6.2); OSC's is "<design> + 60" (JD-3.3)
REQ_AUX = re.compile(r"\s*\+\s*(?:auxiliary\s+unit|aux\s+unit|auxiliary|aux|60)\b.*$", re.I)


def words_of(pdf):
    """Every word of a PDF's text, in order (a CAD export shows one word per text piece, a
    simple writer a whole line: split either way)."""
    import pdf_text
    return " ".join(str(p) for p in pdf_text.text_of(pdf)).split()


def title_blocks(words, lot_no):
    """The title-block text before each "Lot <lot_no>" that follows an "@A3" within 15 words."""
    lot = str(lot_no or "").strip()
    out = []
    for i, w in enumerate(words[:-1]):
        if w.lower() != "lot" or words[i + 1].strip(",.") != lot:
            continue
        start = next((k for k in range(i - 1, max(-1, i - 16), -1) if words[k].upper() == "@A3"), None)
        if start is not None and i - start > 1:
            out.append(" ".join(words[start + 1:i]))
    return out


def parse_title(title):
    """{design, facade, aux} from one title-block text (see the module doc for the forms)."""
    t = " ".join(str(title).split())
    t = re.sub(r"^\d+\s*\+\s*\d+\s+", "", t)                      # "4+2 Custom ..." - bedrooms
    facade = None
    m = re.search(r"\(\s*([^()]*?)\s*fa[cç]ade\s*\)\s*$", t, re.I)    # "Diamond mod (Karri Facade)"
    if m:
        facade, t = m.group(1).strip() or None, t[:m.start()].strip()
    parts = [p.strip() for p in re.split(r"\s+-\s+", t) if p.strip()]
    aux = any(re.search(r"\+\s*60\b", p) or re.search(r"secondary\s+dwelling|granny", p, re.I) for p in parts)
    parts = [p for p in parts if not re.fullmatch(r"secondary\s+dwelling|granny\s+flat", p, re.I)]
    design = parts[0] if parts else ""
    if len(parts) > 1 and facade is None:
        facade = re.sub(r"\s*fa[cç]ade$", "", parts[-1], flags=re.I).strip() or None
    elif len(parts) == 1 and facade is None:
        m = re.search(r"\s(\S+)\s+fa[cç]ade$", design, re.I)          # "Avoca 180 Koba Facade"
        if m:
            facade, design = m.group(1), design[:m.start()].strip()
    design = re.sub(r"\s*\+\s*60\b", "", design).strip(" -")
    # "TBA Lot 2051-2058 Integrated Housing" (26052): no design yet; a "Lot" inside is another
    # lot's title, never a design
    if not design or re.match(r"(?:tba|tbc)\b", design, re.I) or re.search(r"\blot\b", design, re.I):
        design = None
    return {"design": design, "facade": facade, "aux": aux}


def total_area(words):
    """The largest "<n.nn> m²" on the plans - the total of the areas table - or None."""
    vals = [float(words[i - 1].replace(",", "")) for i, w in enumerate(words)
            if i and w in ("m²", "m2", "M²", "M2") and re.fullmatch(r"\d{2,3}(?:,\d{3})*\.\d{2}", words[i - 1])]
    return f"{max(vals):.2f}" if vals else None


def from_plans(pdfs, lot_no):
    """What the plans say: {design, facade, aux, size, source, titles, conflict}."""
    seen, sources, sizes, unread = Counter(), {}, [], []
    for pdf in pdfs:
        try:
            words = words_of(pdf)
        except Exception as e:   # less evidence, and said so
            unread.append(f"{Path(pdf).name} ({type(e).__name__})")
            continue
        for t in title_blocks(words, lot_no):
            p = parse_title(t)
            if p["design"]:
                key = (p["design"], p["facade"], p["aux"])
                seen[key] += 1
                sources.setdefault(key, Path(pdf).name)
        sizes.append(total_area(words))
    designs = {k[0] for k in seen}
    size = next((s for s in sizes if s), None)
    none = {"design": None, "facade": None, "aux": False, "size": size, "source": None, "conflict": None,
            "unread": unread}
    if not seen:
        return none
    if len(designs) > 1:
        return dict(none, conflict=sorted(designs))
    key = seen.most_common(1)[0][0]
    return dict(none, design=key[0], facade=key[1], aux=any(k[2] for k in seen), source=sources[key])


def tokens(s):
    words = re.findall(r"[a-z0-9]+", str(s or "").lower())
    return {"modified" if w == "mod" else w for w in words}


def team_wording(design):
    """"Custom mod" -> "Modified Custom", as the team writes it."""
    words = design.split()
    mods = [w for w in words if w.lower() in ("mod", "modified")]
    if not mods:
        return design
    rest = " ".join(w for w in words if w.lower() not in ("mod", "modified"))
    return f"Modified {rest}".strip()


def decide(house_type, plan):
    """(the house type to use or None to keep the request's, why). `plan` is from_plans()."""
    req = " ".join(str(house_type or "").split())
    base = REQ_AUX.sub("", req).strip()
    req_aux = bool(req) and base != req
    if not plan.get("design"):
        return None, "the plans name no design"
    if base and tokens(plan["design"]) <= tokens(base):
        return None, f"the plans' design {plan['design']!r} is the request's {base!r}"
    new = team_wording(plan["design"]) + (AUX_SUFFIX if (req_aux or plan.get("aux")) else "")
    return new, (f"the plans read {plan['design']!r}" + (f" ({plan['source']})" if plan.get("source") else "")
                 + f", the request {base or 'nothing'!r}")


def decide_facade(facade, plan):
    """(the facade to use or None to keep the request's, why) - the design's rule for the facade.
    Written "<name> Façade" with the cedilla, the dominant convention (CD-2.8); "Mod" as the team
    writes it, "Modified Façade" (26032)."""
    got = plan.get("facade")
    mine = " ".join(str(facade or "").split())
    if not got:
        return None, "the plans name no façade"
    if mine and tokens(got) <= tokens(mine):
        return None, f"the plans' façade {got!r} is the request's {mine!r}"
    return f"{team_wording(got)} Façade", f"the plans read façade {got!r}, the request {mine or 'nothing'!r}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--lot", required=True)
    ap.add_argument("--house-type", help="the request's house type, to say which wins")
    ap.add_argument("--facade", help="the request's facade, to say which wins")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    plan = from_plans([Path(p) for p in a.pdfs], a.lot)
    for u in plan["unread"]:
        print(f"UNREAD   : {u}")
    if plan["conflict"]:
        print(f"design   : the plans disagree with each other {plan['conflict']} - nothing taken")
    else:
        print(f"design   : {plan['design'] or 'none in the title blocks'}"
              + (f"  (aux dwelling)" if plan["aux"] else "") + (f"  from {plan['source']}" if plan["source"] else ""))
    print(f"facade   : {plan['facade'] or '-'}")
    print(f"size     : {plan['size'] + ' m²' if plan['size'] else '-'}   (HOUSE SIZE takes the plans' total, CD-2.7)")
    if a.house_type is not None:
        new, why = decide(a.house_type, plan)
        print(f"house type: {('use ' + repr(new)) if new else 'keep ' + repr(a.house_type)} - {why}")
    if a.facade is not None:
        new, why = decide_facade(a.facade, plan)
        print(f"facade    : {('use ' + repr(new)) if new else 'keep ' + repr(a.facade)} - {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

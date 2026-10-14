from dataclasses import dataclass

REFERENCE = "2026-10-12T10:00:00+08:00"
ZONE = "Asia/Taipei"


@dataclass(frozen=True)
class Expected:
    identity: str
    aliases: tuple[str, ...]
    due_date: str | None = None
    due_at: str | None = None
    explicit: str | None = None
    importance: str | None = None


@dataclass(frozen=True)
class Fixture:
    id: str
    text: str
    required: tuple[Expected, ...]
    forbidden: tuple[str, ...]
    optional: tuple[Expected, ...] = ()


LONG_TEXT = """I need to get everything out of my head. There's laundry in the washer, and I think I've already washed it twice because I keep forgetting to hang it up. We're almost out of shampoo. Also groceries, but I should check the fridge first because I keep buying things we already have.

My job application has to be submitted tomorrow by 5pm. First, open the application form and check which documents they need. My resume still needs updating. I want to work on it tonight, but that's just the plan, not another deadline. I keep switching between fixing the wording and changing the layout.

Maya messaged me a few days ago. Reply to Maya. It doesn't need to be a perfect reply.

Dad's birthday dinner is Saturday. I should buy him a card, but the dinner date doesn't mean I have to buy it that day. I also need to book a dentist appointment. I've been putting that off because I don't know which days I'm free.

The kitchen is bothering me. Clean the kitchen. Actually, please don't turn that into fifteen separate chores. I just need somewhere clear to make dinner.

Oh, the electricity bill must be paid by October 15 or there's a late fee. I have the bill in my email. And I need to cancel that free trial before it charges me, but I can't remember when it ends, so first I need to check the renewal date.

I'd like to feel healthier and less scattered. Maybe go for a twenty-minute walk today. I'm not trying to make that urgent. I'm just tired of spending the whole day thinking about what I should do.

There's also my portfolio case study. First finish the project write-up, then add the project to my resume, then send the application. Wait, the application is due tomorrow, so I might need to use the current portfolio instead. I haven't decided.

And the laundry. Please don't let the laundry disappear from this list."""
# Preserve the typography of the approved conversational input.
LONG_TEXT = LONG_TEXT.replace("'", "\u2019")

PROJECT = Expected("project_addition", (
    r"(add|include|put|incorporate|list).*project.*(resume|cv)",
))

LONG = Fixture("long_dump", LONG_TEXT, (
    Expected("laundry", (r"(hang|dry).*laundry", r"hang.*clothes")),
    Expected("shampoo", (r"(buy|get|purchase|pick up).*shampoo",)),
    Expected("groceries", (r"(buy|get|shop|purchase).*grocer", r"grocery shopping"), explicit="check the fridge"),
    Expected("application", (r"(submit|send).*application",), due_at="2026-10-13T17:00:00+08:00",
             explicit="open the application form and check which documents they need"),
    Expected("resume", (r"(update|revise|fix|edit|finish|work on).*resume",)),
    Expected("maya", (r"(reply|respond|message).*maya",)),
    Expected("card", (r"(buy|get|purchase).*card",)),
    Expected("dentist", (r"(book|schedule|arrange).*dent(al|ist)",)),
    Expected("kitchen", (r"(clean|tidy).*kitchen",)),
    Expected("bill", (r"(pay|settle).*(electricity|power|electric).*bill",), due_date="2026-10-15"),
    Expected("trial", (r"(cancel|end).*trial",), explicit="check the renewal date"),
    Expected("walk", (r"(walk|stroll)",)),
    Expected("writeup", (r"(finish|complete|write|prepare).*(write.?up|case study)",)),
), (
    r"(wash|rewash).*laundry", r"(attend|organize|book).*birthday.*dinner",
    r"(become|be|feel).*healthier", r"learn.*pottery",
), (PROJECT, Expected("portfolio_decision", (r"(decide|choose|consider).*portfolio",))))

REPEATED = Fixture("repeated_mentions",
    "I need to pay the electricity bill by October 15. First find the bill in my email. "
    "Also reply to Maya. Oh, the electricity bill, I really must remember to pay that. "
    "And Maya's message is still waiting for a reply. That's the same message I mentioned, not another one.",
    (Expected("bill", LONG.required[9].aliases, due_date="2026-10-15",
              explicit="find the bill in my email", importance="normal"),
     Expected("maya", LONG.required[5].aliases, importance="normal")),
    (r"remember.*(bill|pay)",))

CONDITIONAL = Fixture("revised_plans",
    "I was going to buy a new desk, but I've decided not to. Instead, clear my current desk "
    "tomorrow evening; that's just when I plan to do it. First put the loose papers into one pile. "
    "I also need to send the signed lease by October 16 at noon; missing that deadline would mean "
    "losing the apartment. If the landlord asks for another document, I'll send it, but they "
    "haven't asked for anything else.",
    (Expected("desk", (r"(clear|clean|tidy).*desk",),
              explicit="put the loose papers into one pile", importance="normal"),
     Expected("lease", (r"(send|submit|deliver).*lease",),
              due_at="2026-10-16T12:00:00+08:00", importance="high")),
    (r"(buy|purchase|get).*desk", r"^(sign|obtain).*lease",
     r"(send|submit).*(another|additional|extra).*document",
     r"(ask|contact|message).*landlord"))

FIXTURES = (LONG, REPEATED, CONDITIONAL)

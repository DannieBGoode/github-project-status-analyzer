# AGENTS Instructions

## Testing Requirements

1. Run automated tests before finishing any task.
2. Use the full suite command from repository root:
   - `python run_tests.py`
3. If a change touches behavior, add or update tests in the same task.
4. Prefer targeted unit tests near changed code, then run the full suite.
5. Do not consider work complete if tests fail; fix failures or clearly report blockers.

## Coverage Expectations

1. Increase test coverage incrementally as you work.
2. Add regression tests for every bug fix.
3. For UI/JS changes, add or update tests in `tests/js`.
4. For Python changes, add or update tests in `tests/python`.

## Design Context

### Users
Primary users are CEOs, COOs, VPs, Delivery Managers, and Team Leads.
They use the product to understand project health quickly and reliably for leadership decision-making, status reviews, and communication alignment.
The UI should support rapid scan-and-understand workflows where users must trust reported signals without deep technical digging.

### Brand Personality
Voice and tone should be calm, concise, and assured.
Brand personality: Elegant, Modern, Simple.
Emotional goals are calm and confidence, with interface behavior that feels stable, precise, and predictable.

### Aesthetic Direction
Use a refined, minimal, executive-ready visual style that prioritizes legibility and information hierarchy over decorative complexity.
Support both light and dark themes with consistent contrast and clear semantic status cues.
No explicit external references or anti-references were provided; default to current project visual language and avoid playful, noisy, or gimmicky presentation patterns.

### Design Principles
1. Clarity First: Make status, risk, and outcomes immediately legible with strong hierarchy and concise wording.
2. Trust Through Precision: Use consistent structure, unambiguous labels, and stable interaction behavior to reinforce confidence in output.
3. Executive Scanability: Optimize layouts for fast interpretation, highlighting key signals before details.
4. Elegant Simplicity: Prefer restrained, modern styling and intentional whitespace; avoid visual clutter.
5. Accessible by Default: Maintain strong contrast, keyboard/focus clarity, and reduced-motion support as baseline behavior.

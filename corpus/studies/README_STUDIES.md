# Personal Software Engineering Learning Studies

Start here: **[master_study_and_onboarding_manual.md](master_study_and_onboarding_manual.md)** —
setup from a fresh clone, honest current test status, the 6-module
curriculum (5 engineering modules + a 6th on the philosophical/meta-tooling
layer), and links to real exercises.

Exercises with actual tasks (not just "go read this file") are in
**[EXERCISES.md](EXERCISES.md)**, one section per module — including
Module 6's hands-on **sandbox practicum**: predict a `/eval` result from
`standalone_rca_sandbox.py` before running it, hand-verify the gamma cap,
and trace the correspondence ledger's honesty guard yourself.

Current honest status (see `../TESTING_STANDARD.md` for what these terms
mean): **24 / 24 engines VERIFIED**, 0 / 24 RAN_ONLY, 0 failed, 0 missing (run test_all_engines.py for the live count).
Confirm live with `python ../test_all_engines.py` rather than trusting any
static number in a doc -- this count changed several times in one day
(17 -> 18 -> 23 files, then 15 -> 22 -> 23 of those 23 VERIFIED) as engines
that existed on disk but were never registered in the runner kept turning up
during a full-repo sweep, and as dedicated tests were written for the
remaining RAN_ONLY scripts, ending with `standalone_rca_sandbox.py` --
see the onboarding manual's Chapter 3 for exactly what that test does and
does not claim to verify.

`course_syllabus.md` and `week1_oop_study_guide.md` are now folded into the
onboarding manual above and just point back to it, to stop three documents
from drifting out of sync with each other the way they had before.

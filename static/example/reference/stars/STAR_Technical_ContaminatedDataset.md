# STAR: The Contaminated Dataset
Competencies: Technical, Creativity

**Situation.** A state agency dumped four years of county-level cancer-incidence data the week
before I was meant to write a piece on a suspected disease cluster. The spreadsheet was a
horror – inconsistent county codes, three different spellings of "esophageal," rates that swung
wildly between years for reasons nobody could explain, and a footnote admitting some figures
were "provisional" without saying which.

**Task.** I had to figure out whether the cluster was real or an artifact of bad bookkeeping –
and I had to do it myself, because no one on a small paper was going to hand me a statistician.
If I got it wrong in either direction, I'd either miss a genuine public-health story or terrify
a county over a rounding error.

**Action.** I cleaned the thing by hand in Python – reconciled the county codes against the
census table, collapsed the spelling variants, and flagged every provisional figure so I could
run the numbers with and without them. The wild year-to-year swings turned out to be the tell:
the counties with the scariest spikes were the ones with the smallest populations, where two
extra cases looks like an epidemic and means nothing. So I borrowed a trick from the
demographers and age-adjusted the rates, then set a floor on population size before I'd trust a
spike at all. The "cluster" mostly dissolved. One county, though, held up under every
adjustment I threw at it.

**Result.** I wrote the story about the one county that survived the scrubbing, and left the
others alone – which is the story I'd have gotten exactly backwards if I'd trusted the raw
sheet. The agency later issued a corrected dataset that matched my cleaned version almost row
for row. I am not a statistician, but I have learned that a reporter who can open a messy file
and ask it honest questions is worth a great deal on a small desk.

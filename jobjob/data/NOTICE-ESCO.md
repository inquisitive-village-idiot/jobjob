# ESCO Attribution Notice

`skill_cloud.toml` in this directory contains curated, modified data from
**ESCO (European Skills, Competences, Qualifications and Occupations)**,
© European Union, esco.ec.europa.eu.

ESCO data is reused under [Commission Decision 2011/833/EU](https://eur-lex.europa.eu/eli/dec/2011/833/oj/eng)
on the reuse of Commission documents (Creative Commons Attribution 4.0
International terms): reuse is allowed provided appropriate credit is given and
changes are indicated.

**Changes made** (by `scripts/curate_skill_cloud.py`):

- Selected a subset of skill branches (skills pillar S1/S2/S4/S5, knowledge
  pillar ISCED-F fields, and the transversal skills/competences tree).
- Assigned weighted membership in a jobjob-specific six-category vocabulary
  (communication, collaboration, leadership, creativity, technical, domain).
  Category weights are a jobjob curation judgment, not part of ESCO.
- Assigned snake_case canonical ids derived from the English preferred labels.
- English labels only; other ESCO languages omitted.

The source ESCO release and retrieval date are recorded in the `[cloud]` table
of `skill_cloud.toml`. The European Commission does not endorse this product.

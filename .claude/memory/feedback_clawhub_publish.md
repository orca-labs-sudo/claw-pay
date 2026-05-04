---
name: ClawHub Skill publish — immer --name Flag
description: Beim clawhub publish IMMER --name "claw-pay" mitgeben, sonst zeigt ClawHub "Skill" als Anzeigename
type: feedback
originSessionId: 7c8f7deb-7f0c-48a1-89bc-92efe8ebd4b9
---
Beim Veröffentlichen eines Skill-Updates auf ClawHub IMMER `--slug "claw-pay"` UND explizite `--version` angeben:

```
npx clawhub publish . --slug "claw-pay" --version X.X.X --changelog "..."
```

**Why:**
- Ohne `--slug`: CLI versucht einen NEUEN Skill zu registrieren → Error "Slug is already taken" (weil claw-pay existiert) und nichts wird geupdatet.
- Ohne `--version`: CLI errort mit "must be valid semver" auch wenn package.json / claw.json die Version hat.
- `--name` ist OPTIONAL und nur beim Erst-Publish relevant — beim Update wird der Name aus dem existierenden Skill übernommen.

**How to apply:** Jedes Mal wenn ein Update für den existierenden Skill publiziert wird — `--slug` + `--version` sind Pflicht.

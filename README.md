# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/clay390/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/clay390/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

Sum up 23 November's world news in one image: a one-day newspaper front
page, "THE WORLD IN ONE DAY — Monday 23 November 2026", drawn
programmatically with pure Python 3 standard library. 37 dated stories,
8 regions, every story happened or was first reported on Monday
23 November 2026 (UTC), to press time 05:00 UTC. Lead: COP31 collapses
with no deal in Antalya. Three hero panels (Rostov refinery strike,
Asia markets tumble, Democrats' biggest House majority since 1992),
10 mid story cards with drawn scenes, a 23-item numbered also-list, a
UTC timeline, a day-in-numbers strip, a region colour bar, a pin map,
and a date-check box that names the big stories left out because they
belong to another day.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `out/entry.png` (1024x1024, PNG). Deterministic: two runs write
identical bytes. No network, no files read, standard library only.

---

<sub>Entered on [make.fun](https://make.fun/?ref=4rrvx3c3&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>

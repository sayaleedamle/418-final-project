# TruthCheck — Transcript EDA Results

Generated: 2026-05-02  
Videos analysed: 6  
Channels: Huberman Lab · Nutrition Made Simple (Gil Carvalho)

## Per-video summary

| Video | Channel | Caption | Segments | Words | Duration (min) | Words/min |
|---|---|---|---:|---:|---:|---:|
| Nutrients For Brain Health & Performance | Huberman Lab | manual | 2,502 | 17,175 | 99.1 | 173.3 |
| Rational Approach to Supplementation | Huberman Lab | generated | 3,418 | 21,627 | 241.3 | 89.6 |
| How Foods & Nutrients Control Our Moods | Huberman Lab | manual | 735 | 5,464 | 32.5 | 168.0 |
| What, Why & How of Healthy Eating | Nutrition Made Simple | manual | 85 | 1,415 | 8.3 | 170.1 |
| Heart Disease & Longevity Claims | Nutrition Made Simple | generated | 1,425 | 9,142 | 104.2 | 87.8 |
| Best Longevity Diet & Supplements | Nutrition Made Simple | generated | 2,946 | 17,237 | 192.8 | 89.4 |

## LLM-readability scorecard

Thresholds: noise < 5 % · punctuation > 30 % · keyword density > 1 %

| Video | Caption | Noise % | Punct % | KW density % | Gaps >2 s | Low noise | Punctuated | On-topic |
|---|---|---:|---:|---:|---:|:---:|:---:|:---:|
| Nutrients For Brain Health & Performance | manual | 0.1 | 80.2 | 2.57 | 2 | ✓ | ✓ | ✓ |
| Rational Approach to Supplementation | generated | 0.0 | 15.2 | 2.59 | 0 | ✓ | ✗ | ✓ |
| How Foods & Nutrients Control Our Moods | manual | 0.3 | 78.9 | 3.62 | 0 | ✓ | ✓ | ✓ |
| What, Why & How of Healthy Eating | manual | 0.0 | 91.8 | 1.55 | 1 | ✓ | ✓ | ✓ |
| Heart Disease & Longevity Claims | generated | 0.0 | 25.9 | 1.37 | 2 | ✓ | ✗ | ✓ |
| Best Longevity Diet & Supplements | generated | 0.1 | 23.0 | 1.85 | 3 | ✓ | ✗ | ✓ |

## Token budget (128 k safe window)

| Video | Words | Est. tokens | Fits 128 k? |
|---|---:|---:|:---:|
| Heart Disease & Longevity Claims | 9,142 | 12,189 | Yes |
| Best Longevity Diet & Supplements | 17,237 | 22,982 | Yes |
| Nutrients For Brain Health & Performance | 17,175 | 22,900 | Yes |
| What, Why & How of Healthy Eating | 1,415 | 1,886 | Yes |
| How Foods & Nutrients Control Our Moods | 5,464 | 7,285 | Yes |
| Rational Approach to Supplementation | 21,627 | 28,836 | Yes |

## Top health/nutrition keywords per video

| Video | KW hits | Density % | Top keywords |
|---|---:|---:|---|
| Heart Disease & Longevity Claims | 125 | 1.37 | cholesterol(40), fasting(24), protein(17), diet(10), fat(9), nutrition(6), cardiovascular(6), longevity(4), glucose(4), blood pressure(2) |
| Best Longevity Diet & Supplements | 319 | 1.85 | diet(120), cholesterol(31), protein(23), fiber(22), fasting(19), supplement(15), vitamin(15), cardiovascular(11), fat(10), nutrition(7) |
| Nutrients For Brain Health & Performance | 442 | 2.57 | brain(136), glucose(39), gut(38), diet(27), dopamine(27), cognitive(23), sleep(22), supplement(22), omega(18), metabolism(12) |
| What, Why & How of Healthy Eating | 22 | 1.55 | nutrition(12), diet(8), brain(1), gut(1) |
| How Foods & Nutrients Control Our Moods | 198 | 3.62 | brain(49), gut(45), microbiome(25), dopamine(22), serotonin(19), omega(10), diet(8), sleep(5), calorie(3), nutrition(2) |
| Rational Approach to Supplementation | 561 | 2.59 | sleep(100), hormone(93), supplement(67), nutrition(47), gut(33), microbiome(31), cognitive(31), vitamin(29), brain(25), mineral(22) |

## Key findings

- **On-topic signal**: All videos pass the 1 % keyword threshold.
- **Noise artifacts**: Noise levels are low (<5 %) across all videos.
- **Token budget**: All videos fit within the 128 k safe window — no chunking needed.
- **Punctuation**: Rational Approach to Supplementation, Heart Disease & Longevity Claims, Best Longevity Diet & Supplements have <30 % punctuated segments (likely auto-generated captions). Consider adding punctuation restoration before claim extraction.

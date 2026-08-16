# Guardian content-safety Android fixture

This directory is a synthetic, non-shipping Android fixture. It is deliberately
not referenced by `apps/mobile/android/settings.gradle`, Expo autolinking, or any
release source set. It must never be added to a production artifact.

`FixtureActivity.kt` exercises the signals that Guardian can observe without
capturing a screen or storing child content:

- safe, medium-risk, high-risk, negated, educational/news and Unicode-obfuscated
  titles;
- a custom Canvas view with no accessible text, representing honest
  `UNAVAILABLE`/partial coverage;
- deterministic content changes while the package stays the same;
- synthetic notification and media-metadata broadcasts;
- allowed and blocked synthetic domain `ACTION_VIEW` intents; and
- explicit background/foreground controls.

All payloads are synthetic. The fixture emits metadata only to the local test
harness; it does not contact Guardian APIs and it does not contain real child
data. Runtime installation/connected acceptance is `UNVERIFIED` unless a
separate debug-only Android fixture build is created. The release admission
checks must continue to reject fixture mode and fixture bytes.

Current validation status: `UNVERIFIED` at runtime. The local Android Gradle
wrapper could not start because `JAVA_HOME` is unset and no `java` executable is
available. JSON/static validation was completed; this does not substitute for
an emulator run.

The golden evaluator is the test-only `ContentRiskGoldenEvaluatorTest` in the
Guardian protection module. It loads the 140-case JSON corpus, prints
per-category precision, recall, false positives and false negatives, and fails
if the current deterministic rules regress against the frozen v0 rules
projection. The corpus is a synthetic regression gate, not an accuracy claim.

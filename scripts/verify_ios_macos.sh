#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "verify_ios_macos.sh requires macOS/Xcode; source authoring is supported on Linux." >&2
  exit 2
fi

command -v xcodebuild >/dev/null
command -v swift >/dev/null
command -v pod >/dev/null

if [[ ! -d apps/mobile/ios/Guardian.xcworkspace ]]; then
  (cd apps/mobile/ios && pod install)
fi

swift test --package-path apps/mobile/ios/GuardianPolicyCore
xcodebuild \
  -workspace apps/mobile/ios/Guardian.xcworkspace \
  -scheme Guardian \
  -sdk iphonesimulator \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  build

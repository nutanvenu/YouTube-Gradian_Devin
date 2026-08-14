// swift-tools-version: 5.9
import PackageDescription

let package = Package(
  name: "GuardianPolicyCore",
  platforms: [.iOS(.v16)],
  products: [
    .library(name: "GuardianPolicyCore", targets: ["GuardianPolicyCore"])
  ],
  targets: [
    .target(name: "GuardianPolicyCore"),
    .testTarget(
      name: "GuardianPolicyCoreTests",
      dependencies: ["GuardianPolicyCore"]
    )
  ]
)

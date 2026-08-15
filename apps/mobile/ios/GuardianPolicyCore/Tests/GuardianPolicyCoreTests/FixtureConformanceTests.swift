import Foundation
import XCTest
@testable import GuardianPolicyCore

final class FixtureConformanceTests: XCTestCase {
  func testEveryPolicyFixtureCaseExecutesAndMatches() throws {
    let root = URL(fileURLWithPath: #filePath)
      .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    let fixture = root.appendingPathComponent("../../../../packages/test-fixtures/policy-decision-cases.json").standardizedFileURL
    let data = try Data(contentsOf: fixture)
    let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]
    let bundles = json["bundles"] as! [String: Any]
    let cases = json["cases"] as! [[String: Any]]
    var executed = 0
    for item in cases {
      let bundle = try JSONValue(bundles[item["bundle_ref"] as! String]!)
      let context = try JSONValue(item["context"]!)
      let actual = GuardianPolicyEvaluator.evaluate(bundle: bundle, context: context)
      let expected = item["expected"] as! [String: Any]
      XCTAssertEqual(actual.action, expected["action"] as? String, item["id"] as! String)
      XCTAssertEqual(actual.reasonCode, expected["reason_code"] as? String, item["id"] as! String)
      XCTAssertEqual(actual.policyRuleID, expected["policy_rule_id"] as? String, item["id"] as! String)
      XCTAssertEqual(actual.bundleStale, expected["bundle_stale"] as? Bool, item["id"] as! String)
      executed += 1
    }
    XCTAssertEqual(executed, cases.count)
  }
}

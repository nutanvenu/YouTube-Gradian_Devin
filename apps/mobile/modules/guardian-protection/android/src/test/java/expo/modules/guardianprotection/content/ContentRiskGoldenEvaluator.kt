package expo.modules.guardianprotection.content

import org.json.JSONObject

data class GoldenCase(
  val id: String,
  val source: SignalSource,
  val appRef: String,
  val title: String?,
  val text: String?,
  val expectedCategory: String?,
  val baselineCategory: String?,
  val capability: ContentCapabilityLevel,
  val availability: String,
)

data class CategoryMetric(
  val category: String,
  val precision: Double,
  val recall: Double,
  val falsePositives: Int,
  val falseNegatives: Int,
  val truePositives: Int,
)

data class GoldenEvaluationReport(
  val totalCases: Int,
  val evaluatedCases: Int,
  val unavailableCases: Int,
  val current: Map<String, CategoryMetric>,
  val baseline: Map<String, CategoryMetric>,
) {
  fun render(): String = buildString {
    appendLine("Synthetic fixture classifier evaluation; not real-world accuracy.")
    appendLine("cases=$totalCases evaluated=$evaluatedCases unavailable=$unavailableCases")
    current.keys.sorted().forEach { category ->
      val now = current.getValue(category)
      val old = baseline.getValue(category)
      appendLine(
        "$category " +
          "precision=${"%.3f".format(now.precision)} " +
          "recall=${"%.3f".format(now.recall)} " +
          "fp=${now.falsePositives} fn=${now.falseNegatives} " +
          "baseline_precision=${"%.3f".format(old.precision)} " +
          "baseline_recall=${"%.3f".format(old.recall)}",
      )
    }
  }
}

/**
 * Evaluates only the deterministic MVP provider. The frozen v0 projection in the
 * JSON is a regression baseline, not a claim about production accuracy.
 */
object ContentRiskGoldenEvaluator {
  private const val RESOURCE = "content-risk-golden.json"

  fun evaluate(
    classifier: ContentRiskClassifier = DeterministicContentRiskClassifier(),
  ): GoldenEvaluationReport {
    val cases = loadCases()
    val evaluated = cases.filter { it.availability != "UNAVAILABLE" }
    val currentPredictions = evaluated.associateWith { prediction(it, classifier) }
    val baselinePredictions = evaluated.associateWith { it.baselineCategory }
    val labels = evaluated.flatMap { listOfNotNull(it.expectedCategory, it.baselineCategory) }.toSet().sorted()
    return GoldenEvaluationReport(
      totalCases = cases.size,
      evaluatedCases = evaluated.size,
      unavailableCases = cases.size - evaluated.size,
      current = labels.associateWith { category -> metric(category, evaluated, currentPredictions) },
      baseline = labels.associateWith { category -> metric(category, evaluated, baselinePredictions) },
    )
  }

  fun assertNotWorseThanBaseline(report: GoldenEvaluationReport) {
    require(report.totalCases >= 100) { "Golden dataset must contain at least 100 cases" }
    report.current.forEach { (category, current) ->
      val baseline = report.baseline.getValue(category)
      require(current.precision + 1e-9 >= baseline.precision) {
        "$category precision regressed: ${current.precision} < ${baseline.precision}"
      }
      require(current.recall + 1e-9 >= baseline.recall) {
        "$category recall regressed: ${current.recall} < ${baseline.recall}"
      }
    }
  }

  private fun prediction(case: GoldenCase, classifier: ContentRiskClassifier): String? {
    val normalized = ContentTextNormalizer.normalize(case.title, case.text)
    return classifier.classify(normalized, case.source)?.category?.name
  }

  private fun metric(
    category: String,
    cases: List<GoldenCase>,
    predictions: Map<GoldenCase, String?>,
  ): CategoryMetric {
    val truePositives = cases.count { it.expectedCategory == category && predictions[it] == category }
    val falsePositives = cases.count { it.expectedCategory != category && predictions[it] == category }
    val falseNegatives = cases.count { it.expectedCategory == category && predictions[it] != category }
    val precision = if (truePositives + falsePositives == 0) 1.0 else {
      truePositives.toDouble() / (truePositives + falsePositives)
    }
    val recall = if (truePositives + falseNegatives == 0) 1.0 else {
      truePositives.toDouble() / (truePositives + falseNegatives)
    }
    return CategoryMetric(category, precision, recall, falsePositives, falseNegatives, truePositives)
  }

  private fun loadCases(): List<GoldenCase> {
    val stream = requireNotNull(ContentRiskGoldenEvaluator::class.java.classLoader?.getResourceAsStream(RESOURCE)) {
      "Missing $RESOURCE"
    }
    val json = stream.bufferedReader().use { it.readText() }
    val values = JSONObject(json).getJSONArray("cases")
    return (0 until values.length()).map { index -> parse(values.getJSONObject(index)) }
  }

  private fun parse(value: JSONObject): GoldenCase = GoldenCase(
    id = value.getString("id"),
    source = SignalSource.valueOf(value.getString("source")),
    appRef = value.getString("app_ref"),
    title = nullableString(value, "title"),
    text = nullableString(value, "text"),
    expectedCategory = nullableString(value, "expected_category"),
    baselineCategory = nullableString(value, "baseline_category"),
    capability = ContentCapabilityLevel.valueOf(value.getString("capability")),
    availability = value.getString("availability"),
  )

  private fun nullableString(value: JSONObject, key: String): String? =
    if (value.isNull(key)) null else value.getString(key)
}

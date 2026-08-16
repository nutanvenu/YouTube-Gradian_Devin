package com.guardian.fixture.contentsafety

import android.app.Activity
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Synthetic cases only. This source is intentionally outside the shipping Android project. */
data class FixtureCase(
  val id: String,
  val title: String?,
  val body: String?,
  val capability: String,
  val publicContentId: String? = null,
  val canvasOnly: Boolean = false,
)

object FixtureCatalog {
  val cases = listOf(
    FixtureCase("safe-001", "A guide to building a treehouse", "Weekend plans for a family project", "BEST_EFFORT", "fixture:safe-001"),
    FixtureCase("medium-001", "Fire challenge compilation", "Synthetic fixture title", "BEST_EFFORT", "fixture:medium-001"),
    FixtureCase("high-001", "How to build a bomb", "Synthetic safety fixture", "BEST_EFFORT", "fixture:high-001"),
    FixtureCase("negated-001", "Do not hurt yourself", "Find a trusted adult for help", "BEST_EFFORT", "fixture:negated-001"),
    FixtureCase("educational-001", "News lesson: suicide prevention", "A public health resource", "BEST_EFFORT", "fixture:educational-001"),
    FixtureCase("unicode-001", "Ｓｅｌｆ\u200b－ｈａｒｍ plan tonight", "Synthetic Unicode fixture", "BEST_EFFORT", "fixture:unicode-001"),
    FixtureCase("inaccessible-canvas-001", null, null, "UNAVAILABLE", "fixture:inaccessible-canvas-001", canvasOnly = true),
  )
}

/** A view that draws text but exposes no text/content description to accessibility. */
private class CanvasOnlyContentView(context: android.content.Context, private val label: String) : View(context) {
  private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
    color = Color.DKGRAY
    textSize = 42f
  }

  override fun onDraw(canvas: Canvas) {
    super.onDraw(canvas)
    canvas.drawText(label, 24f, 80f, paint)
  }
}

class FixtureActivity : Activity() {
  private var index = 0
  private lateinit var content: LinearLayout
  private lateinit var status: TextView

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    render()
  }

  override fun onResume() {
    super.onResume()
    if (::status.isInitialized) status.text = "Lifecycle: foreground"
  }

  override fun onPause() {
    if (::status.isInitialized) status.text = "Lifecycle: background"
    super.onPause()
  }

  private fun render() {
    val root = LinearLayout(this).apply {
      orientation = LinearLayout.VERTICAL
      setPadding(24, 24, 24, 24)
    }
    status = TextView(this).apply { text = "Lifecycle: foreground" }
    root.addView(status)
    root.addView(TextView(this).apply { text = "Synthetic content-safety fixture" })

    val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
    controls.addView(button("Previous") { index = (index - 1 + FixtureCatalog.cases.size) % FixtureCatalog.cases.size; renderCase() })
    controls.addView(button("Next content") { index = (index + 1) % FixtureCatalog.cases.size; renderCase() })
    controls.addView(button("Background") { moveTaskToBack(true) })
    controls.addView(button("Foreground") { startActivity(Intent(this, FixtureActivity::class.java)) })
    root.addView(controls)

    val signals = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
    signals.addView(button("Notification") { emitNotification() })
    signals.addView(button("Media metadata") { emitMediaMetadata() })
    signals.addView(button("Allowed domain") { openDomain("https://fixture.safe.test") })
    signals.addView(button("Blocked domain") { openDomain("https://fixture.blocked.test") })
    root.addView(signals)

    content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
    root.addView(ScrollView(this).apply { addView(content) }, LinearLayout.LayoutParams(-1, 0, 1f))
    setContentView(root)
    renderCase()
  }

  private fun renderCase() {
    content.removeAllViews()
    val fixture = FixtureCatalog.cases[index]
    content.addView(TextView(this).apply { text = "Case: ${fixture.id}\nCapability: ${fixture.capability}" })
    if (fixture.canvasOnly) {
      content.addView(CanvasOnlyContentView(this, "Canvas-only risky title"), LinearLayout.LayoutParams(-1, 180))
      content.addView(TextView(this).apply { text = "No accessible title/body is exposed for this case." })
    } else {
      content.addView(TextView(this).apply { text = "Title: ${fixture.title}\nBody: ${fixture.body}" })
    }
    content.addView(TextView(this).apply { text = "Public fixture reference: ${fixture.publicContentId}" })
  }

  private fun emitNotification() {
    val fixture = FixtureCatalog.cases[index]
    sendBroadcast(Intent("com.guardian.fixture.NOTIFICATION_METADATA").apply {
      putExtra("fixture_id", fixture.id)
      putExtra("package_ref", packageName)
      putExtra("title", fixture.title)
      putExtra("text", fixture.body)
      putExtra("content_capability", fixture.capability)
    })
  }

  private fun emitMediaMetadata() {
    val fixture = FixtureCatalog.cases[index]
    sendBroadcast(Intent("com.guardian.fixture.MEDIA_METADATA").apply {
      putExtra("fixture_id", fixture.id)
      putExtra("package_ref", packageName)
      putExtra("media_title", fixture.title)
      putExtra("media_description", fixture.body)
      putExtra("content_capability", fixture.capability)
    })
  }

  private fun openDomain(base: String) {
    val fixture = FixtureCatalog.cases[index]
    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("$base/?fixture_id=${fixture.id}")))
  }

  private fun button(label: String, action: () -> Unit) = Button(this).apply {
    text = label
    setOnClickListener { action() }
    minHeight = 48
    minWidth = 48
  }
}

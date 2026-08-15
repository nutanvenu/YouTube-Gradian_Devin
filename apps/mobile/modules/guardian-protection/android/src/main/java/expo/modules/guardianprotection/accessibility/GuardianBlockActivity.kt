package expo.modules.guardianprotection.accessibility

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class GuardianBlockActivity : Activity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val content = LinearLayout(this).apply {
      orientation = LinearLayout.VERTICAL
      gravity = Gravity.CENTER
      setPadding(48, 48, 48, 48)
      setBackgroundColor(Color.WHITE)
    }
    content.addView(TextView(this).apply {
      text = "This app is unavailable right now."
      textSize = 24f
      setTextColor(Color.BLACK)
      gravity = Gravity.CENTER
    })
    content.addView(TextView(this).apply {
      text = "Your time limit or routine applies. Ask a parent to change the limit or routine if you need more time."
      textSize = 16f
      setTextColor(Color.DKGRAY)
      gravity = Gravity.CENTER
      setPadding(0, 24, 0, 24)
    })
    content.addView(Button(this).apply {
      text = "Return"
      setOnClickListener { finish() }
    })
    setContentView(content)
  }

  companion object {
    const val EXTRA_APP = "blocked_app"
    const val EXTRA_REASON = "blocked_reason"
  }
}

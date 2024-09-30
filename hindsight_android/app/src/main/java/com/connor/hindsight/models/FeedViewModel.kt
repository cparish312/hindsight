package com.connor.hindsight.models

import androidx.lifecycle.ViewModel
import com.connor.hindsight.utils.Preferences


class FeedViewModel : ViewModel() {
    private var primaryUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString().replace(Regex(":[0-9]+"), ":5000").replace("https:", "http:")
    private var fallbackUrl: String = Preferences.prefs.getString(
        Preferences.interneturl,
        ""
    ).toString().replace(Regex(":[0-9]+"), ":5000").replace("https:", "http:")
}
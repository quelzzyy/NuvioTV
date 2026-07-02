package com.nuvio.tv.ui.screens.player

import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

internal fun PlayerRuntimeController.startSleepTimer(minutes: Int) {
    sleepTimerJob?.cancel()
    val endAtMs = System.currentTimeMillis() + minutes * 60_000L
    _uiState.update { it.copy(sleepTimerEndAtMs = endAtMs, showSleepTimerDialog = false) }
    sleepTimerJob = scope.launch {
        val remaining = endAtMs - System.currentTimeMillis()
        if (remaining > 0) delay(remaining)
        pauseForSleepTimer()
        _uiState.update { it.copy(sleepTimerEndAtMs = null) }
        sleepTimerJob = null
    }
}

internal fun PlayerRuntimeController.cancelSleepTimer() {
    sleepTimerJob?.cancel()
    sleepTimerJob = null
    _uiState.update { it.copy(sleepTimerEndAtMs = null, showSleepTimerDialog = false) }
}

private fun PlayerRuntimeController.pauseForSleepTimer() {
    if (isUsingMpvEngine()) {
        if (!isPlaybackCurrentlyPlaying()) return
        userPausedManually = true
        setPlaybackPaused(true)
        stopProgressUpdates()
        stopWatchProgressSaving()
        emitStopScrobbleForCurrentProgress()
        schedulePauseOverlay()
    } else {
        _exoPlayer?.let { player ->
            if (!player.isPlaying) return
            userPausedManually = true
            pauseStartTimeMs = System.currentTimeMillis()
            player.pause()
            schedulePauseOverlay()
        }
    }
}

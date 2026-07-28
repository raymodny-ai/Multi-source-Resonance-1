import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Snapshot {
  timestamp: string
  total_score: number
  gex_score: number
  vix_score: number
  crypto_score: number
  darkpool_score: number
  alert_level: string
}

export const useReplayStore = defineStore('replay', () => {
  // State
  const isReplayMode = ref(false)
  const snapshots = ref<Snapshot[]>([])
  const currentIndex = ref(0)
  const playbackSpeed = ref(1)
  const isPlaying = ref(false)
  const playInterval = ref<ReturnType<typeof setInterval> | null>(null)

  // Getters
  const currentSnapshot = computed(() =>
    snapshots.value[currentIndex.value] ?? null
  )
  const currentTimestamp = computed(() =>
    currentSnapshot.value?.timestamp ?? null
  )
  const snapshotCount = computed(() => snapshots.value.length)
  const progress = computed(() => {
    if (snapshots.value.length <= 1) return 0
    return (currentIndex.value / (snapshots.value.length - 1)) * 100
  })

  // Actions
  function setSnapshots(data: Snapshot[]) {
    snapshots.value = data
    currentIndex.value = 0
  }

  function seek(index: number) {
    currentIndex.value = Math.max(0, Math.min(index, snapshots.value.length - 1))
  }

  function seekToTimestamp(timestamp: string) {
    const idx = snapshots.value.findIndex((s) => s.timestamp === timestamp)
    if (idx >= 0) currentIndex.value = idx
  }

  function play() {
    if (snapshots.value.length === 0) return
    isPlaying.value = true
    isReplayMode.value = true
    const intervalMs = 2000 / playbackSpeed.value
    playInterval.value = setInterval(() => {
      if (currentIndex.value >= snapshots.value.length - 1) {
        pause()
        return
      }
      currentIndex.value++
    }, intervalMs)
  }

  function pause() {
    isPlaying.value = false
    if (playInterval.value) {
      clearInterval(playInterval.value)
      playInterval.value = null
    }
  }

  function setSpeed(speed: number) {
    playbackSpeed.value = speed
    if (isPlaying.value) {
      pause()
      play()
    }
  }

  function exitReplay() {
    pause()
    isReplayMode.value = false
    currentIndex.value = 0
  }

  return {
    isReplayMode, snapshots, currentIndex, playbackSpeed, isPlaying,
    currentSnapshot, currentTimestamp, snapshotCount, progress,
    setSnapshots, seek, seekToTimestamp, play, pause, setSpeed, exitReplay,
  }
})

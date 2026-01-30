'use client'

import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Camera as CameraIcon, RefreshCcw } from 'lucide-react'

interface CameraItem {
  id: number
  name: string
  source_url: string
  zone_name?: string | null
}

interface VideoItem {
  name: string
}

export default function StreamingPage() {
  const [cameras, setCameras] = useState<CameraItem[]>([])
  const [activeCameraId, setActiveCameraId] = useState<number | null>(null)
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [selectedVideo, setSelectedVideo] = useState<string>('video.mp4')
  const [videoSrc, setVideoSrc] = useState<string>('/video_feed')

  const activeCamera = useMemo(
    () => (activeCameraId ? cameras.find((c) => c.id === activeCameraId) : null),
    [activeCameraId, cameras]
  )

  const refresh = async () => {
    try {
      const [camRes, vidRes] = await Promise.all([
        fetch('http://localhost:8000/api/cameras'),
        fetch('http://localhost:8000/api/videos')
      ])
      const camData = await camRes.json()
      const vidData = await vidRes.json()
      const list: CameraItem[] = Array.isArray(camData.cameras) ? camData.cameras : []
      setCameras(list)
      const vids: VideoItem[] = Array.isArray(vidData.videos) ? vidData.videos.map((n: string) => ({ name: n })) : []
      setVideos(vids)
      let active = typeof camData.active_camera_id === 'number' ? camData.active_camera_id : null
      // If no active camera and list not empty, select the first
      if (active == null && list.length > 0) {
        active = list[0].id
        await fetch(`http://localhost:8000/api/cameras/${active}/select`, { method: 'POST' })
      }
      setActiveCameraId(active)
    } catch {
      setCameras([])
      setVideos([])
      setActiveCameraId(null)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const handleSelectCamera = async (cameraId: number) => {
    await fetch(`http://localhost:8000/api/cameras/${cameraId}/select`, { method: 'POST' })
    setActiveCameraId(cameraId)
    setVideoSrc(`/video_feed?ts=${Date.now()}`)
  }

  const handleSelectVideo = async (videoName: string) => {
    await fetch('http://localhost:8000/api/videos/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: videoName })
    })
    setSelectedVideo(videoName)
    setVideoSrc(`/video_feed?ts=${Date.now()}`)
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Video streaming</h1>
          <p className="text-sm text-muted-foreground">Flux MJPEG du backend</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
            <CameraIcon className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Caméra</span>
            <select
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={activeCameraId ?? ''}
              onChange={(e) => handleSelectCamera(Number(e.target.value))}
            >
              <option value="" disabled>
                Sélectionner…
              </option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.zone_name ? ` — ${c.zone_name}` : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
            <CameraIcon className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Vidéo</span>
            <select
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={selectedVideo}
              onChange={(e) => handleSelectVideo(e.target.value)}
            >
              {videos.map((v) => (
                <option key={v.name} value={v.name}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
          <Button onClick={refresh} variant="outline">
            <RefreshCcw className="mr-2 h-4 w-4" />
            Rafraîchir
          </Button>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>
            Flux vidéo{activeCamera?.zone_name ? ` — ${activeCamera.zone_name}` : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative overflow-hidden rounded-lg border bg-background">
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent" />
            <img
              src={videoSrc}
              alt="Video stream"
              className="relative w-full"
              style={{ maxHeight: '70vh', objectFit: 'contain' }}
            />
          </div>
          {activeCamera && (
            <div className="mt-3 text-xs text-muted-foreground break-all">
              Source: {activeCamera.source_url}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

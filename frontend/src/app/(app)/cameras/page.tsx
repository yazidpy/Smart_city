'use client'

import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Camera, Plus, Trash2, RefreshCcw } from 'lucide-react'

interface CameraItem {
  id: number
  name: string
  source_url: string
  zone_name?: string | null
  created_at?: string
}

export default function CamerasPage() {
  const [cameras, setCameras] = useState<CameraItem[]>([])
  const [activeCameraId, setActiveCameraId] = useState<number | null>(null)

  const [newCameraName, setNewCameraName] = useState('')
  const [newCameraUrl, setNewCameraUrl] = useState('')
  const [newZoneName, setNewZoneName] = useState('')

  const [loading, setLoading] = useState(false)

  const activeCamera = useMemo(
    () => (activeCameraId ? cameras.find((c) => c.id === activeCameraId) : null),
    [activeCameraId, cameras]
  )

  const refresh = async () => {
    setLoading(true)
    try {
      const r = await fetch('http://localhost:8000/api/cameras')
      const data = await r.json()
      const list: CameraItem[] = Array.isArray(data.cameras) ? data.cameras : []
      setCameras(list)
      const active = typeof data.active_camera_id === 'number' ? data.active_camera_id : null
      setActiveCameraId(active)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const createCamera = async () => {
    if (!newCameraName || !newCameraUrl) return
    await fetch('http://localhost:8000/api/cameras', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newCameraName,
        source_url: newCameraUrl,
        zone_name: newZoneName || null,
      }),
    })
    setNewCameraName('')
    setNewCameraUrl('')
    setNewZoneName('')
    await refresh()
  }

  const deleteCamera = async (cameraId: number) => {
    await fetch(`http://localhost:8000/api/cameras/${cameraId}`, { method: 'DELETE' })
    await refresh()
  }

  const selectCamera = async (cameraId: number) => {
    await fetch(`http://localhost:8000/api/cameras/${cameraId}/select`, { method: 'POST' })
    await refresh()
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Gestion des caméras</h1>
          <p className="text-sm text-muted-foreground">Ajouter, sélectionner, supprimer des sources (RTSP/HTTP/fichiers)</p>
        </div>
        <Button onClick={refresh} variant="outline" disabled={loading}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Rafraîchir
        </Button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Caméras enregistrées</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {cameras.length === 0 ? (
              <div className="text-sm text-muted-foreground">Aucune caméra. Ajoute-en une à droite.</div>
            ) : (
              <div className="divide-y rounded-md border bg-background">
                {cameras.map((c) => (
                  <div key={c.id} className="flex flex-col gap-2 p-3 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Camera className="h-4 w-4 text-muted-foreground" />
                        <div className="font-medium text-foreground truncate">
                          {c.name}
                          {c.zone_name ? ` — ${c.zone_name}` : ''}
                          {activeCameraId === c.id ? ' (active)' : ''}
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground break-all">{c.source_url}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant={activeCameraId === c.id ? 'default' : 'outline'}
                        onClick={() => selectCamera(c.id)}
                      >
                        Sélectionner
                      </Button>
                      <Button variant="outline" onClick={() => deleteCamera(c.id)}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        Supprimer
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ajouter une caméra</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              className="h-10 w-full rounded-md border bg-background px-3 text-sm"
              placeholder="Nom caméra"
              value={newCameraName}
              onChange={(e) => setNewCameraName(e.target.value)}
            />
            <input
              className="h-10 w-full rounded-md border bg-background px-3 text-sm"
              placeholder="URL/IP (rtsp://... ou http://... ou chemin fichier)"
              value={newCameraUrl}
              onChange={(e) => setNewCameraUrl(e.target.value)}
            />
            <input
              className="h-10 w-full rounded-md border bg-background px-3 text-sm"
              placeholder="Nom zone (optionnel)"
              value={newZoneName}
              onChange={(e) => setNewZoneName(e.target.value)}
            />
            <Button onClick={createCamera} className="w-full">
              <Plus className="mr-2 h-4 w-4" />
              Ajouter
            </Button>

            {activeCamera && (
              <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                <div className="font-medium text-foreground">Caméra active</div>
                <div className="mt-1">{activeCamera.name}{activeCamera.zone_name ? ` — ${activeCamera.zone_name}` : ''}</div>
                <div className="mt-1 break-all">{activeCamera.source_url}</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

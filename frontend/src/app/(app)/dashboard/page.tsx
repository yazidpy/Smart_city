'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { TrendingUp, Activity, Camera as CameraIcon } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { motion } from 'framer-motion'

interface Metrics {
  timestamp: string
  frame: number
  counts: Record<string, number>
  traffic_state: 'fluid' | 'moderate' | 'saturated'
  fps: number
}

interface HistoryPoint {
  time: string
  Car: number
  Person: number
  Bicycle: number
  Motorcycle: number
  Bus: number
  Truck: number
}

interface Camera {
  id: number
  name: string
  source_url: string
  zone_name?: string | null
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [trafficStateColor, setTrafficStateColor] = useState('text-green-600')
  const [videoSrc, setVideoSrc] = useState<string>('/video_feed')

  const [cameras, setCameras] = useState<Camera[]>([])
  const [activeCameraId, setActiveCameraId] = useState<number | null>(null)

  useEffect(() => {
    refreshCameras()

    const socket = new WebSocket('ws://localhost:8000/ws')
    socket.onmessage = (event) => {
      const data: Metrics = JSON.parse(event.data)
      setMetrics(data)
      setHistory((prev) => {
        const newPoint: HistoryPoint = {
          time: new Date(data.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
          Car: data.counts.Car || 0,
          Person: data.counts.Person || 0,
          Bicycle: data.counts.Bicycle || 0,
          Motorcycle: data.counts.Motorcycle || 0,
          Bus: data.counts.Bus || 0,
          Truck: data.counts.Truck || 0,
        }
        const updated = [...prev, newPoint]
        return updated.slice(-60)
      })

      if (data.traffic_state === 'saturated') setTrafficStateColor('text-red-600')
      else if (data.traffic_state === 'moderate') setTrafficStateColor('text-yellow-600')
      else setTrafficStateColor('text-green-600')
    }

    return () => socket.close()
  }, [])

  const refreshCameras = async () => {
    try {
      const r = await fetch('http://localhost:8000/api/cameras')
      const data = await r.json()
      const list: Camera[] = Array.isArray(data.cameras) ? data.cameras : []
      setCameras(list)
      const active = typeof data.active_camera_id === 'number' ? data.active_camera_id : null
      setActiveCameraId(active)
    } catch {
      setCameras([])
      setActiveCameraId(null)
    }
  }

  const handleSelectCamera = async (cameraId: number) => {
    await fetch(`http://localhost:8000/api/cameras/${cameraId}/select`, { method: 'POST' })
    setActiveCameraId(cameraId)
    setVideoSrc(`/video_feed?ts=${Date.now()}`)
  }

  const getTrafficStateIcon = () => {
    if (!metrics) return <Activity className="w-6 h-6" />
    if (metrics.traffic_state === 'moderate') return <TrendingUp className="w-6 h-6" />
    return <Activity className="w-6 h-6" />
  }

  const totalVehicles = (metrics?.counts.Car || 0)
    + (metrics?.counts.Bus || 0)
    + (metrics?.counts.Truck || 0)
    + (metrics?.counts.Motorcycle || 0)

  const activeCamera = activeCameraId ? cameras.find((c) => c.id === activeCameraId) : null
  const activeZoneLabel = activeCamera?.zone_name ? String(activeCamera.zone_name) : null

  return (
    <div className="space-y-6">
        <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Dashboard</h1>
            <p className="text-sm text-muted-foreground">KPIs + tendances en temps réel</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
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
              {activeZoneLabel && (
                <span className="ml-2 rounded-full border bg-background px-2 py-1 text-xs text-muted-foreground">
                  Zone: {activeZoneLabel}
                </span>
              )}
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Voitures</CardTitle>
                <div className="h-4 w-4 bg-blue-500 rounded" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.counts.Car || 0}</div>
                <p className="text-xs text-muted-foreground">Détection en cours</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.05 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Piétons</CardTitle>
                <div className="h-4 w-4 bg-green-500 rounded" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.counts.Person || 0}</div>
                <p className="text-xs text-muted-foreground">Détection en cours</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.1 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">État du trafic</CardTitle>
                <div className={trafficStateColor}>{getTrafficStateIcon()}</div>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold capitalize ${trafficStateColor}`}>
                  {metrics?.traffic_state || 'Chargement...'}
                </div>
                <p className="text-xs text-muted-foreground">Analyse en temps réel</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.15 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Véhicules (total)</CardTitle>
                <div className="h-4 w-4 bg-slate-900 dark:bg-slate-100 rounded" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totalVehicles}</div>
                <p className="text-xs text-muted-foreground">Car + Bus + Truck + Moto</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            <Card>
              <CardHeader>
                <CardTitle>Flux vidéo{activeZoneLabel ? ` — ${activeZoneLabel}` : ''}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative overflow-hidden rounded-lg border bg-background">
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent" />
                  <img
                    src={videoSrc}
                    alt="Video stream"
                    className="relative w-full"
                    style={{ maxHeight: '420px', objectFit: 'contain' }}
                  />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.05 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Flux (60 dernières secondes)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={history}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="Car" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Person" stroke="#10b981" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Bicycle" stroke="#f59e0b" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Motorcycle" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </div>
    </div>
  )
}

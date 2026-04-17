'use client'

import { useEffect, useRef } from 'react'
import type { Skill } from '@/lib/types'

interface SkillGraphProps {
  skills: Skill[]
}

export function SkillGraph({ skills }: SkillGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    const centerX = width / 2
    const centerY = height / 2
    const maxRadius = Math.min(width, height) / 2 - 40

    ctx.clearRect(0, 0, width, height)

    const levels = 5
    for (let i = levels; i >= 1; i--) {
      const radius = (maxRadius / levels) * i
      ctx.beginPath()
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
      ctx.strokeStyle = `rgba(0, 240, 255, ${0.1 + i * 0.02})`
      ctx.lineWidth = 1
      ctx.stroke()
    }

    const angleStep = (Math.PI * 2) / skills.length

    ctx.beginPath()
    skills.forEach((skill, i) => {
      const angle = angleStep * i - Math.PI / 2
      const radius = (maxRadius / levels) * skill.level
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius

      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.closePath()
    ctx.fillStyle = 'rgba(0, 240, 255, 0.1)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)'
    ctx.lineWidth = 2
    ctx.stroke()

    skills.forEach((skill, i) => {
      const angle = angleStep * i - Math.PI / 2
      const radius = (maxRadius / levels) * skill.level
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, 12)
      gradient.addColorStop(0, skill.verified ? 'rgba(0, 240, 255, 0.8)' : 'rgba(100, 116, 139, 0.8)')
      gradient.addColorStop(1, 'rgba(0, 240, 255, 0)')

      ctx.beginPath()
      ctx.arc(x, y, 12, 0, Math.PI * 2)
      ctx.fillStyle = gradient
      ctx.fill()

      ctx.beginPath()
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fillStyle = skill.verified ? '#00F0FF' : '#64748B'
      ctx.fill()

      if (skill.verified) {
        ctx.beginPath()
        ctx.arc(x, y, 8, 0, Math.PI * 2)
        ctx.strokeStyle = '#00F0FF'
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      const labelRadius = maxRadius + 25
      const labelX = centerX + Math.cos(angle) * labelRadius
      const labelY = centerY + Math.sin(angle) * labelRadius

      ctx.font = '12px Geist, system-ui, sans-serif'
      ctx.fillStyle = '#E2E8F0'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(skill.name, labelX, labelY)
    })

    ctx.beginPath()
    ctx.arc(centerX, centerY, 8, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(0, 240, 255, 0.3)'
    ctx.fill()

    ctx.beginPath()
    ctx.arc(centerX, centerY, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#00F0FF'
    ctx.fill()
  }, [skills])

  return (
    <div className="relative">
      <canvas ref={canvasRef} className="h-[300px] w-full" style={{ width: '100%', height: '300px' }} />
      <div className="absolute bottom-2 right-2 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-primary" />
          Подтвержден
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-muted-foreground" />
          Не подтвержден
        </div>
      </div>
    </div>
  )
}


'use client'
import { useState } from 'react'
import { VALID_TAGS, PatternTag } from '@/lib/geminiPrompt'

interface Props {
  selected: PatternTag[]
  onChange: (tags: PatternTag[]) => void
}

const TAG_COLORS: Record<string, string> = {
  'gap-and-hold':           'emerald',
  'gap-and-fade':           'red',
  'breakout-clean':         'sky',
  'breakout-whipsaw':       'orange',
  'multi-day-runner':       'violet',
  'sector-sympathy':        'yellow',
  'news-fresh':             'teal',
  'news-stale':             'gray',
  'halt-triggered':         'pink',
  'failed-follow-through':  'rose',
}

function colorClass(tag: string, active: boolean) {
  const c = TAG_COLORS[tag] ?? 'gray'
  return active
    ? `bg-${c}-500/20 text-${c}-300 border-${c}-500/50`
    : 'bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-500'
}

export default function TagSelector({ selected, onChange }: Props) {
  const toggle = (tag: PatternTag) => {
    onChange(
      selected.includes(tag) ? selected.filter(t => t !== tag) : [...selected, tag]
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {VALID_TAGS.map(tag => (
        <button
          key={tag}
          type="button"
          onClick={() => toggle(tag)}
          className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${colorClass(tag, selected.includes(tag))}`}
        >
          {tag}
        </button>
      ))}
    </div>
  )
}

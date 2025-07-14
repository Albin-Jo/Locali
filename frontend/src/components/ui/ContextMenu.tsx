// frontend/src/components/ui/ContextMenu.tsx

import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface ContextMenuItem {
  id: string
  label: string
  icon?: React.ReactNode
  shortcut?: string
  disabled?: boolean
  separator?: boolean
  onClick?: () => void
  submenu?: ContextMenuItem[]
}

interface ContextMenuProps {
  items: ContextMenuItem[]
  children: React.ReactNode
  className?: string
}

export function ContextMenu({ items, children, className }: ContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const menuRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX
    const y = e.clientY

    setPosition({ x, y })
    setIsOpen(true)
  }

  const handleClickOutside = (e: MouseEvent) => {
    if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
      setIsOpen(false)
    }
  }

  const handleItemClick = (item: ContextMenuItem) => {
    if (!item.disabled && item.onClick) {
      item.onClick()
    }
    setIsOpen(false)
  }

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
      document.addEventListener('contextmenu', handleClickOutside)

      // Adjust position if menu would go off screen
      if (menuRef.current) {
        const menu = menuRef.current
        const menuRect = menu.getBoundingClientRect()
        const viewport = {
          width: window.innerWidth,
          height: window.innerHeight
        }

        let newX = position.x
        let newY = position.y

        if (newX + menuRect.width > viewport.width) {
          newX = viewport.width - menuRect.width - 8
        }

        if (newY + menuRect.height > viewport.height) {
          newY = viewport.height - menuRect.height - 8
        }

        if (newX !== position.x || newY !== position.y) {
          setPosition({ x: newX, y: newY })
        }
      }

      return () => {
        document.removeEventListener('click', handleClickOutside)
        document.removeEventListener('contextmenu', handleClickOutside)
      }
    }
  }, [isOpen, position])

  return (
    <>
      <div
        ref={containerRef}
        onContextMenu={handleContextMenu}
        className={className}
      >
        {children}
      </div>

      {isOpen && createPortal(
        <div
          ref={menuRef}
          className="fixed z-50 min-w-[200px] bg-popover border border-border rounded-lg shadow-lg py-1"
          style={{
            left: position.x,
            top: position.y,
          }}
        >
          {items.map((item, index) => {
            if (item.separator) {
              return <div key={index} className="h-px bg-border my-1" />
            }

            return (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                disabled={item.disabled}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2 text-sm text-left transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  'focus:bg-accent focus:text-accent-foreground focus:outline-none'
                )}
              >
                {item.icon && (
                  <span className="text-muted-foreground">{item.icon}</span>
                )}
                <span className="flex-1">{item.label}</span>
                {item.shortcut && (
                  <span className="text-xs text-muted-foreground">
                    {item.shortcut}
                  </span>
                )}
              </button>
            )
          })}
        </div>,
        document.body
      )}
    </>
  )
}
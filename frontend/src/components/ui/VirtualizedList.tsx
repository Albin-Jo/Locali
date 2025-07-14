// frontend/src/components/ui/VirtualizedList.tsx

import React, { useMemo } from 'react'
import { FixedSizeList as List } from 'react-window'

interface VirtualizedListProps<T> {
  items: T[]
  itemHeight: number
  height: number
  renderItem: (props: { index: number; style: React.CSSProperties; data: T[] }) => React.ReactElement
  className?: string
}

export function VirtualizedList<T>({
  items,
  itemHeight,
  height,
  renderItem,
  className
}: VirtualizedListProps<T>) {
  const Row = useMemo(() => {
    return ({ index, style }: { index: number; style: React.CSSProperties }) =>
      renderItem({ index, style, data: items })
  }, [items, renderItem])

  return (
    <div className={className}>
      <List
        height={height}
        itemCount={items.length}
        itemSize={itemHeight}
        itemData={items}
        overscanCount={5}
      >
        {Row}
      </List>
    </div>
  )
}


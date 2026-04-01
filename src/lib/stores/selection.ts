export interface SelectionState {
  selectedIds: Set<number>;
  anchorId: number | null;
}

interface SelectionInput {
  current: SelectionState;
  clickedId: number;
  visibleIds: number[];
  shiftKey: boolean;
  toggleKey: boolean;
}

function buildRange(visibleIds: number[], fromId: number, toId: number) {
  const startIndex = visibleIds.indexOf(fromId);
  const endIndex = visibleIds.indexOf(toId);

  if (startIndex === -1 || endIndex === -1) {
    return [toId];
  }

  const [start, end] = startIndex < endIndex ? [startIndex, endIndex] : [endIndex, startIndex];
  return visibleIds.slice(start, end + 1);
}

export function applySelection(input: SelectionInput): SelectionState {
  const { current, clickedId, visibleIds, shiftKey, toggleKey } = input;

  if (shiftKey && current.anchorId !== null) {
    const rangeIds = buildRange(visibleIds, current.anchorId, clickedId);
    const nextSelected = toggleKey ? new Set(current.selectedIds) : new Set<number>();

    for (const id of rangeIds) {
      nextSelected.add(id);
    }

    return {
      selectedIds: nextSelected,
      anchorId: current.anchorId
    };
  }

  if (toggleKey) {
    const nextSelected = new Set(current.selectedIds);

    if (nextSelected.has(clickedId)) {
      nextSelected.delete(clickedId);
    } else {
      nextSelected.add(clickedId);
    }

    return {
      selectedIds: nextSelected,
      anchorId: clickedId
    };
  }

  return {
    selectedIds: new Set([clickedId]),
    anchorId: clickedId
  };
}

export function selectAllVisible(visibleIds: number[]): SelectionState {
  return {
    selectedIds: new Set(visibleIds),
    anchorId: visibleIds[0] ?? null
  };
}

export function clearSelection(): SelectionState {
  return {
    selectedIds: new Set<number>(),
    anchorId: null
  };
}

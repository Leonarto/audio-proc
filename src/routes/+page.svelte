<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Check,
    FolderSearch,
    LoaderCircle,
    RefreshCw,
    Search,
    Sparkles,
    SquareCheckBig,
    X
  } from 'lucide-svelte';
  import type { AudioFileItem, JobResponse, SearchResultItem } from '$api/types';
  import {
    getAudioStreamUrl,
    getJob,
    getSettings,
    listAudioFiles,
    processAudio,
    searchTranscripts,
    startScan,
    updateSettings
  } from '$api/client';
  import { chooseFolder, isDesktopBridgeAvailable, showItemInFolder } from '$desktop/bridge';
  import { applySelection, clearSelection, selectAllVisible } from '$stores/selection';
  import { formatDateTime, formatDuration, formatStatus } from '$utils/format';
  import AudioPlayer from '$lib/components/AudioPlayer.svelte';
  import Badge from '$ui/Badge.svelte';
  import Button from '$ui/Button.svelte';
  import Card from '$ui/Card.svelte';
  import Input from '$ui/Input.svelte';
  import Progress from '$ui/Progress.svelte';

  type FilterKey = 'all' | 'processed' | 'unprocessed';
  type SortKey = 'filename' | 'modified' | 'duration' | 'processed';
  type BadgeVariant = 'neutral' | 'success' | 'warning' | 'danger' | 'accent';

  let items: AudioFileItem[] = [];
  let currentFolderPath: string | null = null;
  let selectedIds = new Set<number>();
  let anchorId: number | null = null;
  let activeAudioId: number | null = null;
  let loading = false;
  let searchLoading = false;
  let errorMessage = '';
  let searchQuery = '';
  let searchResults: SearchResultItem[] = [];
  let filterKey: FilterKey = 'all';
  let sortKey: SortKey = 'modified';
  let sortDirection: 'asc' | 'desc' = 'desc';
  let activeJob: JobResponse | null = null;
  let providerName = 'mock';

  const filterOptions: Array<{ key: FilterKey; label: string }> = [
    { key: 'all', label: 'All' },
    { key: 'processed', label: 'Processed' },
    { key: 'unprocessed', label: 'Unprocessed' }
  ];
  const sortOptions: Array<{ key: SortKey; label: string }> = [
    { key: 'modified', label: 'Modified' },
    { key: 'filename', label: 'Filename' },
    { key: 'duration', label: 'Duration' },
    { key: 'processed', label: 'Processed' }
  ];

  function jobProgress(job: JobResponse | null) {
    if (!job || job.total === 0) {
      return 0;
    }

    return (job.completed / job.total) * 100;
  }

  function statusVariant(status: AudioFileItem['transcript_status']): BadgeVariant {
    switch (status) {
      case 'processed':
        return 'success';
      case 'processing':
        return 'accent';
      case 'failed':
        return 'danger';
      default:
        return 'neutral';
    }
  }

  function processedVariant(processed: boolean): BadgeVariant {
    return processed ? 'success' : 'neutral';
  }

  function jobVariant(status: JobResponse['status']): BadgeVariant {
    if (status === 'completed') {
      return 'success';
    }

    if (status === 'failed') {
      return 'danger';
    }

    return 'accent';
  }

  function sortItems(list: AudioFileItem[]) {
    return [...list].sort((left, right) => {
      const direction = sortDirection === 'asc' ? 1 : -1;

      switch (sortKey) {
        case 'filename':
          return left.filename.localeCompare(right.filename) * direction;
        case 'duration':
          return ((left.duration_seconds ?? -1) - (right.duration_seconds ?? -1)) * direction;
        case 'processed':
          return (Number(left.processed) - Number(right.processed)) * direction;
        default:
          return (
            (new Date(left.modified_at_fs).getTime() - new Date(right.modified_at_fs).getTime()) * direction
          );
      }
    });
  }

  function filterItems(list: AudioFileItem[]) {
    return list.filter((item) => {
      if (filterKey === 'processed') {
        return item.processed;
      }

      if (filterKey === 'unprocessed') {
        return !item.processed;
      }

      return true;
    });
  }

  $: visibleItems = sortItems(filterItems(items));
  $: visibleIds = visibleItems.map((item) => item.id);
  $: activeAudio =
    items.find((item) => item.id === activeAudioId) ??
    visibleItems[0] ??
    null;
  $: activeAudioSrc = activeAudio ? getAudioStreamUrl(activeAudio.id) : '';
  $: totalCount = items.length;
  $: processedCount = items.filter((item) => item.processed).length;
  $: unprocessedCount = items.filter((item) => !item.processed).length;
  $: selectedCount = selectedIds.size;
  $: desktopModifierLabel = isDesktopBridgeAvailable() ? 'Cmd on macOS / Ctrl on Windows' : 'Ctrl';
  $: if (activeAudioId !== null && !items.some((item) => item.id === activeAudioId)) {
    activeAudioId = visibleItems[0]?.id ?? null;
  }

  async function refreshFiles() {
    loading = true;
    errorMessage = '';

    try {
      const response = await listAudioFiles();
      items = response.items;
      currentFolderPath = response.current_folder_path;
      const availableIds = new Set(response.items.map((item) => item.id));
      selectedIds = new Set(Array.from(selectedIds).filter((id) => availableIds.has(id)));

      if (anchorId !== null && !availableIds.has(anchorId)) {
        anchorId = null;
      }

      if (!activeAudioId && response.items.length > 0) {
        activeAudioId = response.items[0].id;
      }
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Failed to load audio files.';
    } finally {
      loading = false;
    }
  }

  async function bootstrap() {
    try {
      const settings = await getSettings();
      providerName = settings.transcription_provider;
      currentFolderPath = settings.last_folder_path;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Failed to load app settings.';
    }

    await refreshFiles();
  }

  async function waitForJob(jobId: string) {
    while (true) {
      const next = await getJob(jobId);
      activeJob = next;

      if (next.job_type === 'process') {
        await refreshFiles();
      }

      if (next.status === 'completed' || next.status === 'failed') {
        return next;
      }

      await new Promise((resolve) => setTimeout(resolve, 450));
    }
  }

  async function handleChooseFolder() {
    errorMessage = '';

    try {
      const folderPath = await chooseFolder();

      if (!folderPath) {
        return;
      }

      await updateSettings({ last_folder_path: folderPath });
      const job = await startScan(folderPath);
      activeJob = job;
      await waitForJob(job.id);
      await refreshFiles();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Failed to scan the selected folder.';
    }
  }

  async function handleProcess(reprocess = false) {
    errorMessage = '';

    try {
      const job = await processAudio(Array.from(selectedIds), reprocess);
      activeJob = job;
      await waitForJob(job.id);
      await refreshFiles();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Failed to start processing.';
    }
  }

  function handleRowClick(event: MouseEvent, item: AudioFileItem) {
    const next = applySelection({
      current: { selectedIds, anchorId },
      clickedId: item.id,
      visibleIds,
      shiftKey: event.shiftKey,
      toggleKey: event.metaKey || event.ctrlKey
    });

    selectedIds = next.selectedIds;
    anchorId = next.anchorId;
    activeAudioId = item.id;
  }

  function handleSelectAllVisible() {
    const next = selectAllVisible(visibleIds);
    selectedIds = next.selectedIds;
    anchorId = next.anchorId;
  }

  function handleClearSelection() {
    const next = clearSelection();
    selectedIds = next.selectedIds;
    anchorId = next.anchorId;
  }

  function changeSort(nextSortKey: SortKey) {
    if (sortKey === nextSortKey) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }

    sortKey = nextSortKey;
    sortDirection = nextSortKey === 'filename' ? 'asc' : 'desc';
  }

  function snippetParts(snippetHtml: string) {
    const tokens = snippetHtml.split(/(<mark>|<\/mark>)/g).filter(Boolean);
    const parts: Array<{ text: string; highlight: boolean }> = [];
    let highlight = false;

    for (const token of tokens) {
      if (token === '<mark>') {
        highlight = true;
        continue;
      }

      if (token === '</mark>') {
        highlight = false;
        continue;
      }

      parts.push({ text: token, highlight });
    }

    return parts;
  }

  async function handleSearch() {
    if (!searchQuery.trim()) {
      searchResults = [];
      return;
    }

    searchLoading = true;

    try {
      const response = await searchTranscripts(searchQuery.trim());
      searchResults = response.results;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Search failed.';
      searchResults = [];
    } finally {
      searchLoading = false;
    }
  }

  onMount(() => {
    void bootstrap();
  });
</script>

<svelte:head>
  <title>Audio Proc MVP</title>
</svelte:head>

<div class="panel-grid min-h-screen px-3 py-3 md:px-5 md:py-5">
  <div class="mx-auto max-w-[1680px]">
    <div class="studio-shell grain">
      <div class="relative z-10 border-b border-white/8 px-4 py-4 md:px-6">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-1.5">
                <span class="size-2 rounded-full bg-rose-400/80"></span>
                <span class="size-2 rounded-full bg-amber-300/80"></span>
                <span class="size-2 rounded-full bg-emerald-400/80"></span>
              </div>
              <Badge variant="neutral">Local-first desktop transcription</Badge>
              <Badge variant="accent">{providerName}</Badge>
            </div>

            <div class="max-w-4xl space-y-2">
              <p class="data-label">Audio Proc Control Room</p>
              <h1 class="text-4xl text-white sm:text-5xl">Manage folders, process batches, and search transcripts from one screen.</h1>
              <p class="max-w-3xl text-sm leading-6 text-muted-foreground sm:text-base">
                Built for long local sessions: folder scan on the left, sortable library in the center, and playback plus transcript inspection on the right.
              </p>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2 xl:min-w-[420px]">
            <Button on:click={handleChooseFolder} class="w-full">
              <FolderSearch class="size-4" />
              Choose Folder
            </Button>
            <Button variant="secondary" on:click={() => refreshFiles()} class="w-full">
              <RefreshCw class="size-4" />
              Refresh Library
            </Button>
          </div>
        </div>
      </div>

      <div class="relative z-10 px-4 py-4 md:px-6 md:py-5">
        {#if activeJob}
          <div class="mb-5 rounded-[1.25rem] border border-white/10 bg-white/[0.035] p-4">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between gap-3">
                <div class="flex min-w-0 items-center gap-3">
                  <LoaderCircle class="size-4 shrink-0 animate-spin text-primary" />
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-white">{activeJob.message ?? 'Working locally...'}</p>
                    <p class="truncate text-xs text-muted-foreground">
                      {activeJob.job_type.toUpperCase()} · {activeJob.current_label ?? 'Preparing'} · {activeJob.completed}/{activeJob.total}
                    </p>
                  </div>
                </div>
                <Badge variant={jobVariant(activeJob.status)}>{activeJob.status}</Badge>
              </div>
              <Progress value={jobProgress(activeJob)} />
            </div>
          </div>
        {/if}

        {#if errorMessage}
          <div class="mb-5 rounded-[1.15rem] border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {errorMessage}
          </div>
        {/if}

        <div class="grid gap-5 xl:grid-cols-[290px,minmax(0,1fr),360px]">
          <div class="space-y-5">
            <Card class="space-y-4">
              <div class="space-y-2">
                <p class="data-label">Session</p>
                <h2 class="text-2xl text-white">Workspace</h2>
              </div>

              <div class="rounded-[1.2rem] border border-white/10 bg-black/10 p-4">
                <p class="data-label">Current folder</p>
                <p class="mt-3 break-words text-sm leading-6 text-white/90">
                  {currentFolderPath ?? 'No folder selected yet'}
                </p>
              </div>

              <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div class="rounded-[1.15rem] border border-white/10 bg-white/[0.03] p-4">
                  <p class="data-label">Total files</p>
                  <p class="mt-3 text-3xl font-semibold text-white">{totalCount}</p>
                </div>
                <div class="rounded-[1.15rem] border border-white/10 bg-white/[0.03] p-4">
                  <p class="data-label">Selected</p>
                  <p class="mt-3 text-3xl font-semibold text-white">{selectedCount}</p>
                </div>
                <div class="rounded-[1.15rem] border border-white/10 bg-white/[0.03] p-4">
                  <p class="data-label">Processed</p>
                  <p class="mt-3 text-3xl font-semibold text-white">{processedCount}</p>
                </div>
                <div class="rounded-[1.15rem] border border-white/10 bg-white/[0.03] p-4">
                  <p class="data-label">Pending</p>
                  <p class="mt-3 text-3xl font-semibold text-white">{unprocessedCount}</p>
                </div>
              </div>
            </Card>

            <Card class="space-y-4">
              <div class="space-y-2">
                <p class="data-label">Search</p>
                <h2 class="text-2xl text-white">Transcript hits</h2>
              </div>

              <div class="flex gap-2">
                <Input
                  bind:value={searchQuery}
                  placeholder="Search processed transcripts..."
                  on:keydown={(event) => event.key === 'Enter' && handleSearch()}
                />
                <Button variant="secondary" on:click={handleSearch} disabled={searchLoading}>
                  <Search class="size-4" />
                </Button>
              </div>

              {#if searchLoading}
                <p class="text-sm text-muted-foreground">Searching indexed transcript text...</p>
              {:else if searchQuery.trim() && searchResults.length === 0}
                <div class="rounded-[1.15rem] border border-dashed border-white/10 bg-white/[0.025] p-4 text-sm text-muted-foreground">
                  No matches yet for that keyword query.
                </div>
              {:else if searchResults.length > 0}
                <div class="max-h-[360px] space-y-3 overflow-auto pr-1">
                  {#each searchResults as result}
                    <button
                      class="w-full rounded-[1.1rem] border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-primary/40 hover:bg-white/[0.07]"
                      on:click={() => {
                        activeAudioId = result.audio_file_id;
                        selectedIds = new Set([result.audio_file_id]);
                        anchorId = result.audio_file_id;
                      }}
                    >
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0">
                          <p class="truncate font-semibold text-white">{result.filename}</p>
                          <p class="truncate text-xs uppercase tracking-[0.16em] text-muted-foreground">{result.relative_path}</p>
                        </div>
                        <Badge variant="accent">Hit</Badge>
                      </div>
                      <p class="mt-3 text-sm leading-6 text-muted-foreground">
                        {#each snippetParts(result.snippet_html) as part}
                          {#if part.highlight}
                            <mark class="rounded-sm bg-primary/20 px-1 py-0.5 text-primary">{part.text}</mark>
                          {:else}
                            <span>{part.text}</span>
                          {/if}
                        {/each}
                      </p>
                    </button>
                  {/each}
                </div>
              {:else}
                <div class="rounded-[1.15rem] border border-dashed border-white/10 bg-white/[0.025] p-4 text-sm text-muted-foreground">
                  Search runs across processed transcript text only and jumps the inspector to the matching file.
                </div>
              {/if}
            </Card>

            <Card class="space-y-4">
              <div class="space-y-2">
                <p class="data-label">Selection model</p>
                <h2 class="text-2xl text-white">Desktop behavior</h2>
              </div>
              <div class="space-y-3 text-sm leading-6 text-muted-foreground">
                <p>Single click selects one file.</p>
                <p>{desktopModifierLabel} toggles individual rows.</p>
                <p>Shift-click selects a range over the currently visible filtered list.</p>
                <p>Select Visible respects the current filter and sort order.</p>
              </div>
            </Card>
          </div>

          <Card class="flex min-h-[760px] flex-col gap-4">
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div class="space-y-2">
                  <p class="data-label">Library</p>
                  <h2 class="text-2xl text-white">Audio browser</h2>
                  <p class="max-w-2xl text-sm leading-6 text-muted-foreground">
                    Sortable local inventory with processed-state filtering, visible-range selection, and one-click focus for playback.
                  </p>
                </div>

                <div class="flex flex-wrap gap-2">
                  {#each filterOptions as option}
                    <Button
                      variant={filterKey === option.key ? 'default' : 'secondary'}
                      size="sm"
                      on:click={() => (filterKey = option.key)}
                    >
                      {option.label}
                    </Button>
                  {/each}
                </div>
              </div>

              <div class="flex flex-col gap-3 rounded-[1.2rem] border border-white/10 bg-black/10 p-3">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div class="flex flex-wrap gap-2">
                    {#each sortOptions as option}
                      <Button
                        variant={sortKey === option.key ? 'default' : 'ghost'}
                        size="sm"
                        on:click={() => changeSort(option.key)}
                      >
                        {option.label}
                        {#if sortKey === option.key}
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        {/if}
                      </Button>
                    {/each}
                  </div>

                  <div class="flex flex-wrap gap-2">
                    <Button size="sm" on:click={handleSelectAllVisible} disabled={visibleItems.length === 0}>
                      <SquareCheckBig class="size-4" />
                      Select Visible
                    </Button>
                    <Button variant="secondary" size="sm" on:click={handleClearSelection} disabled={selectedCount === 0}>
                      <X class="size-4" />
                      Clear
                    </Button>
                    <Button on:click={() => handleProcess(false)} disabled={selectedCount === 0}>
                      <Sparkles class="size-4" />
                      Process
                    </Button>
                    <Button variant="secondary" on:click={() => handleProcess(true)} disabled={selectedCount === 0}>
                      <RefreshCw class="size-4" />
                      Reprocess
                    </Button>
                  </div>
                </div>

                <div class="flex flex-wrap gap-2">
                  <Badge variant="neutral">{visibleItems.length} visible</Badge>
                  <Badge variant="success">{processedCount} processed</Badge>
                  <Badge variant="warning">{unprocessedCount} pending</Badge>
                  <Badge variant="accent">{selectedCount} selected</Badge>
                </div>
              </div>
            </div>

            <div class="overflow-hidden rounded-[1.35rem] border border-white/10 bg-white/[0.025]">
              <div class="max-h-[620px] overflow-auto">
                <table class="min-w-full text-left text-sm">
                  <thead class="sticky top-0 z-10 bg-[#141a25]/95 backdrop-blur">
                    <tr class="border-b border-white/8 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      <th class="px-4 py-4">File</th>
                      <th class="px-4 py-4">Path</th>
                      <th class="px-4 py-4">Duration</th>
                      <th class="px-4 py-4">Processed</th>
                      <th class="px-4 py-4">Transcript</th>
                      <th class="px-4 py-4">Modified</th>
                    </tr>
                  </thead>

                  <tbody>
                    {#if loading}
                      <tr>
                        <td colspan="6" class="px-4 py-12 text-center text-muted-foreground">Loading audio files...</td>
                      </tr>
                    {:else if visibleItems.length === 0}
                      <tr>
                        <td colspan="6" class="px-4 py-12 text-center text-muted-foreground">
                          Choose a folder to populate the library, or change the current filter if files are hidden.
                        </td>
                      </tr>
                    {:else}
                      {#each visibleItems as item}
                        <tr
                          class:selected={selectedIds.has(item.id)}
                          class:active={activeAudio?.id === item.id}
                          class="cursor-pointer border-t border-white/[0.06] align-top transition hover:bg-white/[0.04]"
                          on:click={(event) => handleRowClick(event, item)}
                        >
                          <td class="px-4 py-4">
                            <div class="flex items-start gap-3">
                              <div class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.05]">
                                {#if selectedIds.has(item.id)}
                                  <Check class="size-3.5 text-primary" />
                                {/if}
                              </div>
                              <div class="min-w-0">
                                <p class="truncate font-semibold text-white">{item.filename}</p>
                                <p class="mt-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.extension}</p>
                              </div>
                            </div>
                          </td>
                          <td class="max-w-[280px] px-4 py-4 text-muted-foreground">{item.relative_path}</td>
                          <td class="px-4 py-4 text-white/90">{formatDuration(item.duration_seconds)}</td>
                          <td class="px-4 py-4">
                            <Badge variant={processedVariant(item.processed)}>{item.processed ? 'Yes' : 'No'}</Badge>
                          </td>
                          <td class="px-4 py-4">
                            <Badge variant={statusVariant(item.transcript_status)}>{formatStatus(item.transcript_status)}</Badge>
                          </td>
                          <td class="px-4 py-4 text-muted-foreground">{formatDateTime(item.modified_at_fs)}</td>
                        </tr>
                      {/each}
                    {/if}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>

          <div class="space-y-5">
            <Card class="space-y-4">
              <div class="space-y-2">
                <p class="data-label">Playback</p>
                <h2 class="text-2xl text-white">Inspector</h2>
              </div>

              <AudioPlayer
                file={activeAudio}
                src={activeAudioSrc}
                onShowInFolder={async (absolutePath) => {
                  await showItemInFolder(absolutePath);
                }}
              />
            </Card>

            <Card class="space-y-4">
              <div class="space-y-2">
                <p class="data-label">Transcript</p>
                <h2 class="text-2xl text-white">Current file</h2>
              </div>

              {#if activeAudio}
                <div class="space-y-4">
                  <div class="flex flex-wrap gap-2">
                    <Badge variant={processedVariant(activeAudio.processed)}>{activeAudio.processed ? 'Processed' : 'Pending'}</Badge>
                    <Badge variant={statusVariant(activeAudio.transcript_status)}>{formatStatus(activeAudio.transcript_status)}</Badge>
                    <Badge variant="neutral">{providerName}</Badge>
                  </div>

                  <div class="rounded-[1.15rem] border border-white/10 bg-black/10 p-4">
                    <p class="data-label">Relative path</p>
                    <p class="mt-2 break-words text-sm leading-6 text-white/90">{activeAudio.relative_path}</p>
                  </div>

                  <div class="rounded-[1.15rem] border border-white/10 bg-black/10 p-4">
                    <p class="data-label">Transcript text</p>
                    <p class="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">
                      {activeAudio.transcript_text ?? 'No transcript stored yet for this file.'}
                    </p>
                  </div>

                  {#if activeAudio.processing_error}
                    <div class="rounded-[1.1rem] border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                      {activeAudio.processing_error}
                    </div>
                  {/if}
                </div>
              {:else}
                <div class="rounded-[1.15rem] border border-dashed border-white/10 bg-white/[0.025] p-4 text-sm text-muted-foreground">
                  Select an audio row to inspect playback and transcript details here.
                </div>
              {/if}
            </Card>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  tr.selected {
    background: rgba(249, 115, 22, 0.1);
  }

  tr.active {
    box-shadow: inset 3px 0 0 rgba(249, 115, 22, 0.92);
  }
</style>

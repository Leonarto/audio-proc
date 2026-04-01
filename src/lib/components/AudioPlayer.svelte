<script lang="ts">
  import { Pause, Play, FolderOpen } from 'lucide-svelte';
  import Button from '$ui/Button.svelte';
  import { formatDuration, formatFileSize, formatDateTime } from '$utils/format';
  import type { AudioFileItem } from '$api/types';

  export let file: AudioFileItem | null = null;
  export let src = '';
  export let onShowInFolder: ((path: string) => Promise<void> | void) | null = null;

  let audioElement: HTMLAudioElement | null = null;
  let currentTime = 0;
  let playerDuration = 0;
  let isPlaying = false;
  let previousSrc = '';

  $: if (audioElement && src !== previousSrc) {
    previousSrc = src;
    audioElement.pause();
    currentTime = 0;
    playerDuration = file?.duration_seconds ?? 0;
    isPlaying = false;
  }

  function togglePlayback() {
    if (!audioElement || !file) {
      return;
    }

    if (audioElement.paused) {
      void audioElement.play();
      return;
    }

    audioElement.pause();
  }

  function handleLoadedMetadata() {
    playerDuration = audioElement?.duration ?? file?.duration_seconds ?? 0;
  }

  function handleTimeUpdate() {
    currentTime = audioElement?.currentTime ?? 0;
  }

  function handlePlaybackState(isActive: boolean) {
    isPlaying = isActive;
  }

  function seek(event: Event) {
    if (!audioElement) {
      return;
    }

    const target = event.currentTarget as HTMLInputElement;
    audioElement.currentTime = Number(target.value);
    currentTime = audioElement.currentTime;
  }
</script>

<div class="space-y-4">
  {#if !file}
    <div class="rounded-[1.25rem] border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm text-muted-foreground">
      Pick a file from the browser to preview it here.
    </div>
  {:else}
    <audio
      bind:this={audioElement}
      {src}
      preload="metadata"
      on:loadedmetadata={handleLoadedMetadata}
      on:timeupdate={handleTimeUpdate}
      on:play={() => handlePlaybackState(true)}
      on:pause={() => handlePlaybackState(false)}
      on:ended={() => handlePlaybackState(false)}
    ></audio>

    <div class="space-y-4 rounded-[1.25rem] border border-white/10 bg-black/10 p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="data-label">Player</p>
          <h3 class="truncate text-xl text-white">{file.filename}</h3>
          <p class="truncate text-sm text-muted-foreground">{file.relative_path}</p>
        </div>

        {#if onShowInFolder}
          <Button variant="secondary" size="sm" on:click={() => onShowInFolder?.(file.absolute_path)}>
            <FolderOpen class="size-4" />
            Folder
          </Button>
        {/if}
      </div>

      <div class="flex items-center gap-3">
        <Button on:click={togglePlayback} disabled={!src} class="min-w-[110px]">
          {#if isPlaying}
            <Pause class="size-4" />
            Pause
          {:else}
            <Play class="size-4" />
            Play
          {/if}
        </Button>

        <div class="w-full">
          <input
            class="h-2.5 w-full cursor-pointer appearance-none rounded-full bg-white/[0.12]"
            type="range"
            min="0"
            max={playerDuration || file.duration_seconds || 0}
            step="0.1"
            value={currentTime}
            on:input={seek}
          />
          <div class="mt-1 flex items-center justify-between text-xs text-muted-foreground">
            <span>{formatDuration(currentTime)}</span>
            <span>{formatDuration(playerDuration || file.duration_seconds)}</span>
          </div>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
          <p class="data-label">Duration</p>
          <p class="text-sm font-medium text-white">{formatDuration(file.duration_seconds)}</p>
        </div>
        <div class="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
          <p class="data-label">File Size</p>
          <p class="text-sm font-medium text-white">{formatFileSize(file.file_size)}</p>
        </div>
        <div class="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
          <p class="data-label">Modified</p>
          <p class="text-sm font-medium text-white">{formatDateTime(file.modified_at_fs)}</p>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  input[type='range']::-webkit-slider-thumb {
    appearance: none;
    height: 16px;
    width: 16px;
    border-radius: 999px;
    background: hsl(var(--primary));
  }

  input[type='range']::-moz-range-thumb {
    height: 16px;
    width: 16px;
    border: none;
    border-radius: 999px;
    background: hsl(var(--primary));
  }
</style>

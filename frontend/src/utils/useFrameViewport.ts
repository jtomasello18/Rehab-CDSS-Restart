import { useEffect, useState } from 'react';

/** Keep a fixed drawer within the visible portion of Streamlit's tall iframe. */
export function useFrameViewport(active: boolean) {
  const [viewport, setViewport] = useState<{ top: number; height: number }>();
  useEffect(() => {
    if (!active) return;
    let host: Window = window;
    let frame: Element | null = null;
    try {
      // Only read same-origin geometry. Never reach into the host's app state.
      frame = window.frameElement;
      if (frame) host = window.parent;
    } catch { /* Cross-origin embeds retain their own viewport dimensions. */ }
    let animationFrame = 0;
    const update = () => {
      cancelAnimationFrame(animationFrame);
      animationFrame = requestAnimationFrame(() => {
        const visibleTop = host.visualViewport?.offsetTop ?? 0;
        const visibleHeight = host.visualViewport?.height ?? host.innerHeight;
        const rect = frame?.getBoundingClientRect();
        const top = rect ? Math.max(0, visibleTop - rect.top) : visibleTop;
        const bottom = rect ? Math.min(rect.height, visibleTop + visibleHeight - rect.top) : visibleTop + visibleHeight;
        const height = Math.max(0, bottom - top);
        setViewport(previous => previous?.top === top && previous.height === height ? previous : { top, height });
      });
    };
    update();
    // Streamlit scrolls an inner container, so capture descendant scroll events.
    host.addEventListener('scroll', update, true);
    host.addEventListener('resize', update);
    host.visualViewport?.addEventListener('resize', update);
    host.visualViewport?.addEventListener('scroll', update);
    const observer = new ResizeObserver(update);
    if (frame) observer.observe(frame);
    return () => {
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
      host.removeEventListener('scroll', update, true);
      host.removeEventListener('resize', update);
      host.visualViewport?.removeEventListener('resize', update);
      host.visualViewport?.removeEventListener('scroll', update);
    };
  }, [active]);
  return viewport;
}

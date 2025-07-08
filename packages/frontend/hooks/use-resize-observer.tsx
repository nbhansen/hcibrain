"use client";

import { useEffect, useRef, useState } from "react";

export function useResizeObserver<T extends HTMLElement>(): [
  React.RefObject<T>,
  number | undefined,
] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (!ref.current) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setWidth(entry.contentRect.width);
      }
    });

    observer.observe(ref.current);

    return () => {
      observer.disconnect();
    };
  }, [ref]);

  return [ref, width];
}

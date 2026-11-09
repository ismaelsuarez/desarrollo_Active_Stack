import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function RouteFocus() {
  const { pathname } = useLocation();
  useEffect(() => {
    const focusHeading = () => {
      const heading = document.querySelector<HTMLElement>('main h1');
      if (!heading) return false;
      heading.setAttribute('tabindex', '-1');
      heading.focus();
      return true;
    };
    if (focusHeading()) return;
    const observer = new MutationObserver(() => { if (focusHeading()) observer.disconnect(); });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [pathname]);
  return null;
}

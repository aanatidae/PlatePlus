import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown } from "lucide-react";

export type PlatePlusOption = { value: string; label: string; disabled?: boolean };

export function nextEnabledOptionIndex(options: PlatePlusOption[], from: number, direction: 1 | -1) {
  if (!options.length) return -1;
  for (let offset = 1; offset <= options.length; offset += 1) {
    const index = (from + direction * offset + options.length) % options.length;
    if (!options[index].disabled) return index;
  }
  return -1;
}

export function PlatePlusSelect({ label, value, options, onChange, disabled = false, placeholder = "Select an option" }: {
  label: string; value: string; options: PlatePlusOption[]; onChange: (value: string) => void; disabled?: boolean; placeholder?: string;
}) {
  const labelId = useId(); const listboxId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null); const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false); const [activeIndex, setActiveIndex] = useState(0);
  const [position, setPosition] = useState<{ left: number; top: number; width: number; maxHeight: number } | null>(null);
  const selectedIndex = options.findIndex(option => option.value === value);
  const selected = options[selectedIndex];
  const close = (restoreFocus = false) => { setOpen(false); if (restoreFocus) requestAnimationFrame(() => triggerRef.current?.focus()); };
  const updatePosition = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const viewportPadding = 12; const roomBelow = window.innerHeight - rect.bottom - viewportPadding; const roomAbove = rect.top - viewportPadding;
    const openUpwards = roomBelow < 180 && roomAbove > roomBelow;
    const maxHeight = Math.max(120, Math.min(280, (openUpwards ? roomAbove : roomBelow) - 4));
    setPosition({ left: Math.max(viewportPadding, Math.min(rect.left, window.innerWidth - rect.width - viewportPadding)), top: openUpwards ? Math.max(viewportPadding, rect.top - maxHeight - 6) : rect.bottom + 6, width: Math.min(rect.width, window.innerWidth - viewportPadding * 2), maxHeight });
  };
  const openMenu = () => { if (disabled) return; setActiveIndex(selectedIndex >= 0 ? selectedIndex : options.findIndex(option => !option.disabled)); updatePosition(); setOpen(true); };
  const choose = (index: number) => { const option = options[index]; if (!option || option.disabled) return; onChange(option.value); close(true); };
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => { if (!triggerRef.current?.contains(event.target as Node) && !menuRef.current?.contains(event.target as Node)) close(); };
    const reposition = () => updatePosition();
    document.addEventListener("pointerdown", closeOutside); window.addEventListener("resize", reposition); window.addEventListener("scroll", reposition, true);
    requestAnimationFrame(() => menuRef.current?.focus());
    return () => { document.removeEventListener("pointerdown", closeOutside); window.removeEventListener("resize", reposition); window.removeEventListener("scroll", reposition, true); };
  }, [open]);
  const move = (direction: 1 | -1) => setActiveIndex(index => nextEnabledOptionIndex(options, index, direction));
  const onTriggerKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); openMenu(); setActiveIndex(selectedIndex >= 0 ? selectedIndex : options.findIndex(option => !option.disabled)); }
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open ? close() : openMenu(); }
  };
  const onMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") { event.preventDefault(); close(true); }
    else if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
    else if (event.key === "Home") { event.preventDefault(); setActiveIndex(options.findIndex(option => !option.disabled)); }
    else if (event.key === "End") { event.preventDefault(); const enabled = options.map((option, index) => option.disabled ? -1 : index).filter(index => index >= 0); setActiveIndex(enabled.length ? enabled[enabled.length - 1] : -1); }
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(activeIndex); }
  };
  return <div className="plateplus-select"><span className="plateplus-select-label" id={labelId}>{label}</span><button ref={triggerRef} type="button" className="plateplus-select-trigger" aria-labelledby={labelId} aria-haspopup="listbox" aria-controls={open ? listboxId : undefined} aria-expanded={open} disabled={disabled} title={selected?.label ?? placeholder} onClick={() => open ? close() : openMenu()} onKeyDown={onTriggerKeyDown}><span>{selected?.label ?? placeholder}</span><ChevronDown aria-hidden="true" size={16} /></button>{open && position && createPortal(<div ref={menuRef} id={listboxId} className="plateplus-select-menu" role="listbox" aria-labelledby={labelId} aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined} tabIndex={-1} style={position} onKeyDown={onMenuKeyDown}>{options.map((option, index) => <button id={`${listboxId}-${index}`} type="button" role="option" aria-selected={option.value === value} aria-disabled={option.disabled || undefined} className={`${option.value === value ? "selected" : ""} ${index === activeIndex ? "active" : ""}`} disabled={option.disabled} key={option.value} onMouseMove={() => !option.disabled && setActiveIndex(index)} onClick={() => choose(index)}><span>{option.label}</span>{option.value === value && <Check size={15} aria-hidden="true" />}</button>)}</div>, document.body)}</div>;
}

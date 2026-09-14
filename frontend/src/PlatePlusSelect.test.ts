import { describe, expect, it } from "vitest";
import { getListboxPosition } from "./PlatePlusSelect";

const rect = (left: number, top: number, width: number, height: number) => ({ left, top, width, height, right: left + width, bottom: top + height }) as DOMRect;

describe("shared PlatePlus listbox positioning", () => {
  it("anchors below its trigger with matching width when there is room", () => {
    expect(getListboxPosition(rect(100, 160, 180, 40), 160, 1280, 800)).toMatchObject({ left: 100, top: 206, width: 180 });
  });

  it("uses the rendered menu height when opening upwards instead of leaving a stale-height gap", () => {
    expect(getListboxPosition(rect(100, 700, 180, 40), 116, 1280, 800)).toMatchObject({ top: 578, maxHeight: 280 });
  });

  it("keeps a near-edge menu inside the horizontal viewport", () => {
    expect(getListboxPosition(rect(1240, 120, 160, 40), 160, 1280, 800)).toMatchObject({ left: 1108, width: 160 });
  });
});

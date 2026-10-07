// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { ModelPerformance, SingaporeanDetectorEvidence } from "./ModelPerformance";
import { PlatePlusSelect, getListboxPosition } from "./PlatePlusSelect";

vi.mock("./locations", () => ({ getJson: async () => ({ evaluation: { detector: { accuracy_percent: 93.1 }, ocr: { exact_matches:37, held_out_samples:44, exact_match_accuracy_percent:84.1 } }, known_failure_conditions: Array.from({length:50},(_,i)=>`Limitation ${i}`) }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("portals the modal outside its filtered header, locks background scroll, and restores focus/scroll on close", async () => {
  const { container } = render(<header style={{backdropFilter:"blur(12px)"}}><ModelPerformance /></header>);
  const trigger=screen.getByRole("button",{name:"Model performance"});
  fireEvent.click(trigger);
  const dialog=await screen.findByRole("dialog");
  expect(container.contains(dialog)).toBe(false);
  expect(dialog.parentElement?.parentElement).toBe(document.body);
  expect(document.body.style.overflow).toBe("hidden");
  const close=within(dialog).getByRole("button",{name:"Close model performance"});
  expect(document.activeElement).toBe(close);
  expect(within(dialog).getByRole("region",{name:"Model evaluation evidence"}).tabIndex).toBe(0);
  fireEvent.click(close);
  expect(screen.queryByRole("dialog")).toBeNull();
  await waitFor(()=>expect(document.activeElement).toBe(trigger));
  expect(document.body.style.overflow).toBe("");
  fireEvent.click(trigger); fireEvent.mouseDown(screen.getByRole("dialog").parentElement!);
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("renders only verified SG detector metrics, separately from OCR/origin claims", () => {
  const evidence={verified:true,split:"test",images:31,labelled_plates:33,standard_metrics:{precision:.826,recall:.788,map50:.81,map50_95:.567},operational_metrics:{true_positive_plates:24,recall:24/33},parameters:{operational_confidence:.5}};
  const { rerender }=render(<SingaporeanDetectorEvidence evidence={evidence} />);
  expect(screen.getByText("72.7% recall at runtime gate")).toBeTruthy();
  expect(screen.getByText(/24 \/ 33 labelled plates/)).toBeTruthy();
  expect(screen.getByText(/without Singaporean fine-tuning/)).toBeTruthy();
  rerender(<SingaporeanDetectorEvidence evidence={{...evidence,verified:false}} />);
  expect(screen.queryByText("Singaporean detector transfer evaluation")).toBeNull();
});

it("keeps a wider intrinsic menu inside the viewport instead of matching a narrow trigger", () => {
  const rect={left:1200,top:100,right:1280,bottom:140,width:80,height:40} as DOMRect;
  expect(getListboxPosition(rect,200,1366,768,320)).toMatchObject({width:320,left:1034,top:146});
  expect(getListboxPosition(rect,200,390,844,500).width).toBe(366);
});

it("shows full Grand Saga option text/title and preserves keyboard selection and Escape", async () => {
  const onChange=vi.fn();
  const names=["Simulated LDP Toll Plaza","Simulated AKLEH Toll Plaza","Simulated NPE Toll Plaza","Simulated Grand Saga Toll Plaza","Simulator Toll Plaza"];
  render(<PlatePlusSelect label="Toll location" value="0" options={names.map((label,i)=>({value:String(i),label}))} onChange={onChange} />);
  const trigger=screen.getByRole("button",{name:"Toll location"});
  fireEvent.click(trigger);
  const option=screen.getByRole("option",{name:names[3]});
  expect(option.title).toBe(names[3]);
  const menu=screen.getByRole("listbox");
  fireEvent.keyDown(menu,{key:"End"}); fireEvent.keyDown(menu,{key:"ArrowUp"}); fireEvent.keyDown(menu,{key:"Enter"});
  expect(onChange).toHaveBeenCalledWith("3");
  fireEvent.click(trigger); fireEvent.keyDown(screen.getByRole("listbox"),{key:"Escape"});
  expect(screen.queryByRole("listbox")).toBeNull();
});

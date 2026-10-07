// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { useFeed } from "./locations";

function Probe({ path="/api/operations/demo/feed" }: {path?:string}) {
  const feed=useFeed<{value:string}>(path);
  return <p>{feed.error || feed.data?.value || "loading"}</p>;
}
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();});

it("allows a slow response to finish across multiple poll ticks without aborting it",async()=>{
  vi.useFakeTimers();
  let finish!: (response:Response)=>void;
  const fetch=vi.fn(()=>new Promise<Response>(resolve=>{finish=resolve;}));
  vi.stubGlobal("fetch",fetch);
  render(<Probe />);
  await act(async()=>{vi.advanceTimersByTime(10_000);});
  expect(fetch).toHaveBeenCalledTimes(1);
  const signal=(fetch.mock.calls[0] as unknown as [string,RequestInit])[1].signal!;
  expect(signal.aborted).toBe(false);
  await act(async()=>{finish(new Response(JSON.stringify({value:"running and current"})));});
  expect(screen.getByText("running and current")).toBeTruthy();
  await act(async()=>{vi.advanceTimersByTime(5_000);});
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("retains the real request deadline and exposes a timeout instead of healthy cached status",async()=>{
  vi.useFakeTimers();
  vi.stubGlobal("fetch",vi.fn(()=>new Promise<Response>(()=>{})));
  render(<Probe />);
  await act(async()=>{vi.advanceTimersByTime(15_001);});
  expect(screen.getByText(/taking too long to respond/)).toBeTruthy();
});

it("still aborts the old request when the location scope changes and ignores its late result",async()=>{
  let oldFinish!: (response:Response)=>void;
  const fetch=vi.fn((path:string)=>path.includes("old")?new Promise<Response>(resolve=>{oldFinish=resolve;}):Promise.resolve(new Response(JSON.stringify({value:"new scope"}))));
  vi.stubGlobal("fetch",fetch);
  const {rerender}=render(<Probe path="/api/live/overview?location_id=old" />);
  const signal=(fetch.mock.calls[0] as unknown as [string,RequestInit])[1].signal!;
  rerender(<Probe path="/api/live/overview?location_id=new" />);
  expect(signal.aborted).toBe(true);
  await act(async()=>{oldFinish(new Response(JSON.stringify({value:"wrong old scope"})));});
  expect(screen.getByText("new scope")).toBeTruthy();
  expect(screen.queryByText("wrong old scope")).toBeNull();
});

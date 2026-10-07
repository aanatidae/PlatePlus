// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import NetworkOverview from "./NetworkOverview";

const state=vi.hoisted(()=>({locations:[],feed:{data:{running:false,state:"paused",last_error:null as string|null},error:"",receivedAt:0}}));
vi.mock("./App",()=>({apiHeaders:()=>({Authorization:"Bearer test"})}));
vi.mock("./locations",()=>({
  useLocations:()=>({locations:state.locations,selected:"all",select:vi.fn()}),
  locationPath:(path:string)=>path,
  useFeed:(path:string)=>path==="/api/operations/demo/feed"?state.feed:{data:null,error:"",receivedAt:0},
}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();state.feed={data:{running:false,state:"paused",last_error:null},error:"",receivedAt:0};});

it("reports backend recovery rather than falsely saying healthy running",()=>{
  state.feed.data={running:true,state:"recovering",last_error:"Feed cycle failed (ConnectionError); retrying automatically."};
  render(<NetworkOverview />);
  expect(screen.getByText(/Feed recovering/)).toBeTruthy();
  expect(screen.getByText(/Feed cycle failed/).textContent).toContain("ConnectionError");
  expect(screen.queryByText(/Live feed running/)).toBeNull();
});

it("does not label stale cached running state as current after a polling/auth failure",()=>{
  state.feed.data={running:true,state:"running",last_error:null};state.feed.error="Administrator authentication is required.";
  render(<NetworkOverview />);
  expect(screen.getByText(/Feed status unavailable/)).toBeTruthy();
  expect(screen.queryByText(/Live feed running/)).toBeNull();
});

it("shows failed feed control requests instead of silently treating HTTP 401 as success",async()=>{
  vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({detail:"Administrator authentication is required."}),{status:401})));
  render(<NetworkOverview />);
  fireEvent.click(screen.getByRole("button",{name:"Start Live Feed"}));
  expect((await screen.findByRole("alert")).textContent).toContain("Administrator authentication is required.");
});
